# Summary of Dr. Anyi Liu's Comments and Paper Revision Plan

## Executive Summary

Dr. Liu identifies **one central, critical issue** that permeates the entire paper: **the scope is too narrow**. The paper is overly constrained to RAG-centric memory, limiting its generality and reducing it from a potential Tier-1 publication to a Tier-3 case study. The key transformation required is repositioning memory injection as a **cross-layer agent-state attack primitive** that affects planning, tool use, and action execution—not treating memory as an isolated component.

---

## Part 1: Key Points from All Advisor Comments

### 1.1 Fundamental Scope Issues (CRITICAL)

| Location | Comment Summary |
|----------|-----------------|
| **Abstract** | Current contribution is overly constrained to RAG-centric memory. Must generalize beyond RAG to cover broader agent memory designs (episodic, semantic, procedural skills, coordination memory). |
| **Abstract** | Attack scope is too narrow—focuses only on memory retrieval effects. Must demonstrate capability impact: memory-to-skill degradation and mission-level performance changes. |
| **Abstract** | Need a comprehensive taxonomy grounded in state-of-the-art agent memory attacks with more comprehensive attack vectors (query-only injection, indirect poisoning, cross-agent propagation). |
| **Abstract** | **CRITICAL**: Position memory injection as a cross-layer agent-state attack primitive. This makes the difference between Tier-1 and Tier-3 papers. |

### 1.2 Introduction Issues

| Location | Comment Summary |
|----------|-----------------|
| **Introduction** | Currently frames the problem almost exclusively through RAG-based agents—must be broadened. |
| **Introduction** | Should be rewritten as the LAST PART of the paper after methodology is developed. |
| **Introduction** | Must distinguish external memory (RAG, vector stores) from internal agent memory (episodic summaries, reflection buffers, procedural skills). |
| **Introduction** | Clarify whether UAV is the main contribution or a case study supporting a general agent-security argument. |
| **Introduction** | Add a problem statement defining *agent memory* as a superset (episodic, semantic, procedural, coordination), then situate RAG as one instantiation. |

### 1.3 Background & Related Work Issues

| Location | Comment Summary |
|----------|-----------------|
| **Section 2** | Should be rewritten after methodology is better developed. |
| **Section 2** | Research about state-of-the-art is insufficient. Need comprehensive research. |
| **Section 2** | Should separate (i) indirect prompt injection, (ii) RAG corpus poisoning and retrieval backdoors, (iii) agent long-term memory poisoning, (iv) multi-agent propagation attacks. |
| **Section 2** | Add comparison table highlighting what threat model covers vs. what it does not. |
| **Section 2 - RAG** | Explicitly state RAG is one implementation of external memory, not the definition of agent memory. Contrast with reflection buffers and skill libraries. |
| **Section 2 - LLM Systems** | Explicitly present the autonomy loop (observe, plan, act) and highlight where memory is read/written to clarify trust boundaries. |
| **Section 2 - Attacks** | Differentiate transient prompt injection from persistent memory poisoning. Add retrieval backdoor and trigger attacks. A comprehensive attack vector taxonomy is needed. |

### 1.4 System Architecture & Threat Model Issues (MAJOR)

| Location | Comment Summary |
|----------|-----------------|
| **Section 3** | **BIGGEST KILLING POINT**: Architecture lacks vision in scope of Multi-Agent UAV system. Still unclear what the system looks like or key components/connections. |
| **Section 3** | Overly coupled to specific memory implementation—scope too narrow. Need more sophisticated and general "Multi-Agent UAV Architecture." |
| **Section 3** | Abstract memory as a logical module with explicit trust boundaries (ingestion, storage, retrieval, reasoning, action). |
| **Section 3** | Expand threat model to include query-only memory injection, indirect poisoning via observations/communications, and cross-agent propagation. |
| **Section 3** | Need a diagram marking trusted vs. untrusted channels. |
| **Section 3 - UAV Arch** | Subsection jumps directly to "hierarchical multi-agent system" without justification. Need transitions explaining why this formulation. |
| **Section 3 - Success** | Make success conditions measurable and multi-layered: memory-level, decision-level, action-level, and mission-level. |
| **Section 3 - Surfaces** | Categorize attack surfaces by lifecycle stage: ingestion, storage, retrieval, reasoning, action execution. Include multi-agent communication as explicit surface. Need visualization diagram. |
| **Section 3 - Adversary** | "WHAT'S CONTENT???" — Define canonical adversaries (query-only, content injector, insider, compromised agent) and map each experiment to one profile. Integrate with above subsections. |
| **Section 3 - Compromise** | Justify purpose of this subsection. Clarify realism of each compromise vector. Combine similar vectors. |

