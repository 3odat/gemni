import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    OPENAI_KEY = os.getenv("OPENAI_API_KEY")
    API_BASE = f"http://{os.getenv('SIMULATION_IP', '127.0.0.1')}:{os.getenv('API_PORT', '8090')}"
    # Optional: base URL for OpenAI-compatible servers (e.g., Ollama)
    LLM_API_BASE = os.getenv("LLM_API_BASE", "http://localhost:11434/v1")
    
    # Your specific MAVSDK Server Ports
    DRONE_CONFIG = {
        1: {"port": int(os.getenv("DRONE1_PORT", 50051))},
        2: {"port": int(os.getenv("DRONE2_PORT", 50052))}
    }

    # Models to use (can be overridden via env)
    MODEL_NAME = os.getenv("LLM_MODEL_NAME", "gpt-oss:20b")
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")
