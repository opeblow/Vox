import os
import json
import logging
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


class ChapterGenerator:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = "gpt-4o-mini"
        self.prompt = (
            os.getenv("CHAPTER_PROMPT")
            or "Divide this podcast transcript into logical chapters/topics. "
            "Return ONLY a valid JSON array with objects containing: "
            '"title" (string), "start_time" (float in seconds), '
            '"end_time" (float in seconds), "description" (string, 1 sentence). '
            "Each chapter should cover a distinct topic or segment."
        )

    def generate(self, transcript: str, segments: list[dict]) -> list[dict]:
        if not transcript or len(transcript) < 100:
            return [{"title": "Full Episode", "start_time": 0.0, "end_time": segments[-1]["end"] if segments else 0, "description": "Complete podcast episode"}]

        try:
            truncated = transcript[:8000]
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.prompt},
                    {"role": "user", "content": f"Transcript:\n\n{truncated}"},
                ],
                temperature=0.1,
                response_format={"type": "json_object"},
            )
            content = response.choices[0].message.content

            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            parsed = json.loads(content)
            chapters = parsed if isinstance(parsed, list) else parsed.get("chapters", [])

            for ch in chapters:
                if isinstance(ch.get("start_time"), str):
                    ch["start_time"] = self._time_to_seconds(ch["start_time"])
                if isinstance(ch.get("end_time"), str):
                    ch["end_time"] = self._time_to_seconds(ch["end_time"])

            return chapters
        except Exception as e:
            logger.warning(f"Chapter generation failed (non-critical): {e}")
            return [{"title": "Full Episode", "start_time": 0.0, "end_time": segments[-1]["end"] if segments else 0, "description": "Complete podcast episode"}]

    @staticmethod
    def _time_to_seconds(t: str) -> float:
        parts = str(t).split(":")
        if len(parts) == 2:
            return int(parts[0]) * 60 + float(parts[1])
        elif len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
        return float(t)
