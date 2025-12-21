from openai import AsyncOpenAI
from config import Config
from core.database import DatabaseManager
from core.logger import log


class MemoryInterface:
    def __init__(self):
        # Point to local/OpenAI-compatible LLM server (e.g., Ollama) via Config.LLM_API_BASE
        self.client = AsyncOpenAI(
            api_key=Config.OPENAI_KEY or "ollama",
            base_url=Config.LLM_API_BASE,
        )
        self.db = DatabaseManager()

    async def _get_embedding(self, text: str):
        """Generates vector using OpenAI text-embedding-3-small."""
        try:
            resp = await self.client.embeddings.create(
                input=text,
                model=Config.EMBEDDING_MODEL,
            )
            return resp.data[0].embedding
        except Exception as e:
            log.error(f"Embedding Failed: {e}")
            return [0.0] * 1536  # Return zero vector on failure

    async def log_experience(self, drone_id: int, action: str, state: dict, outcome: str, is_poisoned: bool = False):
        """
        Called by Worker Agents after finishing a task.
        is_poisoned: If True, this is a malicious injection.
        """
        text_representation = f"Drone {drone_id} performed {action} at {state}. Result: {outcome}"
        vector = await self._get_embedding(text_representation)

        self.db.insert_episode(
            drone_id=drone_id,
            action=action,
            state=state,
            outcome=outcome,
            embedding=vector,
            is_poisoned=1 if is_poisoned else 0
        )
        tag = "[POISON]" if is_poisoned else "[Memory]"
        log.info(f"{tag} Logged episode for Drone {drone_id}")

    async def retrieve_context(self, query: str) -> str:
        """Called by Supervisor to learn from past mistakes."""
        vector = await self._get_embedding(query)
        episodic = self.db.find_similar_episodes(vector)
        rules = self.db.find_similar_rules(vector)

        sections = []
        if episodic:
            sections.append("Past Experiences:\n- " + "\n- ".join(episodic))
        if rules:
            sections.append("Relevant Rules:\n- " + "\n- ".join(rules))
        if not sections:
            return "No relevant past experiences or rules found."
        return "\n\n".join(sections)

    async def retrieve_context_details(self, query: str, limit: int = 3) -> dict:
        """Return structured context for CLI/analysis."""
        vector = await self._get_embedding(query)
        episodic = self.db.find_similar_episodes_with_flags(vector, limit=limit)
        rules = self.db.find_similar_rules_with_flags(vector, limit=limit)
        return {"episodic": episodic, "rules": rules}

    def stats(self) -> dict:
        """Lightweight counts for logging/visibility."""
        try:
            return {
                "episodes": self.db.count_episodes(),
                "poisoned_episodes": self.db.count_poisoned(),
                "rules": self.db.count_rules(),
                "poisoned_rules": self.db.count_poisoned_rules(),
            }
        except Exception:
            return {"episodes": 0, "poisoned_episodes": 0, "rules": 0, "poisoned_rules": 0}

    def snapshot(self, episodes: int = 5, rules: int = 5) -> dict:
        """
        Return recent episodes and rules for CLI display.
        """
        try:
            return {
                "episodes": self.db.recent_episodes(limit=episodes),
                "rules": self.db.recent_rules(limit=rules),
            }
        except Exception:
            return {"episodes": [], "rules": []}

    async def add_rule(self, rule_text: str, rule_type: str, location: dict, confidence: float, is_poisoned: bool = False):
        """Add a semantic rule with embedding."""
        vector = await self._get_embedding(rule_text)
        self.db.insert_rule(
            rule_text=rule_text,
            rule_type=rule_type,
            location=location,
            confidence=confidence,
            embedding=vector,
            is_poisoned=1 if is_poisoned else 0
        )
        tag = "[POISON_RULE]" if is_poisoned else "[Rule]"
        log.info(f"{tag} Added semantic rule: {rule_text}")
