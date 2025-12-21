from pydantic import BaseModel, Field, ConfigDict
from typing import List, Literal, Optional

# --- STRICT SCHEMA DEFINITIONS ---

class TaskParams(BaseModel):
    """
    Strict parameters model. 
    OpenAI requires all fields to be defined for 'Structured Outputs'.
    We use optional fields that default to None/0 so the LLM can populate what's needed.
    """
    model_config = ConfigDict(extra="forbid") # <--- FIX: This enables OpenAI Strict Mode

    lat: Optional[float] = Field(None, description="Target Latitude (for moves)")
    lon: Optional[float] = Field(None, description="Target Longitude (for moves)")
    alt: float = Field(10.0, description="Target Altitude")
    scan_target: Optional[str] = Field(None, description="Target name if scanning")

class Task(BaseModel):
    model_config = ConfigDict(extra="forbid") # <--- FIX

    task_id: str = Field(..., description="Unique ID for the task")
    drone_id: int = Field(..., description="Target drone (1 or 2)")
    action_type: Literal["move", "scan", "return"]
    params: TaskParams = Field(..., description="Execution parameters")

class MissionPlan(BaseModel):
    model_config = ConfigDict(extra="forbid") # <--- FIX

    reasoning: str = Field(..., description="Explanation of the strategy")
    tasks: List[Task] = Field(..., description="List of tasks to execute concurrently")

class ToolResult(BaseModel):
    """Standardized return format for all tools."""
    success: bool
    message: str
    data: Optional[dict] = None