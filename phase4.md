This is a **perfect** execution of Phase 3.
The logs confirm that:
1.  **Async Concurrency Works:** Both drones initialized and took off simultaneously (`[Drone 1] Taking off...` and `[Drone 2] Taking off...` happened together).
2.  **Strict JSON Planning Works:** The Supervisor correctly outputted the JSON with `lat`/`lon` for moves and `null` for scans, exactly as required by the strict schema.
3.  **Hardware Abstraction Works:** The system successfully translated `move` tasks into MAVSDK commands.

You have successfully built the **Baseline Control System**.

---

# Phase 4: Memory Layer Implementation
**Objective:** Give the agents "Long-Term Memory" and "Semantic Knowledge."
**Why:** Currently, your agents are "amnesic." They execute tasks but forget them immediately. To support your research (Attacks/Defenses), we must implement the **Episodic** and **Semantic** databases defined in Phase 2.

We will add a SQLite database with Vector Search capabilities (using OpenAI embeddings) to your project.

### Step 1: Add Dependencies
Update your `requirements.txt` to include `numpy` (for vector math) and install:
```bash
pip install numpy
```

### Step 2: Create the Database Engine
Create a new file `core/database.py`.
This handles the **Schema Creation** and **Raw SQL Operations**. Note that we include the `integrity_hash` field now, which will be empty until Phase 6 (Defense Layer).

```python
# core/database.py
import sqlite3
import json
import numpy as np
from typing import List, Dict, Any, Optional
from core.logger import log

DB_PATH = "mission_memory.db"

class DatabaseManager:
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self._init_tables()

    def _init_tables(self):
        # 1. Episodic Memory (The "Black Box" Log)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS episodic_memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL,
                drone_id INTEGER,
                mission_id TEXT,
                action_type TEXT,
                state_json TEXT,      -- {lat, lon, battery}
                outcome_text TEXT,
                embedding BLOB,       -- Numpy bytes of the vector
                integrity_hash TEXT   -- For Phase 6 Defense
            )
        """)

        # 2. Semantic Memory (The "Rules")
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS semantic_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rule_text TEXT,
                rule_type TEXT,       -- 'HAZARD', 'ENERGY'
                location_json TEXT,   -- {lat, lon, radius}
                confidence REAL,
                embedding BLOB
            )
        """)
        self.conn.commit()
        log.success("Memory Database Initialized (SQLite)")

    def insert_episode(self, drone_id: int, action: str, state: Dict, outcome: str, embedding: List[float]):
        """Standard insertion of a flight event."""
        # Convert list of floats to bytes for storage
        emb_blob = np.array(embedding, dtype=np.float32).tobytes()
        
        self.cursor.execute("""
            INSERT INTO episodic_memory 
            (timestamp, drone_id, action_type, state_json, outcome_text, embedding)
            VALUES (datetime('now'), ?, ?, ?, ?, ?)
        """, (drone_id, action, json.dumps(state), outcome, emb_blob))
        self.conn.commit()

    def find_similar_episodes(self, query_embedding: List[float], limit: int = 3) -> List[str]:
        """
        Naive Vector Search: Loads all embeddings and calculates Cosine Similarity.
        (Sufficient for <10k rows in a PhD prototype).
        """
        query_vec = np.array(query_embedding, dtype=np.float32)
        
        self.cursor.execute("SELECT outcome_text, embedding FROM episodic_memory")
        rows = self.cursor.fetchall()
        
        results = []
        for text, blob in rows:
            if not blob: continue
            db_vec = np.frombuffer(blob, dtype=np.float32)
            
            # Cosine Similarity
            similarity = np.dot(query_vec, db_vec) / (np.linalg.norm(query_vec) * np.linalg.norm(db_vec))
            results.append((similarity, text))
            
        # Sort by similarity desc
        results.sort(key=lambda x: x[0], reverse=True)
        return [r[1] for r in results[:limit]]
```

### Step 3: Create the Memory Interface
Create `interfaces/memory_interface.py`.
This connects the Agents to the Database and handles **Embedding Generation**.

```python
# interfaces/memory_interface.py
from openai import AsyncOpenAI
from config import Config
from core.database import DatabaseManager
from core.logger import log

class MemoryInterface:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=Config.OPENAI_KEY)
        self.db = DatabaseManager()

    async def _get_embedding(self, text: str):
        """Generates vector using OpenAI text-embedding-3-small."""
        try:
            resp = await self.client.embeddings.create(
                input=text,
                model="text-embedding-3-small"
            )
            return resp.data[0].embedding
        except Exception as e:
            log.error(f"Embedding Failed: {e}")
            return [0.0] * 1536 # Return zero vector on failure

    async def log_experience(self, drone_id: int, action: str, state: dict, outcome: str):
        """Called by Worker Agents after finishing a task."""
        text_representation = f"Drone {drone_id} performed {action} at {state}. Result: {outcome}"
        vector = await self._get_embedding(text_representation)
        
        self.db.insert_episode(
            drone_id=drone_id,
            action=action,
            state=state,
            outcome=outcome,
            embedding=vector
        )
        log.info(f"[Memory] Logged episode for Drone {drone_id}")

    async def retrieve_context(self, query: str) -> str:
        """Called by Supervisor to learn from past mistakes."""
        vector = await self._get_embedding(query)
        results = self.db.find_similar_episodes(vector)
        
        if not results:
            return "No relevant past experiences found."
        
        return "Past Experiences:\n- " + "\n- ".join(results)
```