### 1.5 Taxonomy Issues

| Location | Comment Summary |
|----------|-----------------|
| **Section 4** | The section is "definitely AI-generated" and greatly overlaps with previous section. |
| **Taxonomy (15 Vectors)** | 15 vectors are useful engineering artifact but do NOT constitute publication-grade taxonomy. |
| **Taxonomy** | Define explicit taxonomy axes (memory substrate, lifecycle stage, attacker capability, objective, persistence). |
| **Taxonomy** | Map each of the 15 attacks into those axes (one table is enough). |
| **Taxonomy** | Combine redundant vectors and justify why each vector is distinct. |
| **Taxonomy** | Currently reads like a list—should read like a structured scientific classification. |
| **Tier 1 (DoS)** | Denial-of-service can appear trivial. Include stealthier attacks that preserve benign performance and only trigger under specific conditions. |
| **Tier 2 (Cognitive)** | This tier is central. Strengthen by explaining mechanism—how injected memories override safety logic or create false constraints. |

### 1.6 Skill Degradation Section Issues

| Location | Comment Summary |
|----------|-----------------|
| **Section 5** | Ensure alignment with three main revision goals: generality beyond RAG, memory-to-skill impact, systematic attack taxonomy. |
| **All Subsections** | Multiple subsections marked: "Consider whether this subsection should be expanded, merged, or tightened." |

### 1.7 Implementation & Methodology Issues

| Location | Comment Summary |
|----------|-----------------|
| **Section 6** | Better separate system implementation details from methodological assumptions. |
| **Section 6** | Clearly specify memory write policy, retrieval policy, and memory formatting (attack-critical). |
| **Section 6** | State what attacker can and cannot control in software stack. |
| **Section 6** | Describe reproducibility across runs (random seeds, environment resets, logging). |
| **Metrics** | Add capability and skill metrics. At minimum: mission success rate, time-to-completion, safety violations, persistence metric. |

### 1.8 Evaluation & Results Issues

| Location | Comment Summary |
|----------|-----------------|
| **Section 7** | Evaluation is strong at memory-level effects but NOT sufficient for capability degradation at skill/mission levels. |
| **Section 7** | Add skill-level metrics (policy selection drift, skill failure modes) and mission-level metrics (success rate, time, safety constraint violations). |
| **Section 7** | Measure persistence and recovery (how long attack effect lasts after attacker stops). |
| **Section 7** | Evaluate cross-agent propagation in shared-memory or message-sharing settings. |

### 1.9 Discussion Issues

| Location | Comment Summary |
|----------|-----------------|
| **Section 8** | Opportunity to elevate contribution beyond case study. |
| **Section 8** | Discuss why attacks work in terms of trust boundaries and instruction-data non-separation. |
| **Section 8** | Explain composability—combining memory injection with tool hijacking or indirect prompt injection. |
| **Section 8** | Add short defense discussion as baseline (sanitization, provenance, isolation). |

### 1.10 Mitigation, Limitations, Future Work, Conclusion Issues

