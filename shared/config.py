from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/tasks_db"
    RABBITMQ_URL: str = "amqp://guest:guest@localhost:5672/"
    RABBITMQ_QUEUE: str = "tasks"

    model_config = {
        "env_file": Path(__file__).parent / ".env",
        "env_file_encoding": "utf-8"
    }


settings = Settings()
