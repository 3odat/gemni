import asyncio
from mavsdk import System
from config import Config
from core.logger import log

class DroneInterface:
    def __init__(self, drone_id: int):
        self.drone_id = drone_id
        self.port = Config.DRONE_CONFIG[drone_id]["port"]
        self.drone = System(mavsdk_server_address='localhost', port=self.port)

    async def _wait_for_global_position(self, timeout: float = 30.0):
        """
        Wait until the autopilot reports usable global position.
        This must be true before arming.
        """
        log.info(f"[Drone {self.drone_id}] Waiting for GPS lock...")
        start = asyncio.get_running_loop().time()
        async for health in self.drone.telemetry.health():
            if health.is_global_position_ok:
                log.success(f"[Drone {self.drone_id}] GPS lock acquired")
                return
            if asyncio.get_running_loop().time() - start > timeout:
                raise TimeoutError(f"Drone {self.drone_id} GPS lock timeout")

    async def _wait_for_home_position(self, timeout: float = 10.0):
        """
        Wait for home position after arming (PX4 sets home when armed).
        """
        log.info(f"[Drone {self.drone_id}] Waiting for home position...")
        start = asyncio.get_running_loop().time()
        async for health in self.drone.telemetry.health():
            if health.is_home_position_ok:
                log.success(f"[Drone {self.drone_id}] Home position set")
                return
            if asyncio.get_running_loop().time() - start > timeout:
                raise TimeoutError(f"Drone {self.drone_id} home position timeout")

    async def _wait_for_altitude(self, target_altitude: float, timeout: float = 60.0):
        """
        Confirm climb by watching relative altitude.
        We now require within 0.5m of target (or min 1m) before proceeding to movement.
        """
        start = asyncio.get_running_loop().time()
        threshold = max(1.0, target_altitude - 0.5)
        log.info(f"[Drone {self.drone_id}] Waiting to reach ≥{threshold:.1f}m (target {target_altitude}m)")
        async for position in self.drone.telemetry.position():
            rel_alt = position.relative_altitude_m

            if rel_alt >= threshold:
                log.success(f"[Drone {self.drone_id}] Altitude reached: {rel_alt:.1f}m")
                return
            if asyncio.get_running_loop().time() - start > timeout:
                raise TimeoutError(f"Drone {self.drone_id} takeoff confirmation timeout (last alt {rel_alt:.1f}m)")


    async def connect(self):
        """Establishes connection to the specific gRPC port."""
        log.info(f"[Drone {self.drone_id}] Connecting on port {self.port}...")
        await self.drone.connect()

        # Wait for the drone to be ready
        async for state in self.drone.core.connection_state():
            if state.is_connected:
                log.success(f"[Drone {self.drone_id}] Connected!")
                # Small settle and early health check
                await asyncio.sleep(0.5)
                try:
                    await self._wait_for_global_position(timeout=30.0)
                except Exception:
                    pass
                break

    async def arm_and_takeoff(self, altitude: float = 5.0):
        attempts = 2
        last_exc = None
        for attempt in range(1, attempts + 1):
            try:
                await self._wait_for_global_position()
                log.info(f"[Drone {self.drone_id}] Arming...")
                await self.drone.action.arm()
                await self._wait_for_home_position()
                log.info(f"[Drone {self.drone_id}] Taking off to {altitude}m...")
                await self.drone.action.set_takeoff_altitude(altitude)
                await self.drone.action.takeoff()
                await self._wait_for_altitude(altitude)
                return f"Drone {self.drone_id} airborne at {altitude}m"
            except Exception as e:
                last_exc = e
                log.error(f"[Drone {self.drone_id}] Takeoff attempt {attempt} failed: {e}")
                if attempt < attempts:
                    log.info(f"[Drone {self.drone_id}] Retrying takeoff...")
                    await asyncio.sleep(1.0)
        # If here, all attempts failed
        raise last_exc if last_exc else RuntimeError("Unknown takeoff failure")

    async def goto_location(self, lat: float, lon: float, alt: float):
        log.info(f"[Drone {self.drone_id}] Flying to {lat}, {lon}")
        await self.drone.action.goto_location(lat, lon, alt, 0)
        return "Move command sent"

    async def land(self):
        await self.drone.action.land()
        return "Landing initiated"
