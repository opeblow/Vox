import os
import json
import logging
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


class PodcastComparator:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = "gpt-4o-mini"

    def compare(self, podcast_a: dict, podcast_b: dict) -> dict:
        try:
            summary_a = podcast_a.get("summary", "")[:2000]
            summary_b = podcast_b.get("summary", "")[:2000]
            chapters_a = json.dumps(podcast_a.get("chapters", [])[:10])
            chapters_b = json.dumps(podcast_b.get("chapters", [])[:10])
            moments_a = json.dumps(podcast_a.get("key_moments", [])[:5])
            moments_b = json.dumps(podcast_b.get("key_moments", [])[:5])

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a podcast analyst. Compare two podcast episodes and provide insights. "
                            "Return a JSON object with: "
                            '"overlap_score" (float 0-1, how much they overlap in topics), '
                            '"shared_topics" (list of strings), '
                            '"unique_to_a" (list of topics only in podcast A), '
                            '"unique_to_b" (list of topics only in podcast B), '
                            '"recommendation" (string, which to listen to first and why), '
                            '"comparison_summary" (string, 2-3 sentences).'
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"PODCAST A:\nSummary: {summary_a}\nChapters: {chapters_a}\n"
                            f"Key Moments: {moments_a}\n\n"
                            f"PODCAST B:\nSummary: {summary_b}\nChapters: {chapters_b}\n"
                            f"Key Moments: {moments_b}"
                        ),
                    },
                ],
                temperature=0.2,
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            return json.loads(content)

        except Exception as e:
            logger.warning(f"Podcast comparison failed: {e}")
            return {"overlap_score": 0, "shared_topics": [], "unique_to_a": [], "unique_to_b": [], "recommendation": "Could not compare", "comparison_summary": ""}

    @staticmethod
    def compute_similarity(embedding_a: list[float], embedding_b: list[float]) -> float:
        import numpy as np
        a = np.array(embedding_a)
        b = np.array(embedding_b)
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-10))
