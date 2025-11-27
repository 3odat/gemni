# Phase 3 Technical Report: Baseline Multi-Agent Implementation
**Project:** Memory Attacks and Defenses in Multi-Agent LLM-Controlled UAV Systems
**Date:** November 2025
**Status:** Implementation Ready

## 1. Project Structure
We will adopt a modular "Micro-Framework" structure. This ensures your code is clean enough for a PhD repo.

**Create a folder named `uav_project` and set up this tree:**

```text
uav_project/
├── .env                    # API Keys and Configs
├── requirements.txt        # Python dependencies
├── main.py                 # Entry point (The Orchestrator)
├── config.py               # Central configuration
├── core/
│   ├── __init__.py
│   ├── llm_engine.py       # OpenAI Client Wrapper
│   └── logger.py           # Rich logging setup
├── interfaces/
│   ├── __init__.py
│   ├── drone_interface.py  # MAVSDK Wrapper (Async)
│   └── api_interface.py    # Perception/Sensor REST API Client
├── agents/
│   ├── __init__.py
│   ├── base_agent.py       # Abstract Agent Class
│   ├── supervisor.py       # Supervisor Logic
│   └── worker.py           # Worker Logic
└── schemas/
    ├── __init__.py
    └── models.py           # Pydantic Data Models
```

---

## 2. Environment & Dependencies

**Step 2.1: `requirements.txt`**
These are the industry-standard libraries for modern AI systems.
```text
mavsdk==1.4.9
openai>=1.50.0
pydantic>=2.9.0
httpx>=0.27.0
rich>=13.8.0
python-dotenv>=1.0.1
tenacity>=8.5.0
```

**Step 2.2: `.env`**
Create this file to keep secrets out of your code.
```ini
OPENAI_API_KEY=sk-proj-your-key-here
SIMULATION_IP=127.0.0.1
DRONE1_PORT=50051
DRONE2_PORT=50052
API_PORT=8090
```

---

## 3. Core Implementation (The "Engine")

We need strictly typed data structures to prevent the LLM from hallucinating invalid commands.

**Step 3.1: `schemas/models.py`**
```python
from pydantic import BaseModel, Field
from typing import List, Literal, Optional

# --- Agent Communication Schemas ---

class Task(BaseModel):
    """A single unit of work assigned by the Supervisor."""
    task_id: str = Field(..., description="Unique ID for the task")
    drone_id: int = Field(..., description="Target drone (1 or 2)")
    action_type: Literal["move", "scan", "return"]
    params: dict = Field(..., description="Parameters like {lat, lon, alt}")

class MissionPlan(BaseModel):
    """The output format for the Supervisor Agent."""
    reasoning: str = Field(..., description="Explanation of the strategy")
    tasks: List[Task] = Field(..., description="List of tasks to execute concurrently")

class ToolResult(BaseModel):
    """Standardized return format for all tools."""
    success: bool
    message: str
    data: Optional[dict] = None
```

**Step 3.2: `config.py`**
Handles your specific port mapping.
```python
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    OPENAI_KEY = os.getenv("OPENAI_API_KEY")
    API_BASE = f"http://{os.getenv('SIMULATION_IP', '127.0.0.1')}:{os.getenv('API_PORT', '8090')}"
    
    # Your specific MAVSDK Server Ports
    DRONE_CONFIG = {
        1: {"port": int(os.getenv("DRONE1_PORT", 50051))},
        2: {"port": int(os.getenv("DRONE2_PORT", 50052))}
    }

    # Model to use
    MODEL_NAME = "gpt-4o-2024-08-06" # Supports Structured Outputs nicely
```

---

## 4. Interfaces (Connecting to PX4)

This is the bridge between the digital LLM and the physical simulator.

**Step 4.1: `interfaces/drone_interface.py`**
We handle the MAVSDK connection asynchronously.

