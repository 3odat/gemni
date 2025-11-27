This is the critical "blueprint" step. By freezing the design now, you avoid "scope creep" later and ensure your implementation directly supports your Research Questions (specifically regarding energy constraints and integrity checks).

Below is the complete content for your **Phase 2 Deliverable: Design Document & Architecture Specification**.

You can copy this content directly into your internal project documentation or a clean PDF to send to your advisor.

***

# Phase 2 Design Document: System Architecture & Interfaces
**Project:** Memory Attacks and Defenses in Multi-Agent LLM-Controlled UAV Systems
**Date:** November 2025
**Author:** Ibrahim Odat

## 1. Agent Responsibilities (Task 2.1)
The system uses a hierarchical multi-agent architecture to separate high-level reasoning from low-level execution.

### A. Supervisor Agent (The "Planner")
*   **Role:** High-level mission orchestrator.
*   **Responsibilities:**
    1.  Receives natural language mission goals (e.g., "Inspect the northern perimeter").
    2.  Queries **Semantic Memory** *before* planning to identify constraints (e.g., known hazards, energy-heavy zones).
    3.  Decomposes goals into atomic sub-tasks (e.g., `Task A: Fly to [x,y]`, `Task B: Scan sector`).
    4.  Assigns tasks to Worker Agents based on their current status and battery level.
*   **Context Window:** Contains high-level mission state and semantic rules.

### B. Worker Agents (Drone 1 & Drone 2)
*   **Role:** Execution and reactive reporting.
*   **Responsibilities:**
    1.  Receive atomic sub-tasks from the Supervisor.
    2.  Translate sub-tasks into specific **MAVSDK function calls**.
    3.  Monitor execution (Success/Failure).
    4.  **Write to Episodic Memory:** Log the state, action, and outcome immediately after task completion.
*   **Context Window:** Contains local telemetry, immediate surroundings, and recent tool outputs.

### C. Memory Manager (The "Gatekeeper")
*   **Role:** Interface between Agents and the Database.
*   **Responsibilities:**
    1.  Handles embedding generation for retrieval.
    2.  **Phase 6 Preparation (Defense):** This module will eventually house the logic to calculate/verify **MACs (Integrity Tags)** and perform **Cross-Agent Consistency Checks**. It abstracts the security logic away from the LLM agents.

---

## 2. Tool Interfaces (Task 2.2)
The agents interact with the system via these defined Python interfaces (Tool Definitions).

### A. MAVSDK Tools (Control)
*   `arm_and_takeoff(drone_id: int, target_altitude: float) -> str`
*   `goto_position(drone_id: int, lat: float, lon: float, alt: float) -> str`
*   `return_to_launch(drone_id: int) -> str`
*   `hold_position(drone_id: int) -> str`
*   `get_telemetry(drone_id: int) -> Dict`
    *   *Returns:* `{lat, lon, altitude, battery_remaining_percent, heading}`

### B. Perception & Sensor Tools
*   `scan_surroundings(drone_id: int) -> str`
    *   *Returns:* Text description of simulated objects (e.g., "Obstacle detected 5m North").
*   `check_energy_feasibility(drone_id: int, target_lat: float, target_lon: float) -> Dict`
    *   *Returns:* `{estimated_cost_percent: float, feasible: bool}` (Uses Semantic Memory heuristics).

### C. Memory Tools (RAG Interface)
*   `log_experience(text: str, metadata: Dict) -> bool`
    *   *Usage:* Workers call this to save episodes.
*   `query_memory(query_text: str, memory_type: str, n_results: int) -> List[str]`
    *   *Usage:* Supervisor calls this to recall past hazards or energy rules.

---

## 3. Data Schemas (Task 2.3)
Defining these schemas now is vital for the **Phase 6 Defenses**. The `integrity_hash` and `supporting_evidence` fields are the technical enablers for your security research.

### A. Episodic Memory Schema (The "Log")
*Stores the raw stream of experience. Used for retrieval-augmented planning.*

| Field Name | Type | Description |
| :--- | :--- | :--- |
| `episode_id` | UUID | Unique identifier. |
| `timestamp` | Float | Simulation time ($t$). |
| `drone_id` | Int | The agent that experienced the event. |
| `state_vector` | JSON | `{lat, lon, battery, altitude}` at start of action. |
| `action_cmd` | String | The tool call executed (e.g., `goto_position(...)`). |
| `outcome` | String | Result (e.g., "Success", "Low Battery Abort", "Collision"). |
| `embedding` | Vector | Dense vector representation of the episode text. |
| **`integrity_hash`** | String | **(Critical for RQ2)** HMAC-SHA256 signature of the state+action+outcome. |

