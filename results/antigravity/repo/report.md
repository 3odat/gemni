# System + Attack Technical Report (Chapter Format)

Last updated: 2026-01-29

## Table of Contents
- [Chapter 1 — Introduction](#chapter-1-introduction)
- [Chapter 2 — System Design (end-to-end pipeline)](#chapter-2-system-design-end-to-end-pipeline)
- [Chapter 3 — Memory + RAG Retrieval (how it works)](#chapter-3-memory--rag-retrieval-how-it-works)
- [Chapter 4 — Threat Model and Attack Surfaces](#chapter-4-threat-model-and-attack-surfaces)
- [Chapter 5 — Attack Catalogue (one section per attack)](#chapter-5-attack-catalogue-one-section-per-attack)
- [Chapter 6 — Results (success rates + analysis)](#chapter-6-results-success-rates--analysis)
- [Chapter 7 — Mitigations (mapped to attacks)](#chapter-7-mitigations-mapped-to-attacks)
- [Chapter 8 — Reproducibility (commands)](#chapter-8-reproducibility-commands)
- [Appendix — Repo Map + Glossary](#appendix--repo-map--glossary)

---

<a id="chapter-1-introduction"></a>
# Chapter 1 — Introduction

This repo implements a **RAG-augmented multi-agent UAV controller**: an LLM-based **Supervisor** generates a strict JSON mission plan for two **Workers**, which execute against **PX4 SITL** via **MAVSDK**. The security focus is memory/RAG poisoning: attacker-controlled episodic logs and semantic rules can become “trusted” context and push plans toward denial-of-service (grounding) or safety violations (unsafe flight).

Evidence used (repo/log-grounded):
- System + attacks: `uav_project/` (especially `uav_project/minja_run.py`, `uav_project/core/attack_harness.py`)
- Injection-stage terminal output: `results/injection_only_runs.log`
- Claimed outcomes + aggregate success for 10 attacks: `results/attack_results_log.md`
- DB snapshots for some scenarios: `results/memory_dump_*_{BEFORE,AFTER}.json`
- MAVSDK logs: `mavsdk_50051.log`, `mavsdk_50052.log`

---

<a id="chapter-2-system-design-end-to-end-pipeline"></a>
# Chapter 2 — System Design (end-to-end pipeline)

## 2.1 End-to-end pipeline (grounded in code)

1) Connect: `uav_project/agents/worker.py :: WorkerAgent.initialize` -> `uav_project/interfaces/drone_interface.py :: DroneInterface.connect`
2) Readiness: `uav_project/interfaces/drone_interface.py :: DroneInterface._wait_for_global_position` / `_wait_for_home_position` / `_wait_for_altitude`
3) Memory init: `uav_project/interfaces/memory_interface.py :: MemoryInterface.__init__` -> `uav_project/core/database.py :: DatabaseManager._init_tables` (DB file `mission_memory.db`)
4) Retrieval: `uav_project/interfaces/memory_interface.py :: MemoryInterface.retrieve_context` -> `uav_project/core/database.py :: DatabaseManager.find_similar_episodes` / `find_similar_rules` (top-k default `limit=3`)
5) Prompt assembly: `uav_project/agents/supervisor.py :: SupervisorAgent.plan_mission` (inserts `CONTEXT FROM MEMORY`)
6) Planning: `SupervisorAgent.plan_mission` outputs schema `uav_project/schemas/models.py :: MissionPlan`
7) Execution: `uav_project/agents/worker.py :: WorkerAgent.execute_task` -> `DroneInterface.arm_and_takeoff` / `goto_location` / `land`
8) Logging: `WorkerAgent.execute_task` -> `MemoryInterface.log_experience` -> `DatabaseManager.insert_episode`
9) Evaluation: `uav_project/minja_run.py :: _attack_effect_verdict`

## 2.2 System flowchart (GitHub-safe Mermaid)

```mermaid
flowchart TD
  U[User] --> S[Supervisor]
  A[Attacker] --> DB[MemoryDB]
  S --> R[Retriever]
  R --> DB
  DB --> R
  R --> S
  S --> W[Worker]
  W --> PX4[PX4]
  W --> DB
```

## 2.3 Clean-run sequence (GitHub-safe Mermaid)

```mermaid
sequenceDiagram
  participant U as User
  participant S as Supervisor
  participant R as Retriever
  participant DB as MemoryDB
  participant LLM as LLM
  participant W as Worker
  participant PX4 as PX4
  participant LG as Logger

  U->>S: mission text
  S->>R: retrieve context
  R->>DB: search topk
  DB-->>R: items
  R-->>S: context
  S->>LLM: plan request
  LLM-->>S: MissionPlan JSON
  S->>W: tasks
  W->>PX4: execute
  W->>LG: log to memory
```

---

<a id="chapter-3-memory--rag-retrieval-how-it-works"></a>
# Chapter 3 — Memory + RAG Retrieval (how it works)

## 3.1 Memory types (repo-grounded)

- Episodic logs: SQLite `episodic_memory` in `uav_project/core/database.py :: DatabaseManager._init_tables`, written by `uav_project/interfaces/memory_interface.py :: MemoryInterface.log_experience`
- Semantic rules: SQLite `semantic_rules` in the same file, written by `uav_project/interfaces/memory_interface.py :: MemoryInterface.add_rule`

## 3.2 SQLite schema summary (repo-grounded)

From `uav_project/core/database.py :: DatabaseManager._init_tables`:
- `episodic_memory`: `id,timestamp,drone_id,mission_id,action_type,state_json,outcome_text,embedding,integrity_hash,is_poisoned`
- `semantic_rules`: `id,rule_text,rule_type,location_json,confidence,embedding,is_poisoned`
- Indexes/constraints: TBD (not present in logs/repo) beyond `PRIMARY KEY AUTOINCREMENT`

## 3.3 Retrieval + prompt insertion (repo-grounded)

