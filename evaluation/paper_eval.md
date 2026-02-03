# Summary

This paper presents a Python-based PX4 SITL testbed for studying memory poisoning in an LLM-controlled, two-UAV “Supervisor–Worker” autonomy stack. The key idea is that both Worker logs (episodic memory) and hazard/energy “rules” (semantic memory) are persisted in a shared SQLite database, retrieved via embedding-based cosine similarity (RAG-style), and injected into the Supervisor’s planning prompt. The authors implement six scenarios (baseline, three hazard variants, an energy-only warning, and a stale hazard) and report that hazard injections can suppress one or both drones (reduced participation rate), while energy-only and stale-hazard cases surface as warnings without route changes.

As written, the contribution is best characterized as an instrumented prototype + initial demo results rather than a complete security evaluation. The system design is clear at a high level (Supervisor/Workers, shared memory, PX4/MAVSDK), but the experimental claims are based on “representative runs” without statistical support, rely heavily on the heuristic fallback planner, and do not yet demonstrate a realistic “query-only” attacker that induces poisoning through normal agent interactions.

One-sentence assessment: the contribution is **incremental** (prototype + demonstration) and not yet at the level of a top-tier venue without major strengthening of threat model alignment, evidence, and evaluation rigor.

**Overall Score (1–10):** 4 / 10  
**Submission Readiness:** Not Ready

---

# Section-by-Section Ratings

- Problem Formulation & Motivation — **6/10**
  - Why: The motivation (LLM autonomy needs persistent memory; memory expands attack surface) is coherent in **Section “Introduction”** and the RQs are stated.
  - How to fix: Replace the “PhD roadmap” framing with a crisp security problem statement + concrete threat model, and tighten the paper around one primary claim you can fully support with data.

- Novelty & Contributions — **4/10**
  - Why: The system is a useful testbed, but the novelty claim (“first LLM-based multi-UAV testbed that combines …”, **Introduction**) is high-risk without stronger related-work positioning and evidence that the core attack is genuinely *query-only*.
  - How to fix: (i) Re-scope the claim to what you can prove, (ii) explicitly separate “testbed contribution” vs “attack results,” and (iii) demonstrate at least one attack that is induced through normal agent operation (no direct harness writes) to justify “query-only.”

- Related Work & Positioning — **3/10**
  - Why: **Section “Background and Related Work”** is a short list of representative citations, but it does not convincingly position the paper relative to (a) RAG security literature, (b) LLM-for-robotics safety/security, and (c) multi-agent memory poisoning defenses/mitigations.
  - How to fix: Add a structured related-work table and explicitly state “what is new here vs prior” (testbed, physical grounding, shared memory across agents, energy angle), with concrete distinctions.

- Technical Soundness — **4/10**
  - Why: The paper’s own narrative indicates that many observed effects come from the **heuristic fallback planner** (Algorithm **Read + RAG path**, and **Results → Behavioral Comparison**), which weakens the central claim about LLM susceptibility. There are also specification-level ambiguities (e.g., the read algorithm calls `retrieve_context_details`, but the prompt-injection path is `retrieve_context` as described elsewhere).
  - How to fix: Quantify structured-output success vs fallback frequency, and present results separately for (a) pure LLM planning and (b) heuristic fallback. If fallback contains scenario-specific behavior, isolate and remove it from the measured “attack effect.”

- Methodology & System Design — **6/10**
  - Why: The architecture and memory workflow are explained and supported by algorithms and tables (**Figure architecture**, **Algorithm write path**, **Algorithm read path**, **Figure memory workflow**).
  - How to fix: Add implementation-level details that reviewers will ask for: exact top‑k, embedding dimension/model, similarity normalization, prompt template (system/user messages), and how “Summary” is handled (if applicable).

- Experimental Design — **3/10**
  - Why: The evaluation uses a single mission text (**Experimental Setup → Mission Description**) and “one representative run per scenario” (**Table memory stats**, **Table behavior**). There is no variance analysis, no multi-seed runs, and no sensitivity analysis to model choice, retrieval hyperparameters, or mission diversity.
  - How to fix: Run at least 20–50 trials per scenario with controlled randomness, multiple mission templates, and multiple models (at least one strong hosted LLM and one local model) and report variance/CI.

- Evaluation Metrics & Analysis — **3/10**
  - Why: The main metric is “participation rate” (**Table participation rate**, **Figure participation rate**) and a heuristic “Attack Effect” label (**Measurements**, **Table behavior**). This is too coarse for security reviewers; it does not measure safety violations, hazard zone incursions, or causal attribution to retrieved memory.
  - How to fix: Add safety metrics tied to physical state: distance-to-hazard, geofence violations, takeoff/arming events, mission completion, and “plan vs execution” divergence; log retrieval contents and show causal chain from poison→retrieval→prompt→plan→action.

