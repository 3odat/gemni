from interfaces.drone_interface import DroneInterface
from interfaces.api_interface import APIInterface
from schemas.models import Task, ToolResult
from core.logger import log


class WorkerAgent:
    def __init__(self, drone_id: int, memory):
        self.drone_id = drone_id
        self.drone_hw = DroneInterface(drone_id)
        self.memory = memory
        self.airborne = False
        # Simple simulated state-of-charge (1.0 = 100%)
        self.soc = 1.0

    async def initialize(self):
        """Connects to the physical/simulated hardware."""
        await self.drone_hw.connect()

    async def execute_task(self, task: Task) -> ToolResult:
        log.info(f"[Worker {self.drone_id}] Received Task: {task.action_type}")
        
        try:
            if self.soc <= 0.1 and task.action_type != "return":
                raise RuntimeError("Low SOC – refusing non-return task")

            result_msg = ""
            
            # --- Tool Routing Logic ---
            if task.action_type == "move":
                # FIX: Access attributes directly from the Pydantic model
                lat = task.params.lat
                lon = task.params.lon
                alt = task.params.alt
                
                if lat is None or lon is None:
                    raise ValueError("Move command missing Lat/Lon")

                # First, ensure we are flying
                await self.drone_hw.arm_and_takeoff(alt)
                self.airborne = True
                # Then go to target
                result_msg = await self.drone_hw.goto_location(lat, lon, alt)

            elif task.action_type == "scan":
                # Ensure we are airborne before scanning; if already airborne, skip redundant takeoff
                if not self.airborne:
                    alt = task.params.alt
                    await self.drone_hw.arm_and_takeoff(alt)
                    self.airborne = True

                # Perception disabled per requirement; just acknowledge scan
                result_msg = "Scan completed."

            elif task.action_type == "return":
                result_msg = await self.drone_hw.land()
                self.airborne = False
            # --- PHASE 4/5 INTEGRATION: UPDATE ENERGY + WRITE TO MEMORY ---
            self._update_energy(task)
            current_state = {"soc": round(self.soc, 3), "alt": task.params.alt}
            await self.memory.log_experience(
                drone_id=self.drone_id,
                action=task.action_type,
                state=current_state,
                outcome=result_msg
            )

            log.success(f"[Worker {self.drone_id}] Finished: {result_msg}")
            return ToolResult(success=True, message=result_msg)

        except Exception as e:
            log.error(f"[Worker {self.drone_id}] Failed: {str(e)}")
            # Attempt to log failure as well (SOC unchanged here)
            try:
                await self.memory.log_experience(
                    drone_id=self.drone_id,
                    action=task.action_type,
                    state={"soc": round(self.soc, 3), "alt": task.params.alt},
                    outcome=str(e)
                )
            except Exception:
                pass
            return ToolResult(success=False, message=str(e))

    def _update_energy(self, task: Task) -> None:
        """Very simple energy model: SOC decreases per action."""
        consumption = {
            "move": 0.08,   # ~8% per move
            "scan": 0.02,   # ~2% per scan
            "return": 0.05  # ~5% per return/land
        }
        delta = consumption.get(task.action_type, 0.01)
        self.soc = max(0.0, self.soc - delta)
