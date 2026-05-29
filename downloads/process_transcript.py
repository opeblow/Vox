import os
import sys
from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(__file__), '..', 'stt ai', '.env')
load_dotenv(env_path)

from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

raw_path = os.path.join(os.path.dirname(__file__), 'transcript.txt')
with open(raw_path, 'r', encoding='utf-8') as f:
    raw_text = f.read()

print(f"Raw transcript: {len(raw_text)} chars")

SYSTEM_PROMPT = """You are an AI assistant that transforms raw speech-to-text transcripts into high-quality study notes.

Your tasks:
1. **Clean & fix grammar** — Remove filler words, repetitions, false starts. Fix grammar. Make it read naturally.
2. **Format into readable notes** — Break into logical paragraphs. Use clear section breaks for topic changes. NOT a wall of text.
3. **Preserve all important content** — Keep all subject matter, facts, names, dates, concepts. Don't lose information.
4. **Speaker labels** — Keep speaker changes visible (HOST:, GUEST_1:, etc.) to show discussion flow.
5. **Output format**:
   - First section: Cleaned, formatted transcript as proper study notes
   - Then a "--- SUMMARY & KEY POINTS ---" divider
   - Then: Brief summary of the session
   - Then: Bullet-point key takeaways
   - Then: Any action items or questions raised"""

response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Here is the raw transcript from a class recording. Please clean it and produce study notes with summary and key points:\n\n{raw_text}"},
    ],
    temperature=0.3,
)

output = response.choices[0].message.content

notes_path = os.path.join(os.path.dirname(__file__), 'study_notes.txt')
with open(notes_path, 'w', encoding='utf-8') as f:
    f.write(output)

print(f"\n--- Study notes saved to: {notes_path} ---")
print(f"Output length: {len(output)} chars")
print("\n" + "="*60)
print(output[:3000])
if len(output) > 3000:
    print(f"\n... ({len(output) - 3000} more chars)")
