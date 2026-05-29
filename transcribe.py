import os
import sys
import uuid
import argparse
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")


def download_audio(url: str) -> str:
    import yt_dlp

    session_id = str(uuid.uuid4())[:8]
    out_dir = os.path.join(OUTPUT_DIR, session_id)
    os.makedirs(out_dir, exist_ok=True)

    output_template = os.path.join(out_dir, "%(title)s.%(ext)s")
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": output_template,
        "quiet": True,
        "no_warnings": True,
    }
    logger.info("Downloading audio from URL...")
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        title = info.get("title", "audio")

    m4a_files = [f for f in os.listdir(out_dir) if f.endswith(".m4a") and not f.endswith(".part")]
    if m4a_files:
        audio_path = os.path.join(out_dir, m4a_files[0])
        logger.info(f"Downloaded: {title} ({os.path.getsize(audio_path) / 1024 / 1024:.1f} MB)")
        return audio_path, title

    raise FileNotFoundError(f"No audio file found after downloading {url}")


def transcribe(audio_path: str) -> str:
    from faster_whisper import WhisperModel

    logger.info("Loading Whisper model (tiny)...")
    model = WhisperModel("tiny", device="cpu", compute_type="int8", cpu_threads=4)
    logger.info("Transcribing audio...")
    segments, info = model.transcribe(audio_path, beam_size=1, vad_filter=True)
    text = " ".join(seg.text for seg in segments)
    logger.info(f"Transcription done: {len(text)} chars")
    return text


def generate_notes(transcript: str, title: str) -> str:
    import dotenv
    from openai import OpenAI

    env_path = os.path.join(os.path.dirname(__file__), "stt ai", ".env")
    dotenv.load_dotenv(env_path)

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    system_prompt = """You are an AI assistant that transforms raw speech-to-text transcripts into high-quality study notes.

Your tasks:
1. Clean & fix grammar — Remove filler words, repetitions, false starts. Fix grammar. Make it read naturally.
2. Format into readable notes — Break into logical paragraphs with section breaks. NOT a wall of text.
3. Preserve all important content — Keep all subject matter, facts, names, dates, concepts.
4. Output format:
   - First section: Cleaned, formatted transcript as proper study notes (with markdown headings)
   - Then a "--- SUMMARY & KEY POINTS ---" divider
   - Then: Brief summary of the session
   - Then: Bullet-point key takeaways
   - Then: Any action items or questions raised"""

    logger.info("Generating cleaned study notes via AI...")
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Here is the raw transcript from a class recording titled '{title}'. Please clean it and produce study notes with summary and key points:\n\n{transcript}"},
        ],
        temperature=0.3,
    )
    return response.choices[0].message.content


def main():
    parser = argparse.ArgumentParser(description="Lecture URL to Study Notes")
    parser.add_argument("url", help="URL of the class/meeting recording")
    args = parser.parse_args()

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    try:
        audio_path, title = download_audio(args.url)
    except Exception as e:
        logger.error(f"Download failed: {e}")
        sys.exit(1)

    try:
        transcript = transcribe(audio_path)
        transcript_path = os.path.join(os.path.dirname(audio_path), "transcript.txt")
        with open(transcript_path, "w", encoding="utf-8") as f:
            f.write(transcript)
        logger.info(f"Raw transcript saved: {transcript_path}")
    except Exception as e:
        logger.error(f"Transcription failed: {e}")
        sys.exit(1)

    try:
        notes = generate_notes(transcript, title)
        notes_path = os.path.join(os.path.dirname(audio_path), "study_notes.md")
        with open(notes_path, "w", encoding="utf-8") as f:
            f.write(notes)
        logger.info(f"Study notes saved: {notes_path}")
    except Exception as e:
        logger.error(f"Notes generation failed: {e}")
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f"  Done! Open your study notes:")
    print(f"  {notes_path}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