- Retrieval: cosine similarity top-k in `DatabaseManager.find_similar_episodes` and `DatabaseManager.find_similar_rules`
- Context formatting: `MemoryInterface.retrieve_context` (also prepends `SUMMARY` via `find_rules_by_type("SUMMARY", limit=1)`)
- Prompt insertion: `SupervisorAgent.plan_mission` builds `rag_prompt` containing `CONTEXT FROM MEMORY`

## 3.4 Retrieval flowchart (GitHub-safe Mermaid)

```mermaid
flowchart TD
  Q[MissionText] --> E[EmbedQuery]
  E --> EP[SearchEpisodesTopK]
  E --> RU[SearchRulesTopK]
  RU --> SU[FetchSummaryRule]
  EP --> F[FormatContext]
  SU --> F
  F --> P[BuildRAGPrompt]
  P --> L[LLMPlan]
```

---

<a id="chapter-4-threat-model-and-attack-surfaces"></a>
# Chapter 4 — Threat Model and Attack Surfaces

## 4.1 Threat model (repo/log-grounded)

- Implemented adversary capability: **direct memory injection** using `uav_project/core/attack_harness.py :: AttackHarness.inject_scenario`
  - Terminal evidence: `results/injection_only_runs.log` contains `INFO: [POISON] Logged episode...` and `INFO: [POISON_RULE] Added semantic rule...`
- Implemented adversary influence path: retrieved memory is inserted into the Supervisor prompt:
  - `uav_project/agents/supervisor.py :: SupervisorAgent.plan_mission`
- Constraint: Worker action set is restricted by schema:
  - `uav_project/schemas/models.py :: Task.action_type` allows only `move`, `scan`, `return`

## 4.2 Attack surfaces (repo-grounded)

- Ingestion: `MemoryInterface.log_experience`, `MemoryInterface.add_rule`
- Retrieval: `DatabaseManager.find_similar_*` (similarity-only top-k)
- Prompt insertion: `SupervisorAgent.plan_mission` (memory inside a high-authority prompt)
- Fallback logic: `SupervisorAgent._fallback_plan` (string-triggered behavior such as `SAFETY_OVERRIDE`)

---

<a id="chapter-5-attack-catalogue-one-section-per-attack"></a>
# Chapter 5 — Attack Catalogue (one section per attack)

Global evidence note:
- Injection-stage evidence exists for all integrated scenarios in `results/injection_only_runs.log`.
- Full end-to-end per-scenario terminal traces (retrieval -> plan -> worker -> PX4) are mostly `TBD (not present in logs/repo)`.

## Attack A1: False obstacle plus battery drain (Scenario: `hazard_a`)
- Goal: deny mission for Sector A by inserting crash/hazard and energy warning.
- Where it hits the pipeline: ingestion -> retrieval -> planning.
- Step-by-step (numbered bullets):
  1) (Attacker) SENDS/RECEIVES: poison episodes inserted; Evidence: `INFO: [POISON] Logged episode for Drone 1`; Repo: `uav_project/core/attack_harness.py :: AttackHarness.inject_false_obstacle` (`results/injection_only_runs.log`)
  2) (Attacker) SENDS/RECEIVES: hazard rule inserted; Evidence: `INFO: [POISON_RULE] Added semantic rule: Hazard: High-tension wires detected`; Repo: `uav_project/core/attack_harness.py :: AttackHarness.inject_fake_hazard_rule` (`results/injection_only_runs.log`)
  3) (Retriever) SENDS/RECEIVES: top-k context; Evidence: TBD (not present in logs/repo); Repo: `uav_project/interfaces/memory_interface.py :: MemoryInterface.retrieve_context`
  4) (Supervisor) SENDS/RECEIVES: plan JSON; Evidence: TBD (not present in logs/repo); Repo: `uav_project/agents/supervisor.py :: SupervisorAgent.plan_mission`
- LLM input vs output:
  - Retrieved context: crash/hazard strings (see `results/memory_dump_hazard_a_AFTER.json`).
  - Output: `MissionPlan` JSON schema (`uav_project/schemas/models.py :: MissionPlan`).
  - Plan change mechanism: Supervisor prompt treats `CRITICAL FAILURE` / `UNSAFE` as safety triggers (`SupervisorAgent.system_prompt`).
- Why it succeeded (root weakness): unverified memory is treated as authoritative; `is_poisoned` is not filtered in retrieval.
- Success Rate: TBD (X/Y not present); outcome reported in `results/attack_results_log.md` for `hazard_a` (at least one run).
- Mitigations (3–5):
  - Filter `is_poisoned` in `DatabaseManager.find_similar_*` (retrieval); blocks direct injection; overhead low.
  - Add provenance/signatures for safety-critical entries (ingestion/retrieval); blocks spoofed hazards; overhead medium.
  - Executor safety gate before `goto_location` (executor); blocks unsafe plan execution; overhead medium.
- Repo grounding:
  - Implemented in: `uav_project/core/attack_harness.py :: AttackHarness.inject_scenario` (`hazard_a`)
  - Evidence: `results/injection_only_runs.log`; `results/memory_dump_hazard_a_AFTER.json`

```mermaid
sequenceDiagram
  participant A as Attacker
  participant DB as MemoryDB
  participant R as Retriever
  participant S as Supervisor
  participant W as Worker
  participant PX4 as PX4
  participant LG as Logger
  A->>DB: inject hazard
  S->>R: retrieve context
  R->>DB: search topk
  DB-->>R: poison items
  R-->>S: context with hazard
  S->>W: plan tasks
  W->>PX4: execute
  W->>LG: log outcome
```

## Attack A2: Shared-sector denial (Scenario: `hazard_b`)
- Goal: deny Sector B access via shared memory poisoning.
- Where it hits the pipeline: ingestion -> retrieval -> planning.
- Step-by-step (numbered bullets):
  1) (Attacker) SENDS/RECEIVES: poison inserted; Evidence: `INFO: [POISON] Logged episode for Drone 1`; Repo: `AttackHarness.inject_false_obstacle` (`results/injection_only_runs.log`)
  2) (Retriever) SENDS/RECEIVES: top-k context; Evidence: TBD; Repo: `MemoryInterface.retrieve_context`
  3) (Supervisor) SENDS/RECEIVES: plan JSON; Evidence: TBD; Repo: `SupervisorAgent.plan_mission`
