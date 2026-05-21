import os
import sys
import time
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

try:
    from ml.pipelines.podcast_pipeline import PodcastPipeline
except ImportError as e:
    print(f"Error importing ML pipeline: {e}")
    print("Make sure openai-whisper is installed: pip install openai-whisper")
    sys.exit(1)


def run_interactive_test():
    print("\n" + "=" * 60)
    print("VAULTAI ML ENGINE: DIARIZATION VALIDATION")
    print("=" * 60)

    USER_ID = "230405013"
    PODCAST_ID = "Beta_Test_Run_01"
    AUDIO_PATH = str(ROOT_DIR / "data" / "samples" / "test_audio.mpeg")

    for folder in [ROOT_DIR / "data" / "samples", ROOT_DIR / "storage" / "users"]:
        folder.mkdir(parents=True, exist_ok=True)

    if not os.path.exists(AUDIO_PATH):
        print(f"\nFILE MISSING: Place an audio file at: {AUDIO_PATH}")
        print("Supported formats: .mp3, .wav, .m4a, .mpeg, .ogg, .flac")
        return

    try:
        print("\nInitializing ML Engine (Loading Whisper)...")
        pipeline = PodcastPipeline()
        print(f"\nINGESTING: Processing audio for user_{USER_ID}")
        start_time = time.time()
        result = pipeline.execute(USER_ID, PODCAST_ID, AUDIO_PATH)
        duration = time.time() - start_time

        print(f"\nSUCCESS: Processing completed in {duration:.2f} seconds")
        print(f"Language: {result.get('language', 'Unknown').upper()}")
        print(f"Speakers: {result.get('speaker_count', 0)}")
        print(f"Speaker List: {result.get('speakers', [])}")
        print(f"Chapters: {len(result.get('chapters', []))}")
        print(f"Key Moments: {len(result.get('key_moments', []))}")
        print(f"Vault Path: {result.get('vault_path')}")

        print("\n" + "-" * 60)
        print("SPEAKER TRANSCRIPT PREVIEW (first 5 segments)")
        print("-" * 60)
        for seg in result.get("labeled_segments", [])[:5]:
            print(f"[{seg['start']:>6.2f}s -> {seg['end']:>6.2f}s] {seg['speaker']:>8}: {seg['text'][:90]}{'...' if len(seg['text']) > 90 else ''}")

        print("\n" + "-" * 60)
        print("AI EXECUTIVE SUMMARY")
        summary = result.get("summary", "No summary generated")
        print(summary[:500] + ("..." if len(summary) > 500 else ""))

        print("\n" + "-" * 60)
        print("CHAPTERS")
        for ch in result.get("chapters", []):
            print(f"  - {ch.get('title', 'Untitled')} @ {ch.get('start_time', 0):.1f}s")

        print("\n" + "=" * 70)
        print("VAULT IS OPEN. Ask anything about the podcast.")
        print("Type 'q' or 'quit' to exit")

        while True:
            query = input("\nASK THE AI: ").strip()
            if query.lower() in ['exit', 'quit', 'q']:
                print("\nVault Locked. Session Ended.")
                break
            if not query:
                continue
            print("Searching vault...")
            q_start = time.time()
            answer = pipeline.ask_ai(query)
            q_end = time.time()
            print(f"\nAI RESPONSE ({q_end - q_start:.2f}s):")
            print(answer)
            print("\n" + "-" * 50)

    except Exception as e:
        print(f"Critical Error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    run_interactive_test()
