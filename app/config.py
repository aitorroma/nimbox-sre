from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    # Telegram
    telegram_bot_token: str = ""
    telegram_webhook_secret: str = ""
    
    # Nightingale MCP
    nightingale_api_url: str = "https://collector.nimbox360.com/@warpgate/admin/api"
    nightingale_token: str = ""
    
    # Warpgate
    warpgate_api_url: str = "https://collector.nimbox360.com/@warpgate/admin/api"
    warpgate_token: str = ""
    
    # OpenSRE
    opensre_url: str = "https://sre.nimbox360.com"
    
    # LLM (OpenAI-compatible)
    llm_api_key: str = ""
    llm_base_url: str = "https://api.nan.builders/v1"
    llm_model: str = "qwen3.6"
    
    # App
    app_base_url: str = ""
    state_db_path: str = "/tmp/nimbox-sre-state.db"
    output_dir: str = "/tmp/nimbox-sre-output"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
    
    def output_path(self) -> Path:
        return Path(self.output_dir)


settings = Settings()