- LLM input vs output:
  - Retrieved context: hazard items (see `results/memory_dump_hazard_b_AFTER.json`).
  - Output: `MissionPlan` JSON.
  - Plan change: shared DB influences swarm plan (`uav_project/minja_run.py :: run_minja` uses one `MemoryInterface`).
- Why it succeeded (root weakness): shared memory is a cross-agent contamination channel.
- Success Rate: TBD; outcome reported in `results/attack_results_log.md` for `hazard_b` (at least one run).
- Mitigations (3–5):
  - Partition retrieval by drone_id and writer role (retrieval); overhead medium.
  - Spatial binding using `location_json` (retrieval); overhead medium.
  - Filter `is_poisoned` (retrieval); overhead low.
- Repo grounding:
  - Implemented in: `AttackHarness.inject_scenario` (`hazard_b`)
  - Evidence: `results/injection_only_runs.log`; `results/memory_dump_hazard_b_AFTER.json`

```mermaid
sequenceDiagram
  participant A as Attacker
  participant DB as MemoryDB
  participant R as Retriever
  participant S as Supervisor
  participant W as Worker
  participant PX4 as PX4
  participant LG as Logger
  A->>DB: inject sector B hazard
  S->>R: retrieve context
  R->>DB: search topk
  DB-->>R: poison items
  R-->>S: context with hazard
  S->>W: omit unsafe tasks
  W->>PX4: execute reduced plan
  W->>LG: log outcome
```

## Attack A3: Targeted grounding of Drone 2 (Scenario: `hazard_2`)
- Goal: ground Drone 2 by poisoning its target sector.
- Where it hits the pipeline: ingestion -> retrieval -> planning.
- Step-by-step (numbered bullets):
  1) (Attacker) SENDS/RECEIVES: poison inserted; Evidence: `INFO: [POISON] Logged episode for Drone 2`; Repo: `AttackHarness.inject_false_obstacle` (`results/injection_only_runs.log`)
  2) (Retriever) SENDS/RECEIVES: top-k context; Evidence: TBD; Repo: `MemoryInterface.retrieve_context`
  3) (Supervisor) SENDS/RECEIVES: plan JSON; Evidence: TBD; Repo: `SupervisorAgent.plan_mission`
- LLM input vs output:
  - Retrieved context: hazard items (see `results/memory_dump_hazard_2_AFTER.json`).
  - Output: `MissionPlan` JSON.
  - Plan change: hazard applied to one drone’s move tasks.
- Why it succeeded (root weakness): no robust per-drone binding between memory provenance and planned tasks.
- Success Rate: TBD; outcome reported in `results/attack_results_log.md` for `hazard_2` (at least one run).
- Mitigations (3–5):
  - Build per-drone context blocks (prompt); overhead medium.
  - Spatial binding using `location_json` (retrieval); overhead medium.
  - Filter `is_poisoned` (retrieval); overhead low.
- Repo grounding:
  - Implemented in: `AttackHarness.inject_scenario` (`hazard_2`)
  - Evidence: `results/injection_only_runs.log`; `results/memory_dump_hazard_2_AFTER.json`

```mermaid
sequenceDiagram
  participant A as Attacker
  participant DB as MemoryDB
  participant R as Retriever
  participant S as Supervisor
  participant W as Worker
  participant PX4 as PX4
  participant LG as Logger
  A->>DB: inject hazard for drone2
  S->>R: retrieve context
  R->>DB: search topk
  DB-->>R: poison items
  R-->>S: context with hazard
  S->>W: omit drone2 move
  W->>PX4: execute
  W->>LG: log outcome
```

## Attack A4: Battery drain warning (Scenario: `energy_b`)
- Goal: inject severe battery warning tied to Sector B.
- Where it hits the pipeline: ingestion -> retrieval -> planning.
- Step-by-step (numbered bullets):
  1) (Attacker) SENDS/RECEIVES: warning inserted; Evidence: `INFO: [POISON] Logged episode for Drone 1`; Repo: `AttackHarness.inject_fake_low_battery` (`results/injection_only_runs.log`)
  2) (Retriever) SENDS/RECEIVES: warning retrieved; Evidence: TBD; Repo: `MemoryInterface.retrieve_context`
  3) (Supervisor) SENDS/RECEIVES: plan JSON; Evidence: TBD; Repo: `SupervisorAgent.plan_mission`
- LLM input vs output:
  - Retrieved context: warning text (see `results/memory_dump_energy_b_AFTER.json`).
  - Output: `MissionPlan` JSON.
  - Plan change: warning may bias routing/decisions (model-dependent; logs TBD).
- Why it succeeded (root weakness): warnings are mixed into the trusted memory channel without verification.
- Success Rate: TBD; outcome reported in `results/attack_results_log.md` for `energy_b` (at least one run).
- Mitigations (3–5):
  - Separate narrative memory from structured telemetry (prompt); overhead medium.
  - Rank hazards separately from warnings (retrieval); overhead medium.
  - Filter `is_poisoned` (retrieval); overhead low.
- Repo grounding:
  - Implemented in: `AttackHarness.inject_scenario` (`energy_b`)
  - Evidence: `results/injection_only_runs.log`; `results/memory_dump_energy_b_AFTER.json`

```mermaid
sequenceDiagram
  participant A as Attacker
  participant DB as MemoryDB
  participant R as Retriever
  participant S as Supervisor
  participant W as Worker
  participant PX4 as PX4
  participant LG as Logger
  A->>DB: inject battery warning
  S->>R: retrieve context
  R->>DB: search topk
  DB-->>R: warning item
  R-->>S: context with warning
  S->>W: plan tasks
  W->>PX4: execute
  W->>LG: log outcome
```

