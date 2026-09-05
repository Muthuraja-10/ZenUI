from groq import AsyncGroq

from app.core.config import settings
from app.llm.base import LLMProvider


class GroqProvider(LLMProvider):

    def __init__(self):
        self.client = AsyncGroq(
            api_key=settings.groq_api_key
        )

    async def generate(self, prompt: str) -> str:

        response = await self.client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
        )

        return response.choices[0].message.content