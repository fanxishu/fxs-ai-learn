from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    PROJECT_NAME: str = "鱼皮 AI 闯关学习小程序"
    API_V1_PREFIX: str = "/api/v1"
    BACKEND_CORS_ORIGINS: str = "*"
    VERSION: str = "1.0.0"

    DEEPSEEK_API_KEY: Optional[str] = None
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com/v1"
    DEEPSEEK_MODEL: str = "deepseek-chat"
    DEEPSEEK_TIMEOUT: int = 30
    DEEPSEEK_TEMPERATURE_QUIZ: float = 0.4
    DEEPSEEK_TEMPERATURE_REPORT: float = 0.5
    DEEPSEEK_MAX_RETRIES: int = 2

    USE_MOCK_LLM: bool = True

    USER_INPUT_MIN_LEN: int = 5
    USER_INPUT_MAX_LEN: int = 500
    DEFAULT_QUESTION_COUNT: int = 5
    MIN_QUESTION_COUNT: int = 3
    MAX_QUESTION_COUNT: int = 5

    SENSITIVE_WORDS_FILE: str = "app/utils/sensitive_words.txt"

    DB_DRIVER: str = "pymysql"
    DB_HOST: str = "127.0.0.1"
    DB_PORT: int = 3306
    DB_USER: str = "root"
    DB_PASSWORD: str = ""
    DB_NAME: str = "fxs_ai_learn"

    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_DAYS: int = 7

    WECHAT_APPID: Optional[str] = None
    WECHAT_APPSECRET: Optional[str] = None

    USE_MOCK_WX_LOGIN: bool = True

    @property
    def database_url(self) -> str:
        return (
            f"mysql+aiomysql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
            f"?charset=utf8mb4"
        )


settings = Settings()