## Attack A5: Stale hazard rule (Scenario: `stale_hazard`)
- Goal: plant a semantic hazard rule for later retrieval.
- Where it hits the pipeline: ingestion -> retrieval.
- Step-by-step (numbered bullets):
  1) (Attacker) SENDS/RECEIVES: hazard rule inserted; Evidence: `INFO: [POISON_RULE] Added semantic rule: Hazard: Temporary jamming reported`; Repo: `AttackHarness.inject_fake_hazard_rule` (`results/injection_only_runs.log`)
  2) (Retriever) SENDS/RECEIVES: rule may be retrieved; Evidence: TBD; Repo: `DatabaseManager.find_similar_rules`
- LLM input vs output:
  - Retrieved context: semantic rule (logs show insertion; retrieval logs TBD).
  - Output: `MissionPlan` JSON.
  - Plan change: similarity-only retrieval may surface irrelevant hazards.
- Why it succeeded (root weakness): retrieval does not enforce spatial scoping from `location_json`.
- Success Rate: TBD (not present).
- Mitigations (3–5):
  - Spatial binding using `location_json` (retrieval); overhead medium.
  - Timestamp-aware ranking (retrieval); overhead medium.
  - Conservative conflict policy (prompt); overhead low.
- Repo grounding:
  - Implemented in: `AttackHarness.inject_scenario` (`stale_hazard`)
  - Evidence: `results/injection_only_runs.log`

```mermaid
sequenceDiagram
  participant A as Attacker
  participant DB as MemoryDB
  participant R as Retriever
  participant S as Supervisor
  participant W as Worker
  participant PX4 as PX4
  participant LG as Logger
  A->>DB: inject stale rule
  S->>R: retrieve context
  R->>DB: search topk
  DB-->>R: stale rule
  R-->>S: context with rule
  S->>W: plan tasks
  W->>PX4: execute
  W->>LG: log outcome
```

## Attack A6: Context dilution flood (Scenario: `dilution`)
- Goal: flood memory with noise so hazards drop out of top-k.
- Where it hits the pipeline: ingestion -> retrieval.
- Step-by-step (numbered bullets):
  1) (Attacker) SENDS/RECEIVES: 50 noise episodes; Evidence: `INFO: [POISON] Logged episode for Drone 0`; Repo: `AttackHarness.inject_noise_flood` (`results/injection_only_runs.log`)
  2) (Retriever) SENDS/RECEIVES: top-k dominated by noise; Evidence: TBD; Repo: `DatabaseManager.find_similar_episodes`
- LLM input vs output:
  - Retrieved context: likely noise with mission keywords (injection uses `[Ref: Sector A, Sector B]` in code).
  - Output: `MissionPlan` JSON.
  - Plan change: safety trigger phrases may be absent due to top-k eviction.
- Why it succeeded (root weakness): similarity-only top-k retrieval with no diversity or hazard reservation.
- Success Rate: TBD; narrative outcome reported in `results/attack_results_log.md` for `dilution` (at least one run).
- Mitigations (3–5):
  - Diversity-aware reranking (retrieval); overhead medium.
  - Ingestion rate limits (ingestion); overhead medium.
  - Hazard-reserved context slots (retrieval/prompt); overhead medium.
- Repo grounding:
  - Implemented in: `AttackHarness.inject_scenario` (`dilution`)
  - Evidence: `results/injection_only_runs.log`; `results/attack_results_log.md`

```mermaid
sequenceDiagram
  participant A as Attacker
  participant DB as MemoryDB
  participant R as Retriever
  participant S as Supervisor
  participant W as Worker
  participant PX4 as PX4
  participant LG as Logger
  A->>DB: inject noise logs
  S->>R: retrieve context
  R->>DB: search topk
  DB-->>R: mostly noise
  R-->>S: context missing hazard
  S->>W: plan tasks
  W->>PX4: execute
  W->>LG: log outcome
```

## Attack A7: Prompt stuffing dilution (Scenario: `dilution_prompt`)
- Goal: bias planning by adding large prompt text without DB injection.
- Where it hits the pipeline: prompt assembly.
- Step-by-step (numbered bullets):
  1) (Attacker) SENDS/RECEIVES: set scenario; Evidence: `INFO: Dilution prompt-stuffing enabled in Supervisor; no memory injection performed.`; Repo: `uav_project/agents/supervisor.py :: SupervisorAgent._use_dilution_prompt` (`results/injection_only_runs.log`)
  2) (Supervisor) SENDS/RECEIVES: builds prompt with repeated handbook; Evidence: TBD; Repo: `SupervisorAgent._build_dilution_block` / `SupervisorAgent.plan_mission`
- LLM input vs output:
  - Retrieved context: normal retrieval plus extra appended handbook text.
  - Output: `MissionPlan` JSON.
  - Plan change: stuffed prompt can dilute hazard focus (run logs TBD).
- Why it succeeded (root weakness): single unstructured system prompt mixes safety, memory, and extra references.
- Success Rate: TBD (not present).
- Mitigations (3–5):
  - Fixed prompt budgets (prompt); overhead low.
  - Compartmentalize “reference” content (prompt); overhead low.
  - Require explicit hazard checklist in reasoning (prompt); overhead low.
- Repo grounding:
  - Implemented in: `uav_project/agents/supervisor.py :: SupervisorAgent._use_dilution_prompt`, `_build_dilution_block`
  - Evidence: `results/injection_only_runs.log`

```mermaid
sequenceDiagram
  participant A as Attacker
  participant DB as MemoryDB
  participant R as Retriever
  participant S as Supervisor
  participant W as Worker
  participant PX4 as PX4
  participant LG as Logger
  A-->>DB: no injection
  S->>R: retrieve context
  R->>DB: search topk
  DB-->>R: items
  R-->>S: context
  A->>S: set dilution_prompt
  S->>W: plan tasks
  W->>PX4: execute
```

## Attack A8: Normative precedent poisoning (Scenario: `normative`)
- Goal: insert “authorized precedent” so planning rationalizes unsafe behavior.
- Where it hits the pipeline: ingestion -> planning.
- Step-by-step (numbered bullets):
  1) (Attacker) SENDS/RECEIVES: precedent episode; Evidence: `INFO: [POISON] Logged episode for Drone 1`; Repo: `AttackHarness.inject_bad_precedent` (`results/injection_only_runs.log`)
  2) (Run) SENDS/RECEIVES: connect then abort; Evidence: `ERROR: Mission Aborted by User`; Repo: `uav_project/minja_run.py :: run_minja` (`results/normative_result.txt`)
  3) (Supervisor) SENDS/RECEIVES: plan JSON; Evidence: TBD; Repo: `SupervisorAgent.plan_mission`
