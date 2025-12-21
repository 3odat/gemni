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