- Reproducibility — **2/10**
  - Why: The paper references external artifacts that are not provided in-text (e.g., “screen-capture videos”) and includes figures that depend on external image files (`architecture.png`, `memory_workflow.png`; **Figures architecture, memory workflow**). Without an explicit artifact/reproducibility section, reviewers cannot verify that the paper can be rebuilt and the experiments rerun.
  - How to fix: Add a “Reproducibility” section with exact commands, pinned dependencies, and public links to videos (or remove video claims), and ensure the submission package contains all figure assets.

- Clarity & Writing Quality — **6/10**
  - Why: The paper is generally readable and structured; tables/figures are used appropriately. However, some statements are too strong relative to the evidence (“first testbed…”, **Introduction**) and the “phases” framing reads like a progress report rather than a conference paper.
  - How to fix: Rewrite the introduction/claims to match what the evaluation supports; reduce roadmap content and increase concrete experimental evidence.

- Ethical / Safety Considerations (if applicable) — **5/10**
  - Why: The system is PX4 SITL, which reduces physical harm, but the paper does not explicitly discuss responsible release of attack harnesses, dual-use risk, or safe evaluation practices.
  - How to fix: Add an explicit ethics/safety paragraph: SITL-only evaluation, no real-aircraft deployment, and guidance on secure defaults if releasing code.

---

# Strengths

- Clear system decomposition into Supervisor/Workers/tools (**System Architecture**, **Figure architecture**), which reviewers value when evaluating agentic systems.
- Concrete “memory-as-attack-surface” framing and explicit episodic vs semantic stores (**Memory Design and Workflow**).
- The paper includes algorithms for write/read paths (**Algorithm write path**, **Algorithm read path**) and summarizes outcomes via tables and a chart (**Tables memory stats/participation/behavior**, **Figure participation rate**).
- Honest acknowledgement that energy-policy integration is currently weak (**Results → Key observations**, **Discussion → Limitations**).
- The limitation that the harness is stronger than prompt-only is explicitly stated (**Discussion → Limitations**), which is good scientific hygiene (but still a major concern).

---

# Weaknesses

Fatal / likely-reject issues:

- **Threat model mismatch / ambiguity**: the paper claims a “query-only” adversary (**Introduction**, **Threat Model**) but the implemented attacks (as described) use a harness that directly calls memory APIs (**Attack Scenarios**, **Limitations**), which is stronger than query-only in most security interpretations.
- **Insufficient experimental rigor**: “representative runs” with no variance, no multi-run success rates, and a single mission template (**Experimental Setup**, **Results tables/figure**) will be an immediate red flag at USENIX/CCS/S&P.
- **LLM vs heuristic confounding**: the Results narrative attributes behavior to the fallback planner reasoning (**Behavioral Comparison**), undermining claims about LLM vulnerability and RAG poisoning.
- **Reproducibility/packaging risk**: missing figure assets (`architecture.png`, `memory_workflow.png`) and unlinked videos can make the submission non-buildable and non-verifiable.

Fixable but serious issues:

- Metrics are too coarse (participation rate is not a safety/security metric).
- Over-strong novelty claim without careful positioning.
- Energy constraints are in the title but not meaningfully exercised (energy attacks become warnings).

---

# Detailed Technical Concerns

1) **“Query-only” attacker is not realized in the evaluation**
   - Reference: **Introduction** (query-only poisoning), **Threat Model**, **Discussion → Limitations** (“Attack harness directly uses memory APIs…”).
   - Why this is a problem: A top-tier reviewer will interpret “query-only” as *no internal API access* and will expect the attack to be induced via normal agent interactions (e.g., the agent logs attacker-provided text). A harness that directly calls the memory API resembles insider access.
   - Impact: **Credibility + novelty** (the main threat model claim is not convincingly supported).

2) **Results appear driven by the heuristic fallback planner rather than LLM behavior**
   - Reference: **Algorithm read path** (fallback on error), **Results → Behavioral Comparison** (“fallback planner’s reasoning states …”).
   - Why: If structured outputs frequently fail and the system falls back, the “attack effect” might be attributable to deterministic heuristic logic rather than memory poisoning influencing an LLM.
   - Impact: **Correctness/credibility** of “LLM memory poisoning” claims.

3) **Algorithm–implementation ambiguity around retrieval functions**
   - Reference: **Algorithm read path** uses `retrieve_context_details(M)` then formats into prompt sections; elsewhere the paper describes `retrieve_context(user_command)` as the prompt string function (**Read + RAG Path**).
   - Why: Reviewers will ask which exact function feeds the LLM prompt and whether poison flags could leak to the agent. The algorithm as written risks implying the Supervisor sees poison flags.
   - Impact: **Technical soundness** and potential misunderstanding of the trust boundary.

