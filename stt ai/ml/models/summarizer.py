import os
import logging
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

logger = logging.getLogger(__name__)


class Summarizer:
    def __init__(self, custom_prompt: str | None = None):
        api_key = os.getenv("OPENAI_API_KEY")
        self.system_prompt = (
            custom_prompt
            or os.getenv("SUMMARIZER_SYSTEM_PROMPT")
            or "You are an expert podcast analyst. Summarize the key insights, main topics, and actionable takeaways from this podcast transcript. Be concise but comprehensive."
        )
        self.client = OpenAI(api_key=api_key)
        self.model = "gpt-4o-mini"

    def summarize(self, transcript_text: str) -> str:
        if not transcript_text or not transcript_text.strip():
            return "Transcript is empty"
        logger.info("Generating AI summary...")
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": f"Summarize this podcast transcript:\n\n{transcript_text}"},
                ],
                temperature=0.2,
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Summarize Error: {e}")
            return f"Summary generation failed: {str(e)}"