| Location | Comment Summary |
|----------|-----------------|
| **Mitigations** | Even if defenses not the focus, propose minimal baseline: provenance tagging, memory sanitation, retrieval filtering, isolation of untrusted content. Explain which defenses work against which attack vectors. |
| **Limitations** | Explicitly acknowledge current experiments target RAG memory. State what's required to generalize to non-RAG memory, especially procedural skills and multi-agent propagation. |
| **Future Work** | Make concrete. Top priorities: (i) non-RAG memory substrates, (ii) memory-to-skill degradation experiments, (iii) cross-agent propagation evaluation, (iv) defense baselines. |
| **Conclusion** | Avoid over-claiming generality. Explicitly restate scope limitations (current evaluation is RAG memory) and most important next step (skill-level capability impact). |
| **Conclusion** | End with concrete revision-ready takeaways: what is demonstrated now, what must be shown to generalize beyond RAG, what metrics define success for memory-to-skill impact. |

### 1.11 Appendix Issues

| Location | Comment Summary |
|----------|-----------------|
| **App A** | Summarize payload design principles and how they differ across attack families. |
| **App B** | Ensure command list covers all experiments including new skill-level evaluations. Document expected outputs and provide minimal sanity-check script. |

### 1.12 Required External Research

| Item | Details |
|------|---------|
| **AlphaSecBench** | Read site and paper: https://github.com/maferrag/AlphaSecBench — Critical for identifying important references in wider spectrum beyond RAG systems. |

---

## Part 2: Reconstructed Paper Structure

### Proposed New Structure

