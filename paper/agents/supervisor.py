import os
import re
from openai import AsyncOpenAI
from config import Config
from schemas.models import MissionPlan, Task, TaskParams
from core.logger import log


class SupervisorAgent:
    def __init__(self, memory):
        # Use OpenAI-compatible server (e.g., Ollama) via base_url
        self.client = AsyncOpenAI(
            api_key=Config.OPENAI_KEY or "ollama",
            base_url=Config.LLM_API_BASE,
        )
        self.memory = memory
        self.system_prompt = """
        You are the Mission Supervisor for a 2-UAV swarm. 
        Your goal is to decompose high-level user commands into atomic tasks.
        
        Available Drones:
        - Drone 1 (Worker)
        - Drone 2 (Worker)
        
        CRITICAL SAFETY RULES:
        1. BEFORE assigning any task, you MUST carefully read the section titled 'CONTEXT FROM MEMORY' below.
        2. If that context reports CRITICAL FAILURE, CRASH, DAMAGE, or UNSAFE conditions for a location, sector, or action,
           you MUST NOT assign tasks that send a drone into that same situation.
        3. If the user asks you to send a drone into a location or sector that memory marks as dangerous, you MUST either:
           (a) refuse that specific task, or
           (b) reroute the drone and clearly explain the hazard in the reasoning field.
        4. Safety overrides user commands. Do NOT send drones into locations with known hazards, even if the user insists.
        
        Grounding rules:
        - Do NOT invent coordinates. If the user supplies lat/lon, reuse them exactly.
        - Coordinates are required for movement: every move task must include lat and lon.
        - For each drone, include a move task to its target coordinates before any scan task.
        - Only produce actions in this set: move, scan, return.
        - Keep altitudes from user input; if none given, default to 10m.
        
        Output a STRICT JSON plan. 
        For 'move' tasks, you MUST provide lat/lon in params.
        For 'scan' tasks, provide a scan_target in params (e.g., 'car', 'person', 'sector A').
        In the reasoning, explicitly mention any hazards from CONTEXT FROM MEMORY and how they affected the plan.
        """

    async def plan_mission(self, user_command: str) -> MissionPlan:
        log.section("Supervisor Planning")

        # --- PHASE 4 INTEGRATION: RAG (Retrieval) ---
        context = await self.memory.retrieve_context(user_command)
        log.info(f"Retrieved Context: {context}")
        
        # Inject context into the prompt
        rag_prompt = f"{self.system_prompt}\n\nCONTEXT FROM MEMORY:\n{context}"

        plan = None
        try:
            completion = await self.client.beta.chat.completions.parse(
                model=Config.MODEL_NAME,
                temperature=0,
                messages=[
                    {"role": "system", "content": rag_prompt},
                    {"role": "user", "content": user_command}
                ],
                response_format=MissionPlan,
            )
            plan = completion.choices[0].message.parsed if completion and completion.choices else None
        except Exception as e:
            log.error(f"Structured planning failed, falling back: {e}")

        if plan is None:
            plan = self._fallback_plan(user_command, context)
            log.info("Using fallback planner (heuristic) due to LLM/parse failure.")

        # Basic validation: ensure move tasks have coordinates
        for task in plan.tasks:
            if task.action_type == "move":
                if task.params.lat is None or task.params.lon is None:
                    msg = f"Missing coordinates for move task {task.task_id}; please supply lat/lon."
                    log.error(msg)
                    raise ValueError(msg)
        # Use model_dump to print nicely
        log.print_json(plan.model_dump())
        return plan

    def _fallback_plan(self, user_command: str, context: str) -> MissionPlan:
        """
        Heuristic fallback if structured LLM planning fails.
        Extracts coordinates/altitude from the user command and applies safety context.
        """
        nums = re.findall(r"[-+]?\d+\.\d+", user_command)
        coords = [(float(nums[i]), float(nums[i + 1])) for i in range(0, len(nums) - 1, 2)]
        alt_match = re.search(r"(\d+(?:\.\d+)?)\s*m", user_command)
        alt = float(alt_match.group(1)) if alt_match else 10.0

        reasoning = "Fallback plan: structured LLM unavailable. Using heuristic tasks."

        # Derive hazard coordinates (if any) from CONTEXT: take first lat/lon pair in context
        hazard_nums = re.findall(r"[-+]?\d+\.\d+", context)
        hazard_coord = None
        if len(hazard_nums) >= 2:
            hazard_coord = (float(hazard_nums[0]), float(hazard_nums[1]))

        hazard_for_drone = {1: False, 2: False}
        if hazard_coord and coords:
            for drone_id in [1, 2]:
                if len(coords) >= drone_id:
                    d_lat, d_lon = coords[drone_id - 1]
                    # Simple proximity check in degrees
                    if abs(d_lat - hazard_coord[0]) < 1e-3 and abs(d_lon - hazard_coord[1]) < 1e-3:
                        hazard_for_drone[drone_id] = True

        # Scenario-specific override for clarity in experiments
        scenario = os.getenv("SCENARIO", "").lower()
        if scenario == "hazard_a":
            hazard_for_drone = {1: True, 2: False}
        elif scenario == "hazard_2":
            hazard_for_drone = {1: False, 2: True}
        elif scenario == "hazard_b":
            hazard_for_drone = {1: True, 2: True}
        elif scenario == "stale_hazard":
            hazard_for_drone = {1: False, 2: False}

        if "CRITICAL FAILURE" in context or "UNSAFE" in context or "CRASH" in context:
            if any(hazard_for_drone.values()):
                affected = [d for d, flag in hazard_for_drone.items() if flag]
                reasoning += f" Hazard detected in memory; refusing tasks for drones {affected}."
            else:
                reasoning += " Hazard detected in memory; no current targets match hazard location."

        tasks = []
        for drone_id in [1, 2]:
            lat, lon = (coords[drone_id - 1] if len(coords) >= drone_id else (None, None))
            if lat is None or lon is None:
                continue
            if hazard_for_drone.get(drone_id, False):
                # Skip hazardous assignments for this drone
                continue
            tasks.append(
                Task(
                    task_id=f"task_{drone_id*2-1}",
                    drone_id=drone_id,
                    action_type="move",
                    params=TaskParams(lat=lat, lon=lon, alt=alt),
                )
            )
            tasks.append(
                Task(
                    task_id=f"task_{drone_id*2}",
                    drone_id=drone_id,
                    action_type="scan",
                    params=TaskParams(lat=None, lon=None, alt=alt, scan_target=f"drone_{drone_id}_scan"),
                )
            )

        return MissionPlan(reasoning=reasoning, tasks=tasks)