```python
import asyncio
from mavsdk import System
from config import Config
from core.logger import log

class DroneInterface:
    def __init__(self, drone_id: int):
        self.drone_id = drone_id
        self.port = Config.DRONE_CONFIG[drone_id]["port"]
        self.drone = System(mavsdk_server_address='localhost', port=self.port)

    async def connect(self):
        """Establishes connection to the specific gRPC port."""
        log.info(f"[Drone {self.drone_id}] Connecting on port {self.port}...")
        await self.drone.connect()

        # Wait for the drone to be ready
        async for state in self.drone.core.connection_state():
            if state.is_connected:
                log.success(f"[Drone {self.drone_id}] Connected!")
                break

    async def arm_and_takeoff(self, altitude: float = 5.0):
        log.info(f"[Drone {self.drone_id}] Arming...")
        await self.drone.action.arm()
        log.info(f"[Drone {self.drone_id}] Taking off...")
        await self.drone.action.set_takeoff_altitude(altitude)
        await self.drone.action.takeoff()
        return f"Drone {self.drone_id} airborne at {altitude}m"

    async def goto_location(self, lat: float, lon: float, alt: float):
        log.info(f"[Drone {self.drone_id}] Flying to {lat}, {lon}")
        await self.drone.action.goto_location(lat, lon, alt, 0)
        return "Move command sent"

    async def land(self):
        await self.drone.action.land()
        return "Landing initiated"
```

**Step 4.2: `interfaces/api_interface.py`**
Wraps your custom HTTP sensor server.

```python
import httpx
from config import Config

class APIInterface:
    @staticmethod
    async def get_perception(drone_id: int) -> str:
        """Fetches scene description from your /perception/scene endpoint."""
        # Maps drone ID to the query param expected by your server
        d_str = f"drone{drone_id}" 
        url = f"{Config.API_BASE}/perception/scene"
        
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(url, params={"drone": d_str}, timeout=2.0)
                return resp.text
            except Exception as e:
                return f"Perception Error: {str(e)}"

    @staticmethod
    async def get_sensors(drone_id: int) -> dict:
        """Fetches sensor data from /sensors/{id}."""
        url = f"{Config.API_BASE}/sensors/{drone_id}"
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(url, timeout=2.0)
                return resp.json()
            except Exception as e:
                return {"error": str(e)}
```

---

## 5. Agent Logic (The "Brain")

We use OpenAI's new **Structured Outputs** (`parse`) method. This guarantees the agent returns valid JSON matching our Pydantic models.

**Step 5.1: `agents/supervisor.py`**
The Orchestrator.

```python
from openai import AsyncOpenAI
from config import Config
from schemas.models import MissionPlan
from core.logger import log

class SupervisorAgent:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=Config.OPENAI_KEY)
        self.system_prompt = """
        You are the Mission Supervisor for a 2-UAV swarm. 
        Your goal is to decompose high-level user commands into atomic tasks.
        
        Available Drones:
        - Drone 1 (Worker)
        - Drone 2 (Worker)
        
        Output a STRICT JSON plan.
        """

    async def plan_mission(self, user_command: str) -> MissionPlan:
        log.section("Supervisor Planning")
        
        completion = await self.client.beta.chat.completions.parse(
            model=Config.MODEL_NAME,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_command}
            ],
            response_format=MissionPlan,
        )
        
        plan = completion.choices[0].message.parsed
        log.print_json(plan.model_dump())
        return plan
```

**Step 5.2: `agents/worker.py`**
The Executor.