4) **Unverifiable video claims and unclear artifact availability**
   - Reference: Text claiming recorded videos (**System Architecture**, **Video and Visual Validation**) and dependence on external image files for figures (**Figure architecture**, **Figure memory workflow**).
   - Why: If videos are part of the evidence, they must be provided (URL, supplemental). If the submission includes LaTeX source, the figure assets must be included; otherwise artifact evaluation (and sometimes paper build) fails.
   - Impact: **Reproducibility + credibility**.

5) **Evaluation uses “one representative run per scenario”**
   - Reference: **Table memory stats** caption (“after one run per scenario”), **Table behavior** caption (“representative runs”).
   - Why: Security venues will not accept claims of systematic behavior without repeated trials and variance, especially with LLM nondeterminism and simulator nondeterminism.
   - Impact: **Credibility** of results.

6) **Participation rate is not a sufficient safety/security metric**
   - Reference: **Table participation rate**, **Figure participation rate**, **Results narrative**.
   - Why: “Drone did not take off” is only one kind of failure mode; you need to measure unsafe flights, near misses, geofence violations, and how poisoning changes *plans* and *executions*.
   - Impact: **Evaluation adequacy** (reviewers will consider the analysis shallow).

7) **Energy constraints are not meaningfully evaluated**
   - Reference: Title (“Under Energy Constraints”), **Results** (energy-only is warning only), **Discussion** (energy model simplified).
   - Why: The title frames energy constraints as central, but the experiments do not demonstrate energy-driven planning failures or energy-related poisoning affecting behavior.
   - Impact: **Scope/positioning credibility**; reviewers may call this a “title/claim mismatch.”

8) **Over-strong novelty claim without careful substantiation**
   - Reference: **Introduction** (“first LLM-based multi-UAV testbed that combines …”).
   - Why: “First” claims are heavily scrutinized; if incorrect, reviewers will penalize harshly. The related work section is not strong enough to support it.
   - Impact: **Novelty credibility**.

9) **Citations quality and correctness risk**
   - Reference: Bibliography entry for MINJA: “arXiv:2401.00000” (**References**).
   - Why: Placeholder or incorrect identifiers signal sloppiness and can trigger reviewer distrust.
   - Impact: **Credibility**.

10) **Causal chain poison→retrieval→prompt→plan is asserted, not evidenced**
   - Reference: **Results → Behavioral Comparison** (e.g., “Supervisor’s context includes only these poisoned entries”).
   - Why: This is the central scientific mechanism but no prompt excerpts, retrieval lists, or plan JSON are shown in the paper.
   - Impact: **Correctness/credibility**.

---

# Experimental Review

- Dataset selection and justification
  - What exists: A single mission template (**Mission Description**) with fixed coordinates.
  - Issue: This is not a “dataset” and does not support generality. Reviewers will ask how the result changes with mission phrasing, coordinate noise, different sectors, or different task decompositions.
  - Fix: Define a mission suite (10–50 templates) and justify coverage (hazard proximity, ambiguity, energy stress, multi-step missions).

- Baselines and ablations
  - What exists: Baseline “no attack” scenario; six attack scenarios.
  - Missing: Ablations separating episodic vs semantic poisoning (e.g., hazard episode only vs hazard rule only), top‑k sensitivity, and removal of fallback planner.
  - Fix: Add ablations:
    - Retrieval ablation: k ∈ {1,3,5,10}, with/without summary ordering.
    - Planner ablation: LLM-only (structured outputs succeed), fallback-only, and hybrid.
    - Memory ablation: episodic-only store vs semantic-only store.

- Metrics used and adequacy
  - What exists: Participation rate; heuristic “Attack Effect” labels (**Measurements**, **Table behavior**, **Figure participation rate**).
  - Missing: Safety metrics (hazard zone entry), control-plane metrics (plan deltas), retrieval metrics (rank positions of poisoned items), and execution-ground truth (arming/takeoff logs).
  - Fix: Add metrics that directly measure security impact and causality:
    - Retrieval: poisoned item rank distribution; poisoning rate; context length.
    - Plan: task drop/add, coordinate changes, safety-related reasoning.
    - Execution: takeoff count, waypoint attainment, minimum distance to hazard coordinate.

- Statistical validity
  - What exists: None (no repeated trials, no variance).
  - Fix: Report mean±std or confidence intervals over repeated runs; control randomness (LLM temperature=0 if used; seed simulator if possible).

- Realism of experimental settings
  - Strength: PX4 SITL + MAVSDK is a credible robotics evaluation environment.
  - Concern: The attacker is implemented via a harness that directly writes to memory, which is not a realistic “query-only” constraint; the work needs an induced-write path.