### B. Semantic Memory Schema (The "Rules")
*Stores generalized knowledge derived from episodes.*

| Field Name | Type | Description |
| :--- | :--- | :--- |
| `rule_id` | UUID | Unique identifier. |
| `rule_type` | Enum | `HAZARD_ZONE`, `NO_FLY`, `ENERGY_COST_HIGH`. |
| `rule_text` | String | Natural language rule (e.g., "Area X causes high battery drain due to wind"). |
| `polygon` | List[Coords] | Geofence coordinates for the rule. |
| **`supporting_evidence`**| List[UUID]| **(Critical for RQ2)** List of `episode_id`s that justify this rule's existence. |
| `confidence_score` | Float | 0.0 to 1.0. |

---

## 4. Energy Model Specification (Task 2.4)
To address the "Energy Constraints" in your title, we need a consistent metric.

**The Hybrid Approach:**
1.  **Operational Logic (SITL):** Agents use the standard PX4 battery reading (0-100%) to decide when to return home.
2.  **Scientific Evaluation (Paper Metric):** Because SITL battery models can be inconsistent, we will calculate a derived **Energy Cost ($E$)** for the results section:

$$ E_{total} = \sum_{t=0}^{T} (P_{hover} + P_{move}(v_t)) \cdot \Delta t $$

*   **Implementation Requirement:** The system must log `velocity` and `flight_mode` at 1Hz to a CSV file to calculate this curve during Phase 9 (Analysis).

---

## 5. Architecture Diagram (Task 2.5)

*This Mermaid code generates the architecture figure for your paper. It explicitly visualizes the "Attack Surface" (the Query Interface).*

```mermaid
graph TD
    %% Definitions
    classDef agent fill:#e1f5fe,stroke:#01579b,stroke-width:2px;
    classDef memory fill:#fff9c4,stroke:#fbc02d,stroke-width:2px;
    classDef sim fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px;
    classDef attack fill:#ffcdd2,stroke:#c62828,stroke-width:2px,stroke-dasharray: 5 5;

    subgraph User_Input
        Commander[Human Commander] -->|Mission Goal| Supervisor
    end

    subgraph Multi_Agent_Controller
        Supervisor(Supervisor Agent):::agent -->|Task Assignment| Worker1(Worker Drone 1):::agent
        Supervisor:::agent -->|Task Assignment| Worker2(Worker Drone 2):::agent
        
        %% Memory Access via Guard
        Supervisor <-->|Query Rules| MemGuard[Memory Manager / Guard]:::memory
        Worker1 -->|Log Episode| MemGuard
        Worker2 -->|Log Episode| MemGuard
    end

    subgraph Memory_Store
        MemGuard <-->|SQL + Vector| EpisodicDB[(Episodic Store)]:::memory
        MemGuard <-->|SQL + Vector| SemanticDB[(Semantic Store)]:::memory
    end

    subgraph Simulation_Physical
        Worker1 -->|MAVSDK| PX4_1[PX4 SITL Drone 1]:::sim
        Worker2 -->|MAVSDK| PX4_2[PX4 SITL Drone 2]:::sim
        
        PX4_1 -.->|Telemetry| EnergyLog[Energy Model Logger]:::sim
        PX4_2 -.->|Telemetry| EnergyLog
    end

    subgraph Threat_Model
        Attacker(Query-Only Attacker):::attack -.->|1. Poisoned Context| Commander
        Attacker -.->|2. Hallucinated Rules| MemGuard
    end

    %% Annotations
    linkStyle 6,7,8,9 stroke-width:4px,fill:none,stroke:#fbc02d;
```

### Steps to complete Phase 2:
1.  **Save the text above** as a PDF named `Phase2_Architecture_Spec.pdf`.
2.  **Generate the Diagram:** Copy the Mermaid code block into [Mermaid Live Editor](https://mermaid.live/), download the PNG, and insert it into your LaTeX paper draft.
3.  **Approval:** Send the 1-page design doc and the image to your supervisor with the note: *"Architecture and Schema definitions frozen. Ready to begin Phase 3 (Baseline Implementation)."*
