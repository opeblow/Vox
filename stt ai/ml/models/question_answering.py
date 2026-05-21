import os
import logging
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class QAMachine:
    def __init__(self, embedder_machine, custom_prompt: str | None = None):
        self.embedder = embedder_machine
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.system_prompt = (
            custom_prompt
            or os.getenv("QA_SYSTEM_PROMPT")
            or "You are a podcast AI assistant. Answer questions based ONLY on the provided podcast context. If the answer isn't in the context, say so."
        )
        self.model = "gpt-4o-mini"

    def ask(self, user_question: str) -> str:
        logger.info(f"Processing question: {user_question}")

        context_chunks = self.embedder.search(user_question, k=3)
        context_text = "\n--\n".join(context_chunks)

        if not context_text.strip():
            return "No relevant context found in this podcast to answer your question."

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {
                        "role": "user",
                        "content": f"CONTEXT FROM PODCAST:\n{context_text}\n\nUSER QUESTION: {user_question}",
                    },
                ],
                temperature=0,
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"QA Error: {e}")
            return "I encountered an error trying to find that answer."
