from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env"))

    """Application settings"""
    LINKEDIN_USERNAME: str=''
    LINKEDIN_PASSWORD: str=''
    MONGODB_URL: str = "mongodb://localhost:27017"
    RABBITMQ_URL: str = "amqp://guest:guest@localhost:5672/"
    SCROLL_LIMIT: int = 10
    MAX_POSTS: int = 500


settings = Settings()