- LLM input vs output:
  - Retrieved context: “SUPERVISOR_OVERRIDE ... Mission SUCCESS” style narrative (created by `inject_bad_precedent`).
  - Output: `MissionPlan` JSON.
  - Plan change: authority/precedent framing can override safety reasoning (logs TBD).
- Why it succeeded (root weakness): no authentication for who can assert “authorized override” in memory.
- Success Rate: TBD; narrative outcome reported in `results/attack_results_log.md` for `normative` (at least one run).
- Mitigations (3–5):
  - Signed override entries (ingestion/retrieval); overhead medium.
  - Treat precedent as non-authoritative in prompt (prompt); overhead low.
  - Conservative policy when precedent conflicts with hazards (prompt); overhead low.
- Repo grounding:
  - Implemented in: `AttackHarness.inject_bad_precedent`
  - Evidence: `results/injection_only_runs.log`; `results/attack_results_log.md`; `results/normative_result.txt`

```mermaid
sequenceDiagram
  participant A as Attacker
  participant DB as MemoryDB
  participant R as Retriever
  participant S as Supervisor
  participant W as Worker
  participant PX4 as PX4
  participant LG as Logger
  A->>DB: inject precedent log
  S->>R: retrieve context
  R->>DB: search topk
  DB-->>R: precedent item
  R-->>S: context with precedent
  S->>W: plan tasks
  W->>PX4: execute
  W->>LG: log outcome
```

## Attack A9: Gaslighting via false clearance (Scenario: `spoofing`)
- Goal: insert hazard then “correction” claiming sensor glitch so planning proceeds.
- Where it hits the pipeline: ingestion -> retrieval -> planning.
- Step-by-step (numbered bullets):
  1) (Attacker) SENDS/RECEIVES: hazard inserted; Evidence: `INFO: [POISON] Logged episode for Drone 1`; Repo: `AttackHarness.inject_false_obstacle` (`results/injection_only_runs.log`)
  2) (Attacker) SENDS/RECEIVES: clearance inserted; Evidence: `INFO: [POISON] Logged episode for Drone 99`; Repo: `AttackHarness.inject_false_clearance` (`results/injection_only_runs.log`)
  3) (Supervisor) SENDS/RECEIVES: plan JSON; Evidence: TBD; Repo: `SupervisorAgent.plan_mission`
- LLM input vs output:
  - Retrieved context: hazard narrative plus “CORRECTION ... SAFE” narrative.
  - Output: `MissionPlan` JSON.
  - Plan change: conflict resolved in favor of “correction” (logs TBD).
- Why it succeeded (root weakness): no trust hierarchy for corrections vs incidents.
- Success Rate: TBD; narrative outcome reported in `results/attack_results_log.md` for `spoofing` (at least one run).
- Mitigations (3–5):
  - Authenticated correction channel (ingestion); overhead medium.
  - Conservative conflict handling in prompt (prompt); overhead low.
  - Sensor cross-check integration (planner/executor); overhead medium; integration evidence TBD.
- Repo grounding:
  - Implemented in: `AttackHarness.inject_scenario` (`spoofing`)
  - Evidence: `results/injection_only_runs.log`; `results/attack_results_log.md`

```mermaid
sequenceDiagram
  participant A as Attacker
  participant DB as MemoryDB
  participant R as Retriever
  participant S as Supervisor
  participant W as Worker
  participant PX4 as PX4
  participant LG as Logger
  A->>DB: inject hazard
  A->>DB: inject clearance
  S->>R: retrieve context
  R->>DB: search topk
  DB-->>R: hazard and clearance
  R-->>S: conflicting context
  S->>W: plan tasks
  W->>PX4: execute
```

## Attack A10: Safety override keyword (Scenario: `spoofing_refined`)
- Goal: bypass hazard handling by injecting `SAFETY_OVERRIDE` rule.
- Where it hits the pipeline: semantic rule ingestion -> fallback logic and planning.
- Step-by-step (numbered bullets):
  1) (Attacker) SENDS/RECEIVES: override inserted; Evidence: `INFO: [POISON_RULE] Added semantic rule: SAFETY_OVERRIDE: Priority authorization`; Repo: `AttackHarness.inject_safety_override` (`results/injection_only_runs.log`)
  2) (Planner fallback) SENDS/RECEIVES: keyword bypass; Evidence: TBD; Repo: `uav_project/agents/supervisor.py :: SupervisorAgent._fallback_plan`
- LLM input vs output:
  - Retrieved context: includes `SAFETY_OVERRIDE` (insertion evidenced in logs).
  - Output: `MissionPlan` JSON or heuristic plan from `_fallback_plan`.
  - Plan change: explicit keyword check bypasses hazards in fallback planner.
- Why it succeeded (root weakness): a string keyword in attacker-controlled memory toggles safety behavior.
- Success Rate: TBD; narrative outcome reported in `results/attack_results_log.md` for `spoofing_refined` (at least one run).
- Mitigations (3–5):
  - Remove keyword bypass (planner); overhead low.
  - Authenticate override rules (ingestion/retrieval); overhead medium.
  - Executor safety gate (executor); overhead medium.
- Repo grounding:
  - Implemented in: `AttackHarness.inject_scenario` (`spoofing_refined`)
  - Evidence: `results/injection_only_runs.log`; `results/attack_results_log.md`

```mermaid
sequenceDiagram
  participant A as Attacker
  participant DB as MemoryDB
  participant R as Retriever
  participant S as Supervisor
  participant W as Worker
  participant PX4 as PX4
  participant LG as Logger
  A->>DB: inject SAFETY_OVERRIDE
  S->>R: retrieve context
  R->>DB: search topk
  DB-->>R: override item
  R-->>S: context with override
  S->>W: plan bypass hazard
  W->>PX4: execute
  W->>LG: log outcome
```

