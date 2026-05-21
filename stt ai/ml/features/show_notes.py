import os
import json
import logging
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


class ShowNotesGenerator:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = "gpt-4o-mini"

    def generate(self, metadata: dict) -> dict:
        try:
            summary = metadata.get("summary", "")[:1500]
            chapters = json.dumps(metadata.get("chapters", [])[:15])
            moments = json.dumps(metadata.get("key_moments", [])[:10])
            speaker_count = metadata.get("speakers_count", 0)
            language = metadata.get("language", "en")

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an expert podcast show notes writer. Generate SEO-optimized show notes. "
                            "Return a JSON object with: "
                            '"seo_title" (string, max 60 chars), '
                            '"seo_description" (string, max 160 chars), '
                            '"tags" (array of 5-10 topic tags), '
                            '"key_takeaways" (array of 3-5 bullet points), '
                            '"tweet" (string, a viral tweet about this episode), '
                            '"linkedin_post" (string, professional summary), '
                            '"suggested_guests" (array of related expert topics).'
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Generate show notes for this podcast:\n\n"
                            f"Summary: {summary}\nChapters: {chapters}\n"
                            f"Key Moments: {moments}\n"
                            f"Speakers: {speaker_count}\nLanguage: {language}"
                        ),
                    },
                ],
                temperature=0.3,
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            return json.loads(content)

        except Exception as e:
            logger.warning(f"Show notes generation failed: {e}")
            return {"seo_title": "", "seo_description": "", "tags": [], "key_takeaways": [], "tweet": "", "linkedin_post": ""}
