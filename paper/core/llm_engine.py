from typing import Any, Dict

# from openai import OpenAI
from core.logger import logger
from config import settings


class LLMEngine:
    """
    Thin wrapper around your LLM client (e.g. OpenAI).
    Wire it up to your preferred model / provider.
    """

    def __init__(self, model: str | None = None) -> None:
        self.model = model or settings.openai_model
        self.api_key = settings.openai_api_key
        # Example if you want to actually hook it up:
        # self.client = OpenAI(api_key=self.api_key)

    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        """
        Async interface for text generation.
        Implement your real LLM call here.
        """
        logger.debug(
            "LLMEngine.generate called",
        )
        # Example skeleton (sync client inside async – replace with real impl):
        # resp = self.client.chat.completions.create(
        #     model=self.model,
        #     messages=[
        #         {"role": "system", "content": system_prompt},
        #         {"role": "user", "content": user_prompt},
        #     ],
        # )
        # return resp.choices[0].message.content

        raise NotImplementedError("Wire up your LLM provider in LLMEngine.generate()")
