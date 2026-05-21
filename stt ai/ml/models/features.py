import os
import json
import logging
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


class KeyMomentsExtractor:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = "gpt-4o-mini"
        self.prompt = (
            os.getenv("KEY_MOMENTS_PROMPT")
            or "Extract the 5-10 most important/quotable moments from this podcast. "
            "Return a JSON object with a 'moments' array. "
            "Each moment must have: "
            '"quote" (exact text), "speaker" (string), '
            '"timestamp" (float in seconds), '
            '"why_important" (string, 1 sentence). '
            "Focus on insights, surprising facts, actionable advice, and memorable statements."
        )

    def extract(self, transcript: str, segments: list[dict]) -> list[dict]:
        if not segments:
            return []
        try:
            truncated = transcript[:6000]
            segments_json = json.dumps([
                {"speaker": s["speaker"], "text": s["text"], "start": s["start"]}
                for s in segments[:200]
            ])

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.prompt},
                    {
                        "role": "user",
                        "content": f"Transcript with timestamps:\n\n{segments_json}\n\nFull text:\n\n{truncated}",
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

            parsed = json.loads(content)
            moments = parsed if isinstance(parsed, list) else parsed.get("moments", [])

            for m in moments:
                if "timestamp" in m and isinstance(m["timestamp"], str):
                    m["timestamp"] = self._time_to_seconds(m["timestamp"])

            return moments
        except Exception as e:
            logger.warning(f"Key moments extraction failed (non-critical): {e}")
            return []

    @staticmethod
    def _time_to_seconds(t: str) -> float:
        parts = str(t).split(":")
        if len(parts) == 2:
            return int(parts[0]) * 60 + float(parts[1])
        elif len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
        return float(t)


class CrossPodcastSearch:
    @staticmethod
    def search_across_vaults(query: str, vault_paths: list[str], top_k: int = 5) -> list[dict]:
        from sentence_transformers import SentenceTransformer
        import numpy as np

        model = SentenceTransformer("all-MiniLM-L6-v2")
        query_vec = model.encode([query]).astype("float32")

        results = []
        for vault_path in vault_paths:
            paragraphs_file = os.path.join(vault_path, "paragraphs.txt")
            if not os.path.exists(paragraphs_file):
                continue
            with open(paragraphs_file, "r", encoding="utf-8") as f:
                paragraphs = [line.strip() for line in f if line.strip()]
            if not paragraphs:
                continue
            para_vecs = model.encode(paragraphs).astype("float32")
            scores = np.dot(para_vecs, query_vec.T).flatten()
            top_indices = np.argsort(scores)[-top_k:][::-1]
            for idx in top_indices:
                results.append({
                    "vault": os.path.basename(vault_path),
                    "text": paragraphs[idx],
                    "score": float(scores[idx]),
                })
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]