```python
from interfaces.drone_interface import DroneInterface
from interfaces.api_interface import APIInterface
from schemas.models import Task, ToolResult
from core.logger import log

class WorkerAgent:
    def __init__(self, drone_id: int):
        self.drone_id = drone_id
        self.drone_hw = DroneInterface(drone_id)

    async def initialize(self):
        """Connects to the physical/simulated hardware."""
        await self.drone_hw.connect()

    async def execute_task(self, task: Task) -> ToolResult:
        log.info(f"[Worker {self.drone_id}] Received Task: {task.action_type}")
        
        try:
            result_msg = ""
            
            # --- Tool Routing Logic ---
            if task.action_type == "move":
                lat = task.params.get("lat")
                lon = task.params.get("lon")
                alt = task.params.get("alt", 10.0)
                # First, ensure we are flying
                await self.drone_hw.arm_and_takeoff(alt)
                # Then go to target
                result_msg = await self.drone_hw.goto_location(lat, lon, alt)

            elif task.action_type == "scan":
                # Call the REST API for perception
                scene_desc = await APIInterface.get_perception(self.drone_id)
                result_msg = f"Scan complete. Visible: {scene_desc}"

            elif task.action_type == "return":
                result_msg = await self.drone_hw.land()

            log.success(f"[Worker {self.drone_id}] Finished: {result_msg}")
            
            # FUTURE: Phase 3.3 - Log to Episodic Memory here
            
            return ToolResult(success=True, message=result_msg)

        except Exception as e:
            log.error(f"[Worker {self.drone_id}] Failed: {str(e)}")
            return ToolResult(success=False, message=str(e))
```

---

## 6. The Main Loop (Putting it all together)

**Step 6.1: `core/logger.py`** (Bonus "Fancy" Utility)
```python
from rich.console import Console
from rich.panel import Panel
import json

console = Console()

class log:
    @staticmethod
    def info(msg): console.print(f"[blue]INFO:[/blue] {msg}")
    @staticmethod
    def success(msg): console.print(f"[green]SUCCESS:[/green] {msg}")
    @staticmethod
    def error(msg): console.print(f"[red]ERROR:[/red] {msg}")
    
    @staticmethod
    def section(title):
        console.print(Panel(f"[bold yellow]{title}[/bold yellow]", expand=False))

    @staticmethod
    def print_json(data):
        console.print_json(json.dumps(data))
```

**Step 6.2: `main.py`**
The executable entry point.

```python
import asyncio
from agents.supervisor import SupervisorAgent
from agents.worker import WorkerAgent
from core.logger import log

async def main():
    log.section("Phase 3: System Initialization")

    # 1. Initialize Agents
    supervisor = SupervisorAgent()
    drone1 = WorkerAgent(drone_id=1)
    drone2 = WorkerAgent(drone_id=2)

    # 2. Connect to Hardware (Parallel Init)
    log.info("Connecting to PX4 Instances...")
    await asyncio.gather(
        drone1.initialize(),
        drone2.initialize()
    )
    
    # 3. Define Mission (Hardcoded for Phase 3 Test)
    user_mission = "Takeoff and scan the area at altitude 15m. Drone 1 goes to Sector A (Lat 47.398, Lon 8.545). Drone 2 goes to Sector B (Lat 47.399, Lon 8.546)."

    # 4. Supervisor Plans
    plan = await supervisor.plan_mission(user_mission)

    # 5. Execution Loop
    tasks_to_run = []
    
    for task in plan.tasks:
        if task.drone_id == 1:
            tasks_to_run.append(drone1.execute_task(task))
        elif task.drone_id == 2:
            tasks_to_run.append(drone2.execute_task(task))
    
    log.section("Executing Mission Plan")
    results = await asyncio.gather(*tasks_to_run)

    log.section("Mission Report")
    for res in results:
        log.info(f"Result: {res.message}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.error("Mission Aborted by User")
```

---

### How to Run Phase 3

1.  **Start your Environment:**
    *   Launch your Gazebo/SITL instances.
    *   Ensure your custom API server (`:8090`) is running.
    *   Check ports `50051` and `50052` are active.

2.  **Install Requirements:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Run the System:**
    ```bash
    python main.py
    ```

### Why this is a "PhD-Quality" Implementation:
*   **Separation of Concerns:** Hardware (MAVSDK), Logic (Agents), and Orchestration (Main) are decoupled.
*   **Type Safety:** Using `schemas/models.py` means the LLM cannot crash your drone with bad string parsing.
*   **AsyncIO:** We use `asyncio.gather` so both drones takeoff **simultaneously**, not sequentially. This is true multi-agent behavior.
*   **Extensibility:** In Phase 4, you just add `memory_interface.py` to the `interfaces` folder and call it inside `worker.py`. No rewrite needed.
