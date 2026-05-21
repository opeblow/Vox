from pydantic_settings import BaseSettings


class AppSettings(BaseSettings):
    JWT_SECRET_KEY: str
    PAYSTACK_SECRET_KEY: str = ""
    PAYSTACK_PUBLIC_KEY: str = ""
    DATABASE_URL: str = "sqlite:///./podcast.db"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    RATE_LIMIT_PER_MINUTE: int = 100
    OPENAI_API_KEY: str = ""
    REDIS_URL: str = ""
    SUMMARIZER_SYSTEM_PROMPT: str = "You are an expert podcast analyst. Summarize the key insights."
    QA_SYSTEM_PROMPT: str = "Answer based only on the provided podcast context."
    CHAPTER_PROMPT: str = "Divide this podcast transcript into chapters. Return JSON array with title, start_time, end_time."
    KEY_MOMENTS_PROMPT: str = "Extract the most important quotes from this podcast. Return JSON array."

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "case_sensitive": True}


settings = AppSettings()