## Attack A11: Summary poisoning (Scenario: `self_summary`)
- Goal: insert `SUMMARY` rule that is prepended to context to deny missions.
- Where it hits the pipeline: semantic ingestion -> retrieval formatting.
- Step-by-step (numbered bullets):
  1) (Attacker) SENDS/RECEIVES: SUMMARY inserted; Evidence: `INFO: [POISON_RULE] Added semantic rule: Summary: Repeated hazards in Sector B`; Repo: `AttackHarness.inject_summary_poisoning` (`results/injection_only_runs.log`)
  2) (Retriever) SENDS/RECEIVES: summary prepended; Evidence: TBD; Repo: `MemoryInterface.retrieve_context` (calls `find_rules_by_type("SUMMARY", limit=1)`)
- LLM input vs output:
  - Retrieved context: starts with summary section (formatting in code).
  - Output: `MissionPlan` JSON.
  - Plan change: summary is presented first and can act like global policy.
- Why it succeeded (root weakness): priority placement without provenance verification.
- Success Rate: TBD; narrative outcome reported in `results/attack_results_log.md` for `self_summary` (at least one run).
- Mitigations (3–5):
  - Make SUMMARY read-only (ingestion); overhead medium.
  - Mark summaries untrusted in prompt (prompt); overhead low.
  - Monitor abrupt summary changes (evaluation); overhead medium; implementation TBD.
- Repo grounding:
  - Implemented in: `AttackHarness.inject_summary_poisoning`
  - Evidence: `results/injection_only_runs.log`; `results/attack_results_log.md`

```mermaid
sequenceDiagram
  participant A as Attacker
  participant DB as MemoryDB
  participant R as Retriever
  participant S as Supervisor
  participant W as Worker
  participant PX4 as PX4
  participant LG as Logger
  A->>DB: inject SUMMARY rule
  S->>R: retrieve context
  R->>DB: fetch summary
  DB-->>R: summary item
  R-->>S: context starts summary
  S->>W: plan tasks constrained
  W->>PX4: execute reduced plan
  W->>LG: log outcome
```

## Attack A12: Bridging rule (MINJA style) (Scenario: `minja_query`)
- Goal: insert policy-like exception framed as “analysis” to override general safety guidance.
- Where it hits the pipeline: semantic ingestion -> prompt insertion.
- Step-by-step (numbered bullets):
  1) (Attacker) SENDS/RECEIVES: `Analysis:` rule inserted; Evidence: `INFO: [POISON_RULE] Added semantic rule: Analysis: If No-Fly Zone in Sector A`; Repo: `AttackHarness.inject_minja_style_query` (`results/injection_only_runs.log`)
  2) (Supervisor) SENDS/RECEIVES: prompt contains memory between safety rules and user request; Evidence: TBD; Repo: `SupervisorAgent.plan_mission`
- LLM input vs output:
  - Retrieved context: derived exception rule (see `results/memory_dump_minja_query_AFTER.json`).
  - Output: `MissionPlan` JSON.
  - Plan change: exception can be treated as more specific guidance (logs TBD).
- Why it succeeded (root weakness): no separation between immutable safety rules and mutable “derived policy” memory items.
- Success Rate: TBD (not present).
- Mitigations (3–5):
  - Block unverified policy-derivation rule types (retrieval); overhead low.
  - Repeat safety rules after memory context (prompt); overhead low.
  - Store “analysis” separately from rules (memory); overhead medium.
- Repo grounding:
  - Implemented in: `AttackHarness.inject_minja_style_query`
  - Evidence: `results/injection_only_runs.log`; `results/memory_dump_minja_query_AFTER.json`

```mermaid
sequenceDiagram
  participant A as Attacker
  participant DB as MemoryDB
  participant R as Retriever
  participant S as Supervisor
  participant W as Worker
  participant PX4 as PX4
  participant LG as Logger
  A->>DB: inject bridging rule
  S->>R: retrieve context
  R->>DB: search topk
  DB-->>R: bridging rule
  R-->>S: context with exception
  S->>W: plan tasks
  W->>PX4: execute
  W->>LG: log outcome
```

## Attack A13: Zombie log imitation (MemoryGraft) (Scenario: `memory_graft`)
- Goal: insert “MISSION_SUCCESS” story to induce imitation.
- Where it hits the pipeline: episodic ingestion -> planning.
- Step-by-step (numbered bullets):
  1) (Attacker) SENDS/RECEIVES: MISSION_SUCCESS inserted; Evidence: `INFO: [POISON] Logged episode for Drone 1`; Repo: `AttackHarness.inject_memory_graft` (`results/injection_only_runs.log`)
  2) (Supervisor) SENDS/RECEIVES: plan JSON; Evidence: TBD; Repo: `SupervisorAgent.plan_mission`
- LLM input vs output:
  - Retrieved context: “MISSION_SUCCESS” narrative (see `results/memory_dump_memory_graft_AFTER.json`).
  - Output: `MissionPlan` JSON.
  - Plan change: successful example acts like a procedure template (logs TBD).
- Why it succeeded (root weakness): no separation between “experience log” and “approved procedure.”
- Success Rate: TBD (not present).
- Mitigations (3–5):
  - Forbid procedural imitation from memory in prompt (prompt); overhead low.
  - Validate plan against policy before execution (planner/executor); overhead medium.
  - Sanitize reward-like tokens during retrieval formatting (retrieval); overhead low.
- Repo grounding:
  - Implemented in: `AttackHarness.inject_memory_graft`
  - Evidence: `results/injection_only_runs.log`; `results/memory_dump_memory_graft_AFTER.json`

```mermaid
sequenceDiagram
  participant A as Attacker
  participant DB as MemoryDB
  participant R as Retriever
  participant S as Supervisor
  participant W as Worker
  participant PX4 as PX4
  participant LG as Logger
  A->>DB: inject success story
  S->>R: retrieve context
  R->>DB: search topk
  DB-->>R: zombie log
  R-->>S: context with success
  S->>W: plan tasks
  W->>PX4: execute
  W->>LG: log outcome
```