```
Title: Memory Injection Attacks Against Agentic Autonomous Systems:
       A Multi-Layer Threat Analysis with UAV Case Study

1. INTRODUCTION (Write LAST)
   1.1 Motivation: Agent Memory as Critical Infrastructure
   1.2 Problem Statement: Agent Memory Definition
       - Define agent memory as superset (episodic, semantic, procedural, coordination)
       - Position RAG as one instantiation
   1.3 The Cross-Layer Attack Primitive Thesis
       - Memory injection affects planning, tool use, action execution
       - Not an isolated component vulnerability
   1.4 Contributions (Revised)
   1.5 Paper Organization

2. BACKGROUND: Agent Memory Systems
   2.1 Agent Memory Taxonomy
       - External memory (RAG, vector stores)
       - Internal memory (episodic summaries, reflection buffers)
       - Procedural memory (skills, tool-use routines)
       - Coordination memory (shared state, team roles)
   2.2 The Autonomy Loop
       - Observe → Plan → Act cycle
       - Where memory is read and written
       - Trust boundaries at each stage
   2.3 RAG as One Implementation
       - Technical overview
       - Contrast with reflection buffers and skill libraries

3. RELATED WORK (Separate Section)
   3.1 Transient Attacks
       - Direct prompt injection
       - Indirect prompt injection
   3.2 Persistent Attacks
       - RAG corpus poisoning
       - Retrieval backdoors and triggers
       - Agent long-term memory poisoning
   3.3 Multi-Agent Attacks
       - Cross-agent propagation
       - Fleet contamination
   3.4 Positioning Table
       - What our threat model covers vs. does not cover
       - Gap analysis

4. SYSTEMATIC TAXONOMY OF AGENT MEMORY ATTACKS
   4.1 Taxonomy Design Principles
       - Axes: memory substrate, lifecycle stage, attacker capability, objective, persistence
   4.2 Attack Targets (What is Corrupted)
       - Memory content
       - Indexing/retrieval
       - Update policy
       - Persistence mechanisms
   4.3 Attack Vectors (How Corruption is Introduced)
       - Direct memory injection
       - Query-only injection
       - Indirect poisoning (observations, communications, tool outputs)
       - Cross-agent propagation
   4.4 Comprehensive Taxonomy Table
       - Map all attack variants to axes
       - Clear distinction criteria
   4.5 The 15 Attack Instantiations
       - Tier 1: Denial of Service (with stealth variants)
       - Tier 2: Cognitive Manipulation (mechanism explanations)
       - Tier 3: Algorithmic Override

5. MULTI-AGENT UAV SYSTEM ARCHITECTURE
   5.1 Design Rationale
       - Why hierarchical multi-agent (vs. single-agent, peer-to-peer)
       - Transitions and justification
   5.2 System Components and Connections
       - Supervisor Agent
       - Worker Agents
       - Shared Memory Module
       - System Architecture Diagram
   5.3 Memory as Logical Module
       - Trust boundaries: ingestion, storage, retrieval, reasoning, action
       - Trust boundary diagram (trusted vs. untrusted channels)
   5.4 Memory Lifecycle in UAV Context
       - Write policies
       - Retrieval policies
       - Format specifications

6. THREAT MODEL
   6.1 Adversary Profiles
       - Query-only adversary
       - Content injector
       - Insider threat
       - Compromised agent
   6.2 Attack Surfaces by Lifecycle Stage
       - Ingestion surface
       - Storage surface
       - Retrieval surface
       - Reasoning surface
       - Action execution surface
       - Multi-agent communication surface
   6.3 Initial Compromise Vectors (Realistic)
       - Ranked by realism
       - Hypothetical vectors labeled clearly
   6.4 Multi-Layer Success Conditions
       - Memory-level: retrieval contamination
       - Decision-level: plan deviation
       - Action-level: unsafe trajectory
       - Mission-level: task failure, efficiency loss

7. IMPLEMENTATION & METHODOLOGY
   7.1 Simulation Environment
   7.2 Memory System Specification
       - Write policy details
       - Retrieval policy details
       - Format specifications (attack-critical)
   7.3 Attack Injection Protocol
   7.4 Attacker Capability Constraints
       - What attacker can control
       - What attacker cannot control
   7.5 Reproducibility
       - Random seeds
       - Environment resets
       - Logging procedures

8. EVALUATION & RESULTS
   8.1 Memory-Level Metrics
       - Retrieval rank
       - Prompt dominance
       - Stealth
   8.2 Skill-Level Metrics (NEW)
       - Policy selection drift
       - Skill failure modes
       - Skill success rate
       - Time-to-completion
   8.3 Mission-Level Metrics (NEW)
       - Mission success rate
       - Safety constraint violations
       - Efficiency metrics
   8.4 Persistence and Recovery (NEW)
       - Duration of attack effect
       - Recovery time in episodes
       - Self-reinforcement analysis
   8.5 Cross-Agent Propagation (NEW)
       - Partial compromise experiments
       - Fleet-level coordination failures
       - Amplification effects
   8.6 Attack Results Summary
   8.7 The Defense Paradox
   8.8 Retrieval Dynamics Analysis

9. DISCUSSION
   9.1 Why Attacks Work: Trust Boundaries and Instruction-Data Non-Separation
   9.2 Memory Injection as Cross-Layer Primitive
       - Effects on planning
       - Effects on tool use
       - Effects on action execution
   9.3 Composability Analysis
       - Combining with tool hijacking
       - Combining with indirect prompt injection
   9.4 Defense Baseline Discussion
       - Provenance tagging
       - Memory sanitation
       - Retrieval filtering
       - Isolation of untrusted content
       - Which defenses work against which attacks
   9.5 The Security-Capability Tradeoff

10. LIMITATIONS
    10.1 Current Scope: RAG Memory
    10.2 Requirements for Generalization
        - Non-RAG memory substrates
        - Procedural skills
        - Multi-agent propagation
    10.3 Experimental Constraints

11. FUTURE WORK
    11.1 Non-RAG Memory Substrates (Priority 1)
    11.2 Memory-to-Skill Degradation Experiments (Priority 2)
    11.3 Cross-Agent Propagation Evaluation (Priority 3)
    11.4 Defense Baselines (Priority 4)

12. CONCLUSION
    12.1 What is Demonstrated Now
    12.2 What Must Be Shown to Generalize Beyond RAG
    12.3 Success Metrics for Memory-to-Skill Impact

APPENDICES
A. Attack Payloads
   - Payload design principles by attack family
B. Reproduction Commands
   - Complete experiment list including skill-level evaluations
   - Expected outputs documentation
   - Sanity-check script
```

---

## Part 3: Task Plan and Checklist