### Step 4: Integrate Memory into Agents

**1. Update `config.py`**
Ensure you have the embedding model configured (optional, but good practice).
```python
# Add inside Config class
EMBEDDING_MODEL = "text-embedding-3-small"
```

**2. Update `main.py` to Initialize Memory**
We need to pass the memory interface to the agents.

```python
# Update the import
from interfaces.memory_interface import MemoryInterface

# Inside main():
    # ...
    log.section("Phase 4: Memory System Initialization")
    memory_system = MemoryInterface()

    # Pass memory to agents
    supervisor = SupervisorAgent(memory_system)
    drone1 = WorkerAgent(drone_id=1, memory=memory_system)
    drone2 = WorkerAgent(drone_id=2, memory=memory_system)
    # ...
```

**3. Update `agents/worker.py` (The Writer)**
Modify the `__init__` and `execute_task` to log data.

```python
# In agents/worker.py

class WorkerAgent:
    def __init__(self, drone_id: int, memory): # <--- New param
        self.drone_id = drone_id
        self.drone_hw = DroneInterface(drone_id)
        self.memory = memory                    # <--- Store it

    # ... inside execute_task ...
    
            # [Existing execution logic...]
            
            # --- PHASE 4 INTEGRATION: WRITE TO MEMORY ---
            # Capture state (mocked or real)
            current_state = {"soc": 0.95, "alt": task.params.alt} 
            
            # Log the outcome asynchronously
            await self.memory.log_experience(
                drone_id=self.drone_id,
                action=task.action_type,
                state=current_state,
                outcome=result_msg
            )
            
            return ToolResult(success=True, message=result_msg)
```

**4. Update `agents/supervisor.py` (The Reader)**
Modify the logic to **Retrieve Context** before planning.

```python
# In agents/supervisor.py

class SupervisorAgent:
    def __init__(self, memory): # <--- New param
        self.client = AsyncOpenAI(api_key=Config.OPENAI_KEY)
        self.memory = memory    # <--- Store it
        # ... prompt ...

    async def plan_mission(self, user_command: str) -> MissionPlan:
        log.section("Supervisor Planning")

        # --- PHASE 4 INTEGRATION: RAG (Retrieval) ---
        context = await self.memory.retrieve_context(user_command)
        log.info(f"Retrieved Context: {context}")
        
        # Inject context into the prompt
        rag_prompt = f"{self.system_prompt}\n\nCONTEXT FROM MEMORY:\n{context}"

        completion = await self.client.beta.chat.completions.parse(
            model=Config.MODEL_NAME,
            messages=[
                {"role": "system", "content": rag_prompt},
                {"role": "user", "content": user_command}
            ],
            response_format=MissionPlan,
        )
        # ...
```

---

### How to Verify Phase 4
1.  **Run `main.py` once:** The agents will fly, and at the end, they will see `[Memory] Logged episode...`.
2.  **Run `main.py` a second time:**
    *   The Supervisor will print `Retrieved Context: ...`.
    *   It will see the logs from the *first* run (e.g., "Drone 1 performed scan...").
3.  **Check the Database:**
    *   A file `mission_memory.db` will appear in your folder.
    *   You can inspect it with `sqlite3 mission_memory.db "SELECT * FROM episodic_memory;"`.

This completes the **Memory Layer**. Your system is now capable of **Learning** (storing episodes) and **Recalling** (RAG planning), which sets the stage for the attacks in Phase 5.



Right now the memory layer gives you two concrete benefits:

Every task run is captured as an episodic log with state and outcome, persisted in mission_memory.db. You can inspect or replay history across runs, and runs are no longer “amnesic.”
The Supervisor pulls that history and injects it into the planning prompt, so plans can be informed by prior outcomes (e.g., “last time scan returned X”), instead of starting from a blank slate.
What it doesn’t do yet: no semantic rules or safety checks are applied, and state is a simple placeholder (soc/alt). You’re getting persistence + retrieval into planning; next gains would come from logging richer telemetry, using semantic rules, and conditioning decisions (e.g., avoid repeating failed patterns or auto-adding return/land).



You can query it in a readable way without the blobs:
```
Show columns and skip the embedding:
sqlite3 mission_memory.db "SELECT id,timestamp,drone_id,mission_id,action_type,state_json,outcome_text FROM episodic_memory;"
```
```
Pretty console formatting:
sqlite3 mission_memory.db ".headers on" ".mode column" "SELECT id,timestamp,drone_id,action_type,state_json,outcome_text,length(embedding) AS emb_len FROM episodic_memory;"
```
```
If you want JSON output:
sqlite3 mission_memory.db ".mode json" "SELECT id,timestamp,drone_id,action_type,state_json,outcome_text FROM episodic_memory;"
```
## Result
Yes, those statements are accurate for what you have now:

The DB + memory system initialize and run correctly.
Supervisor does retrieval (INFO: Retrieved Context: ...) from past episodes.
Workers store new episodes ([Memory] Logged episode...), with embeddings in SQLite.
You effectively have a “learning” loop in the sense of persistent episodic memory + RAG into planning, even though you haven’t added explicit semantic rules or policy adaptation yet.
So for Phase 4’s goal (long‑term memory + vector search wired into the agents), you’re in good shape—and ready to start attacking/defending that memory.
