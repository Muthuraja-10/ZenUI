from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    app_name: str = "ZenUI Enterprise"

    app_version: str = "0.1.0"

    groq_api_key: str

    groq_model: str
    
    serper_api_key: str

    linkup_api_key: str

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()