## Attack A14: Temporal confusion (Scenario: `temporal`)
- Goal: inject conflicting hazard and “status update safe” messages with a time-like marker.
- Where it hits the pipeline: episodic ingestion -> planning conflict resolution.
- Step-by-step (numbered bullets):
  1) (Attacker) SENDS/RECEIVES: hazard inserted; Evidence: `INFO: [POISON] Logged episode for Drone 1`; Repo: `AttackHarness.inject_temporal_confusion` (`results/injection_only_runs.log`)
  2) (Attacker) SENDS/RECEIVES: status update inserted; Evidence: `INFO: [POISON] Logged episode for Drone 99`; Repo: `AttackHarness.inject_temporal_confusion` (`results/injection_only_runs.log`)
  3) (Supervisor) SENDS/RECEIVES: plan JSON; Evidence: TBD; Repo: `SupervisorAgent.plan_mission`
- LLM input vs output:
  - Retrieved context: hazard plus status update (see `results/memory_dump_temporal_AFTER.json`).
  - Output: `MissionPlan` JSON.
  - Plan change: model may treat status update as more recent (logs TBD).
- Why it succeeded (root weakness): time is spoofable in text; ranking is cosine-only.
- Success Rate: TBD (not present).
- Mitigations (3–5):
  - Timestamp-aware ranking (retrieval); overhead medium.
  - Validate time markers on ingestion (ingestion); overhead low; implementation TBD.
  - Conservative conflict policy (prompt); overhead low.
- Repo grounding:
  - Implemented in: `AttackHarness.inject_temporal_confusion`
  - Evidence: `results/injection_only_runs.log`; `results/memory_dump_temporal_AFTER.json`

```mermaid
sequenceDiagram
  participant A as Attacker
  participant DB as MemoryDB
  participant R as Retriever
  participant S as Supervisor
  participant W as Worker
  participant PX4 as PX4
  participant LG as Logger
  A->>DB: inject hazard
  A->>DB: inject status update
  S->>R: retrieve context
  R->>DB: search topk
  DB-->>R: hazard and update
  R-->>S: conflicting context
  S->>W: plan tasks
  W->>PX4: execute
```

## Attack A15: Keyword-dense override (PoisonedRAG-lite) (Scenario: `rag_lite`)
- Goal: insert keyword-dense override rule intended to dominate retrieval and interpretation.
- Where it hits the pipeline: semantic ingestion -> retrieval -> planning (and fallback bypass if triggered).
- Step-by-step (numbered bullets):
  1) (Attacker) SENDS/RECEIVES: override inserted; Evidence: `INFO: [POISON_RULE] Added semantic rule: SAFETY_OVERRIDE: SECTOR A. Report:`; Repo: `AttackHarness.inject_poisoned_rag_lite` (`results/injection_only_runs.log`)
  2) (Retriever) SENDS/RECEIVES: override ranks high; Evidence: TBD; Repo: `DatabaseManager.find_similar_rules`
  3) (Supervisor) SENDS/RECEIVES: plan JSON; Evidence: TBD; Repo: `SupervisorAgent.plan_mission` / `_fallback_plan`
- LLM input vs output:
  - Retrieved context: hazard rule plus override rule (see `results/memory_dump_rag_lite_AFTER.json`).
  - Output: `MissionPlan` JSON.
  - Plan change: similarity hijack plus authority language (logs TBD).
- Why it succeeded (root weakness): similarity-only retrieval and no provenance checks for override rules.
- Success Rate: TBD (not present).
- Mitigations (3–5):
  - Authenticate override rules (ingestion/retrieval); overhead medium.
  - Length/keyword normalization (retrieval); overhead medium.
  - Remove keyword-based bypass (planner); overhead low.
- Repo grounding:
  - Implemented in: `AttackHarness.inject_poisoned_rag_lite`
  - Evidence: `results/injection_only_runs.log`; `results/memory_dump_rag_lite_AFTER.json`

```mermaid
sequenceDiagram
  participant A as Attacker
  participant DB as MemoryDB
  participant R as Retriever
  participant S as Supervisor
  participant W as Worker
  participant PX4 as PX4
  participant LG as Logger
  A->>DB: inject override rule
  S->>R: retrieve context
  R->>DB: search topk
  DB-->>R: override item
  R-->>S: context with override
  S->>W: plan tasks
  W->>PX4: execute
  W->>LG: log outcome
```

---

<a id="chapter-6-results-success-rates--analysis"></a>
# Chapter 6 — Results (success rates + analysis)

## 6.1 Aggregate success evidence (repo-grounded)

`results/attack_results_log.md` reports:
- Total attacks implemented: 10
- Attack success rate: 90% (9/10 achieved intended effect)

Per-scenario X/Y counts for the integrated runner are TBD (not present in logs/repo).

## 6.2 Injection-stage verification (repo-grounded)

`results/injection_only_runs.log` shows that each scenario key triggers the expected injection routines and produces poisoned rows, for example:
- `hazard_a`: `INFO: [Memory] Episodes=3(poisoned 3); Rules=1(poisoned 1)`
- `dilution`: `INFO: [Memory] Episodes=50(poisoned 50); Rules=0(poisoned 0)`

## 6.3 Hardware-layer logs (repo-grounded)

MAVSDK logs exist in `mavsdk_50051.log` and `mavsdk_50052.log`. Linking a specific PX4 event to a specific `SCENARIO` run is TBD (not present in logs/repo).

---

<a id="chapter-7-mitigations-mapped-to-attacks"></a>
# Chapter 7 — Mitigations (mapped to attacks)

## 7.1 Mitigations (implementation points)

- M1 Filter poisoned rows in retrieval (blocks most injection-based attacks)
  - Implement in: `uav_project/core/database.py :: DatabaseManager.find_similar_episodes` and `find_similar_rules`
- M2 Authenticate safety-critical rule types (OVERRIDE, SUMMARY, CORRECTION)
  - Implement in: DB schema + `MemoryInterface.add_rule` + retrieval filters