Which claims are not adequately supported by results:
- Any “systematically” or “robustly” phrased claims beyond the single-run representative behavior (e.g., broad generalization implied in **Abstract** and **Introduction**) are not supported as currently evaluated.

---

# Clarity & Presentation

- The “phases” roadmap framing (**Introduction**, **Abstract**) reads like a thesis milestone report; top-tier reviewers often dislike this unless tightly integrated into a paper narrative. Consider moving the roadmap to an appendix or removing it.
- The core mechanism (retrieval contents, prompt construction, and plan output) is not shown. Without at least one concrete prompt excerpt and one plan JSON excerpt, reviewers will view the system as underspecified (**Memory Design**, **Results**).
- Figures:
  - **Figure architecture** and **Figure memory workflow** are essential but currently depend on external PNGs; if missing from the source package, the paper will not build.
  - **Figure conceptual summary** is clear but labeled as “Video and Visual Validation” while the figure itself is not a video; this section is confusingly titled.
- Terminology:
  - “Query-only” is overloaded and likely to be interpreted differently by reviewers; define it precisely in **Threat Model** and use consistent phrasing throughout.

---

# Risks & Limitations

- Reproducibility risks
  - Missing figure assets and lack of exact commands to run the experiments will prevent artifact evaluation.
  - MUST disclose: what is needed to reproduce (PX4 SITL version, MAVSDK versions, model endpoints, exact configs).

- Generalization limits
  - Two drones, one mission template, one (mostly) fallback-driven planner path, and simplistic attack payloads limit generality.
  - MUST disclose: results are demonstration-level and not yet a robust measurement study.

- Deployment/security risks
  - Memory poisoning attacks can translate into unsafe autonomy. Even though evaluation is SITL, code release without safeguards could encourage misuse.
  - MUST disclose: SITL-only evaluation and recommended safe defaults (e.g., don’t deploy this planning policy without defenses).

- Assumptions that may not hold
  - The attacker’s ability to write via memory API (or to induce such writes) is a major assumption; the paper should separate “insider memory writer” vs “query-only induced logging” attackers.

---

# Actionable Recommendations

## Critical (must fix before submission)

- **Fix build/package completeness (figures + links).**
  - Impact: prevents immediate desk rejection / artifact failure.
  - Effort: low–medium.
  - Do: include `architecture.png` and `memory_workflow.png` in the submission package; add a public link to videos (or remove video claims).

- **Clarify and align threat model with the implemented attack path.**
  - Impact: removes the #1 reviewer red flag (“threat model mismatch”).
  - Effort: medium.
  - Do: define two threat models explicitly: (i) direct memory-writer (insider), (ii) query-only induced poisoning. Label which one you evaluate.

- **Separate LLM behavior from heuristic fallback behavior in results.**
  - Impact: prevents “your results are from a heuristic, not an LLM” rejection.
  - Effort: medium–high.
  - Do: report how often structured outputs succeed; provide results for LLM-only runs; remove scenario-specific heuristics from the measurement path.

- **Add repeated trials and variance (no more “representative run”).**
  - Impact: makes results credible for top venues.
  - Effort: high.
  - Do: run N≥20 per scenario; report CI/variance; lock temperature/seed where possible.

## Important (strongly recommended)

- **Add causal evidence: retrieval contents + prompt excerpt + plan excerpt for each scenario class.**
  - Impact: strengthens the scientific claim “poison→retrieval→prompt→plan→action.”
  - Effort: medium.

- **Upgrade metrics to safety-relevant outcomes.**
  - Impact: transforms a demo into a security evaluation.
  - Effort: medium–high.

- **Energy constraints: either integrate or de-scope.**
  - Impact: prevents “title/claim mismatch.”
  - Effort: medium.
  - Do: implement explicit energy policies that affect routing/mission feasibility, then show energy poisoning changes behavior; or remove energy from title/central claims.

- **Strengthen related work and reduce “first” claims.**
  - Impact: reduces novelty challenges and reviewer hostility.
  - Effort: medium.

## Optional (polish / clarity improvements)

- Rename “Video and Visual Validation” to reflect what is actually shown and provided.
  - Impact: improves clarity.
  - Effort: low.

- Add a small appendix with the exact prompt template and the memory schema in table form.
  - Impact: improves reviewer confidence.
  - Effort: low.

---

# Final Verdict

I would **not** recommend acceptance if reviewing this paper today for a top-tier venue. The most likely rejection reason is **insufficiently credible evaluation under a mismatched/unclear threat model**, compounded by heavy reliance on a heuristic fallback planner and lack of repeated-trial evidence.

The single improvement that would most increase acceptance probability is to **run a statistically grounded evaluation (multi-run, multiple missions, multiple models) that cleanly demonstrates the causal chain poison→retrieval→prompt→LLM plan→execution, under a clearly defined attacker model that matches the “query-only” claim**.