### Phase 1: Research Foundation (Week 1-2)

#### 1.1 Literature Review
- [ ] Read AlphaSecBench paper and repository thoroughly
- [ ] Survey state-of-the-art agent memory attacks beyond RAG
- [ ] Identify and categorize: indirect prompt injection papers
- [ ] Identify and categorize: RAG corpus poisoning papers
- [ ] Identify and categorize: retrieval backdoor papers
- [ ] Identify and categorize: agent long-term memory poisoning papers
- [ ] Identify and categorize: multi-agent propagation attack papers
- [ ] Create bibliography with 20+ relevant citations

#### 1.2 Taxonomy Development
- [ ] Define taxonomy axes: memory substrate, lifecycle stage, attacker capability, objective, persistence
- [ ] Create master taxonomy table mapping all known attacks
- [ ] Identify gaps in existing attack coverage
- [ ] Map our 15 attacks to taxonomy axes
- [ ] Identify redundant vectors and merge
- [ ] Justify distinctiveness of each remaining vector

### Phase 2: Architecture & Threat Model Revision (Week 2-3)

#### 2.1 System Architecture
- [ ] Create comprehensive system architecture diagram
- [ ] Design memory as logical module with trust boundaries
- [ ] Create trust boundary diagram (trusted vs. untrusted channels)
- [ ] Document memory lifecycle stages
- [ ] Write justification for hierarchical multi-agent choice
- [ ] Add transitions explaining design decisions

#### 2.2 Threat Model Expansion
- [ ] Define 4 canonical adversary profiles with clear capabilities
- [ ] Map each experiment to adversary profile
- [ ] Expand attack surfaces to cover all lifecycle stages
- [ ] Add multi-agent communication as explicit attack surface
- [ ] Create attack surface visualization
- [ ] Develop multi-layer success conditions
- [ ] Rank compromise vectors by realism
- [ ] Label hypothetical vectors clearly

### Phase 3: Experimental Extensions (Week 3-5)

#### 3.1 Skill-Level Metrics Implementation
- [ ] Define explicit skills: search pattern execution, collision avoidance, return-to-home
- [ ] Implement skill success rate measurement
- [ ] Implement time-to-completion measurement
- [ ] Implement skill failure mode classification
- [ ] Implement policy selection drift measurement
- [ ] Run experiments with skill-level metrics

#### 3.2 Mission-Level Metrics Implementation
- [ ] Implement mission success rate tracking
- [ ] Implement safety constraint violation counter
- [ ] Implement efficiency metrics (time, energy, path length)
- [ ] Run experiments with mission-level metrics

#### 3.3 Persistence & Recovery Experiments
- [ ] Design persistence measurement protocol
- [ ] Measure attack effect duration after attacker stops
- [ ] Measure recovery time in episodes
- [ ] Analyze self-reinforcement patterns
- [ ] Document results

#### 3.4 Cross-Agent Propagation Experiments
- [ ] Design partial compromise experiments
- [ ] Implement coordination success metrics
- [ ] Implement synchronization error measurement
- [ ] Implement emergent safety violation detection
- [ ] Run cross-agent experiments
- [ ] Analyze amplification effects

#### 3.5 Stealth Attack Development
- [ ] Design stealth DoS variants that preserve benign performance
- [ ] Implement conditional trigger attacks
- [ ] Test and document results

### Phase 4: Writing Revision (Week 5-7)

#### 4.1 New Sections to Write
- [ ] Write Section 2: Background on Agent Memory Systems
- [ ] Write Section 3: Related Work (separated, with comparison table)
- [ ] Write Section 4: Systematic Taxonomy (publication-grade)
- [ ] Write Section 5: Multi-Agent UAV Architecture (with diagrams)
- [ ] Write Section 6: Threat Model (expanded)
- [ ] Add skill-level results to Evaluation
- [ ] Add mission-level results to Evaluation
- [ ] Add persistence/recovery results to Evaluation
- [ ] Add cross-agent propagation results to Evaluation
- [ ] Write Discussion section on trust boundaries and composability
- [ ] Write defense baseline discussion
- [ ] Revise Limitations to acknowledge RAG scope
- [ ] Revise Future Work with concrete priorities
- [ ] Revise Conclusion with three takeaways