- M3 Spatial/time binding for rules and episodes
  - Implement in: `DatabaseManager.find_similar_*` (use timestamp + `location_json`)
- M4 Flood controls and diversity-aware retrieval
  - Implement in: ingestion rate limits + retrieval reranking
- M5 Executor-side safety gate
  - Implement in: `uav_project/agents/worker.py :: WorkerAgent.execute_task` (pre-exec validation)

## 7.2 Coverage matrix (simple)

Legend: yes/no indicates “likely blocks if implemented as described.”

| Mitigation | A1 | A2 | A3 | A4 | A5 | A6 | A7 | A8 | A9 | A10 | A11 | A12 | A13 | A14 | A15 |
|:--|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| M1 filter poisoned rows | yes | yes | yes | yes | yes | yes | no | yes | yes | yes | yes | yes | yes | yes | yes |
| M2 signed rules | no | no | no | no | no | no | no | yes | yes | yes | yes | yes | no | no | yes |
| M3 spatial/time binding | no | no | no | no | yes | no | no | no | no | no | no | no | no | yes | no |
| M4 flood+diversity | no | no | no | no | no | yes | no | no | no | no | no | no | no | no | no |
| M5 executor gate | partial | partial | partial | partial | partial | yes | yes | yes | yes | yes | yes | yes | yes | yes | yes |

---

<a id="chapter-8-reproducibility-commands"></a>
# Chapter 8 — Reproducibility (commands)

Integrated runner:
- Runner: `uav_project/minja_run.py`
- Scenario selector: `SCENARIO`
- Reset DB: `rm -f mission_memory.db`

Clean/control:
```bash
rm -f mission_memory.db && export SCENARIO=baseline && python uav_project/minja_run.py
```

Attack scenarios:
```bash
rm -f mission_memory.db && export SCENARIO=hazard_a && python uav_project/minja_run.py
rm -f mission_memory.db && export SCENARIO=hazard_b && python uav_project/minja_run.py
rm -f mission_memory.db && export SCENARIO=hazard_2 && python uav_project/minja_run.py
rm -f mission_memory.db && export SCENARIO=energy_b && python uav_project/minja_run.py
rm -f mission_memory.db && export SCENARIO=stale_hazard && python uav_project/minja_run.py
rm -f mission_memory.db && export SCENARIO=dilution && python uav_project/minja_run.py
rm -f mission_memory.db && export SCENARIO=dilution_prompt && python uav_project/minja_run.py
rm -f mission_memory.db && export SCENARIO=normative && python uav_project/minja_run.py
rm -f mission_memory.db && export SCENARIO=spoofing && python uav_project/minja_run.py
rm -f mission_memory.db && export SCENARIO=spoofing_refined && python uav_project/minja_run.py
rm -f mission_memory.db && export SCENARIO=self_summary && python uav_project/minja_run.py
rm -f mission_memory.db && export SCENARIO=minja_query && python uav_project/minja_run.py
rm -f mission_memory.db && export SCENARIO=memory_graft && python uav_project/minja_run.py
rm -f mission_memory.db && export SCENARIO=temporal && python uav_project/minja_run.py
rm -f mission_memory.db && export SCENARIO=rag_lite && python uav_project/minja_run.py
```

Env vars (repo-grounded via `uav_project/config.py :: Config`):
- `LLM_API_BASE`, `LLM_MODEL_NAME`, `EMBEDDING_MODEL`, `OPENAI_API_KEY`
- `DRONE1_PORT`, `DRONE2_PORT`, `SIMULATION_IP`, `API_PORT`

---

<a id="appendix--repo-map--glossary"></a>
# Appendix — Repo Map + Glossary

## A.1 Repo map (Discovery)

Primary integrated system (`uav_project/`):
- Entrypoints: `uav_project/minja_run.py :: run_minja`, `uav_project/main.py :: main`
- Memory + retrieval: `uav_project/interfaces/memory_interface.py :: MemoryInterface`, `uav_project/core/database.py :: DatabaseManager`
- Planner: `uav_project/agents/supervisor.py :: SupervisorAgent.plan_mission`
- Executor: `uav_project/agents/worker.py :: WorkerAgent.execute_task`
- Hardware bridge: `uav_project/interfaces/drone_interface.py :: DroneInterface`
- Attack registry: `uav_project/core/attack_harness.py :: AttackHarness.inject_scenario`

Terminal/log artifacts:
- `results/injection_only_runs.log` (injection-stage terminal output for all scenarios)
- `results/attack_results_log.md` (aggregate and narrative outcomes)
- `results/memory_dump_*_{BEFORE,AFTER}.json` (DB snapshots for some scenarios)
- `mavsdk_50051.log`, `mavsdk_50052.log` (MAVSDK server logs)

Other attack prototypes (separate codebases; not integrated `uav_project/` runner):
- `normative_poisoning_s1-master/...`
- `context_dilution_s2-master/...`
- `memory_rewriting_s3-master/...`
- `compromised_buffer_c1-master/...`
- `scribe_poisoning_c2-master/...`
- `infinite_thread_drift_c3-master/...`

## A.2 Scenario keys

Defined in `uav_project/core/attack_harness.py :: AttackHarness.inject_scenario` unless noted:
- `baseline`
- `hazard_a`, `hazard_b`, `hazard_2`, `energy_b`, `stale_hazard`
- `dilution`, `normative`, `spoofing`, `spoofing_refined`, `self_summary`
- `minja_query`, `memory_graft`, `temporal`, `rag_lite`

Prompt-only:
- `dilution_prompt` in `uav_project/agents/supervisor.py :: SupervisorAgent._use_dilution_prompt`

## A.3 Glossary

- MemoryDB: SQLite file `mission_memory.db` (`uav_project/core/database.py :: DatabaseManager`)
- Retriever: `MemoryInterface.retrieve_context` + `DatabaseManager.find_similar_*`
- Supervisor: `SupervisorAgent` (LLM planning)
- Worker: `WorkerAgent` (task execution + episodic logging)
- PX4: SITL autopilot via MAVSDK (`DroneInterface`)

