import os
import json
import logging
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


class SentimentAnalyzer:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = "gpt-4o-mini"

    def analyze(self, segments: list[dict]) -> dict:
        if not segments:
            return {"overall_sentiment": "neutral", "speaker_sentiments": {}, "highlights": []}

        try:
            transcript_excerpt = "\n".join(
                f"{s['speaker']}: {s['text']}" for s in segments[:100]
            )[:4000]

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Analyze the sentiment and emotional tone of this podcast transcript. "
                            "Return a JSON object with: "
                            '"overall_sentiment" (string: positive/negative/neutral/mixed), '
                            '"sentiment_score" (float 0-1, 1=most positive), '
                            '"speaker_sentiments" (object mapping speaker names to their sentiment), '
                            '"emotional_arc" (string describing how sentiment changes), '
                            '"most_exciting_moment" (string, the most energetic part), '
                            '"tone_description" (string, e.g. "enthusiastic", "serious", "casual"). '
                            "Be concise."
                        ),
                    },
                    {
                        "role": "user",
                        "content": f"Transcript:\n\n{transcript_excerpt}",
                    },
                ],
                temperature=0.1,
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            return json.loads(content)

        except Exception as e:
            logger.warning(f"Sentiment analysis failed: {e}")
            return {"overall_sentiment": "neutral", "speaker_sentiments": {}, "highlights": []}
