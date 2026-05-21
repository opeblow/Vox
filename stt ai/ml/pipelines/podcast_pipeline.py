import os
import json
from ml.utils.audio import load_and_process
from ml.utils.text import chunk_text, clean_text
from ml.models.stt import SpeechToText
from ml.models.summarizer import Summarizer
from ml.models.vector_store import VectorMachine
from ml.models.embeddings import Embedder
from ml.models.question_answering import QAMachine
from ml.models.chapter import ChapterGenerator
from ml.models.features import KeyMomentsExtractor
from ml.models.registry import ModelRegistry
from ml.features.sentiment import SentimentAnalyzer
from ml.features.show_notes import ShowNotesGenerator
from dotenv import load_dotenv

load_dotenv()


class PodcastPipeline:
    def __init__(self, use_singletons: bool = True):
        if use_singletons:
            self.stt_engine = ModelRegistry.get("stt", lambda: SpeechToText(model_name="base"))
            self.summarizer_engine = ModelRegistry.get("summarizer", lambda: Summarizer())
            self.embedder_engine = ModelRegistry.get("embedder", lambda: Embedder())
            self.qa_machine = QAMachine(embedder_machine=self.embedder_engine)
        else:
            self.stt_engine = SpeechToText(model_name="base")
            self.summarizer_engine = Summarizer()
            self.embedder_engine = Embedder()
            self.qa_machine = QAMachine(embedder_machine=self.embedder_engine)

        self.vector_store = VectorMachine()
        self.chapter_engine = ChapterGenerator()
        self.key_moments_engine = KeyMomentsExtractor()
        self.sentiment_engine = SentimentAnalyzer()
        self.show_notes_engine = ShowNotesGenerator()
        self.current_vault_path = None
        print("[PIPELINE] VaultAI ML Engine Initialized")

    def execute(self, user_id, podcast_id, audio_input_path):
        print(f"\n[PIPELINE] Processing for user {user_id}")

        processed_audio_path = load_and_process(audio_input_path)
        print("[PIPELINE] Generating speaker-aware transcript...")
        labeled_segments, language_info = self.stt_engine.transcribe_with_timestamps(processed_audio_path)
        speaker_transcript = "\n".join([s["labeled_text"] for s in labeled_segments])
        print(f"[PIPELINE] Language: {language_info.upper()}")

        full_text = " ".join([s["text"] for s in labeled_segments])
        cleaned_text = clean_text(full_text)
        chunks = chunk_text(cleaned_text)

        print("[PIPELINE] Building vector index...")
        user_vault_path = os.path.join("storage", "users", str(user_id), "indices", str(podcast_id))
        os.makedirs(user_vault_path, exist_ok=True)
        self.embedder_engine.add_to_index(chunks)
        self.embedder_engine.save(folder_path=user_vault_path)
        self.vector_store.current_vault_path = user_vault_path
        self.current_vault_path = user_vault_path

        print("[PIPELINE] Generating AI summary...")
        summary = self.summarizer_engine.summarize(speaker_transcript)

        print("[PIPELINE] Detecting chapters...")
        chapters = self.chapter_engine.generate(speaker_transcript, labeled_segments)

        print("[PIPELINE] Extracting key moments...")
        key_moments = self.key_moments_engine.extract(speaker_transcript, labeled_segments)

        print("[PIPELINE] Analyzing sentiment...")
        sentiment = self.sentiment_engine.analyze(labeled_segments)

        print("[PIPELINE] Generating show notes...")
        speakers_found = list(set(s["speaker"] for s in labeled_segments))
        duration = labeled_segments[-1]["end"] if labeled_segments else 0
        metadata = {
            "user_id": user_id,
            "podcast_id": podcast_id,
            "language": language_info,
            "speakers": speakers_found,
            "speakers_count": len(speakers_found),
            "segments": labeled_segments,
            "summary": summary,
            "chapters": chapters,
            "key_moments": key_moments,
            "sentiment": sentiment,
            "duration_seconds": duration,
            "transcript": speaker_transcript,
        }

        show_notes = self.show_notes_engine.generate(metadata)
        metadata["show_notes"] = show_notes

        with open(os.path.join(user_vault_path, "metadata.json"), "w") as f:
            json.dump(metadata, f, indent=2)

        print(f"[PIPELINE] {podcast_id} fully processed")

        return {
            "status": "success",
            "language": language_info,
            "summary": summary,
            "vault_path": user_vault_path,
            "labeled_segments": labeled_segments,
            "speaker_count": len(speakers_found),
            "speakers": speakers_found,
            "chapters": chapters,
            "key_moments": key_moments,
            "sentiment": sentiment,
            "show_notes": show_notes,
        }

    def ask_ai(self, question: str) -> str:
        print(f"[PIPELINE] Query: '{question}'")
        return self.qa_machine.ask(user_question=question)

    def _init_qa(self):
        self.qa_machine = QAMachine(embedder_machine=self.embedder_engine)
        return self.qa_machine
