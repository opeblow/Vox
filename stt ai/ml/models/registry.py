import logging
import threading

logger = logging.getLogger(__name__)


class ModelRegistry:
    _instances = {}
    _lock = threading.RLock()

    @classmethod
    def get(cls, key: str, builder):
        if key not in cls._instances:
            with cls._lock:
                if key not in cls._instances:
                    logger.info(f"[REGISTRY] Building singleton: {key}")
                    cls._instances[key] = builder()
        return cls._instances[key]

    @classmethod
    def clear(cls):
        with cls._lock:
            cls._instances.clear()
            logger.info("[REGISTRY] All models cleared")

    @classmethod
    def warmup(cls):
        from ml.models.stt import SpeechToText
        from ml.models.embeddings import Embedder
        from ml.models.summarizer import Summarizer

        logger.info("[REGISTRY] Warming up models...")
        stt = cls.get("stt", lambda: SpeechToText(model_name="base"))
        stt._ensure_model()

        embedder = cls.get("embedder", lambda: Embedder())
        _ = embedder.model

        summarizer = cls.get("summarizer", lambda: Summarizer())
        _ = summarizer.client

        logger.info("[REGISTRY] All models warmed up")