#### 4.2 Section Revisions
- [ ] Revise Abstract to reflect broader scope
- [ ] Write Introduction LAST
- [ ] Update all metric tables with new measurements
- [ ] Add mechanism explanations to Tier 2 attacks
- [ ] Document payload design principles in appendix
- [ ] Update reproduction commands for new experiments
- [ ] Add expected outputs documentation
- [ ] Create sanity-check script

### Phase 5: Figures and Tables (Week 6-7)

#### 5.1 Required New Figures
- [ ] System architecture diagram (comprehensive)
- [ ] Trust boundary diagram
- [ ] Attack surface lifecycle diagram
- [ ] Memory module logical architecture diagram
- [ ] Skill degradation visualization
- [ ] Cross-agent propagation visualization

#### 5.2 Required New Tables
- [ ] Agent memory taxonomy table
- [ ] Related work positioning table (coverage vs. gaps)
- [ ] Comprehensive attack taxonomy table (all axes)
- [ ] Adversary profile capability matrix
- [ ] Attack surface by lifecycle stage table
- [ ] Skill-level metrics results table
- [ ] Mission-level metrics results table
- [ ] Persistence/recovery metrics table
- [ ] Cross-agent propagation results table
- [ ] Defense-to-attack mapping table

### Phase 6: Quality Assurance (Week 7-8)

#### 6.1 Internal Review
- [ ] Check all AI-generated content for originality
- [ ] Remove redundancy between sections
- [ ] Ensure consistent terminology throughout
- [ ] Verify all claims have experimental support
- [ ] Check figure/table references
- [ ] Proofread for clarity

#### 6.2 Scope Verification
- [ ] Verify paper positions memory injection as cross-layer primitive
- [ ] Verify generalization beyond RAG is addressed
- [ ] Verify memory-to-skill impact is demonstrated
- [ ] Verify systematic taxonomy is publication-grade
- [ ] Verify UAV is positioned as case study, not sole contribution

---

## Priority Matrix

| Priority | Task Category | Impact | Effort |
|----------|---------------|--------|--------|
| **P0** | Taxonomy development & related work research | Critical | High |
| **P0** | System architecture & threat model revision | Critical | High |
| **P1** | Skill-level and mission-level experiments | High | High |
| **P1** | Cross-agent propagation experiments | High | Medium |
| **P2** | Persistence/recovery experiments | Medium | Medium |
| **P2** | Stealth attack variants | Medium | Medium |
| **P3** | Defense baseline discussion | Low | Low |

---

## Target Conference Consideration

Dr. Liu asks: "Which conference are you targeting?"

The paper title suggests IEEE format targeting USENIX Security / ACM CCS / NDSS. To meet Tier-1 standards for these venues:

1. **USENIX Security**: Requires strong empirical evaluation, novel threat models, and practical impact
2. **ACM CCS**: Emphasizes systematic analysis and comprehensive coverage
3. **NDSS**: Values real-world applicability and defense discussions

Current state: **Tier-3 case study** (narrow RAG focus, limited metrics)
Target state: **Tier-1 systematic threat analysis** (cross-layer primitive, comprehensive taxonomy, multi-level impact)

---

## Summary of Critical Actions

1. **Broaden scope** from RAG-only to general agent memory systems
2. **Develop publication-grade taxonomy** with explicit axes
3. **Create comprehensive system architecture** with trust boundary diagrams
4. **Expand threat model** to include all lifecycle stages and adversary types
5. **Add skill-level and mission-level metrics** to demonstrate capability impact
6. **Conduct cross-agent propagation experiments**
7. **Position memory injection as cross-layer attack primitive**
8. **Write Introduction LAST** after methodology is solid
9. **Read AlphaSecBench** for comprehensive attack landscape understanding
