"""Configuration management with .env support."""
import os
from functools import lru_cache
from typing import List, Optional
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load .env file
load_dotenv()


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Server
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_URL: str = "http://localhost:8000"
    DEBUG: str = "False"  # Accept string, will be converted to bool
    
    # CORS
    CORS_ORIGINS: str = "http://localhost:8000,http://127.0.0.1:8000,http://localhost:8001,http://127.0.0.1:8001,http://127.0.0.1:59127"
    CORS_ALLOW_CREDENTIALS: bool = True
    
    # Supabase (Authentication & Database)
    SUPABASE_URL: Optional[str] = None
    SUPABASE_ANON_KEY: Optional[str] = None
    
    
    # Ollama / LLM
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.2"
    OLLAMA_FALLBACK_MODEL: str = "mistral"
    
    # OpenAI (Optional)
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4"
    
    # Anthropic (Optional)
    ANTHROPIC_API_KEY: Optional[str] = None
    ANTHROPIC_MODEL: str = "claude-3-sonnet-20240229"
    
    # Groq (Optional)
    GROQ_API_KEY: Optional[str] = None
    GROQ_MODEL: str = "llama-3.3-70b-specdec"
    
    # Gemini (Primary)
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-3.1-flash-lite"
    GEMINI_FALLBACK_MODEL: str = "gemini-3-flash"
    
    # Vector DB
    CHROMA_DB_PATH: str = "./chroma_db"
    CHROMA_COLLECTION_NAME: str = "manuals"
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    
    # Document Processing
    UPLOAD_DIR: str = "./uploads"
    MAX_FILE_SIZE_MB: int = 100
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    
    # JWT Auth
    JWT_SECRET_KEY: str = "your-super-secret-jwt-key-change-this-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 480
    
    # Admin
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD_HASH: str = "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewKyNiAYMyzJ/I1K"
    
    # Database
    DATABASE_URL: str = "sqlite:///./indexfield.db"
    
    # SharePoint
    SHAREPOINT_CLIENT_ID: Optional[str] = None
    SHAREPOINT_CLIENT_SECRET: Optional[str] = None
    SHAREPOINT_TENANT_ID: Optional[str] = None
    SHAREPOINT_SITE_URL: Optional[str] = None
    
    # CMMS
    CMMS_API_KEY: Optional[str] = None
    CMMS_API_URL: Optional[str] = None
    CMMS_PROVIDER: Optional[str] = None
    
    # MQTT / IoT
    MQTT_BROKER_HOST: Optional[str] = None
    MQTT_BROKER_PORT: int = 1883
    MQTT_USERNAME: Optional[str] = None
    MQTT_PASSWORD: Optional[str] = None
    
    # Webhooks
    WEBHOOK_URL: Optional[str] = None
    WEBHOOK_SECRET: Optional[str] = None
    
    # Cloud Storage
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_REGION: str = "us-east-1"
    S3_BUCKET_NAME: Optional[str] = None
    
    AZURE_STORAGE_CONNECTION_STRING: Optional[str] = None
    AZURE_CONTAINER_NAME: Optional[str] = None
    
    GOOGLE_APPLICATION_CREDENTIALS: Optional[str] = None
    GCS_BUCKET_NAME: Optional[str] = None
    
    # Email
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    ALERT_EMAIL: Optional[str] = None
    
    # Slack (Optional - Webhook for simple notifications)
    SLACK_WEBHOOK_URL: Optional[str] = None
    SLACK_CHANNEL: str = "#maintenance-alerts"
    
    # Slack App Credentials (Full API access)
    SLACK_APP_ID: Optional[str] = None
    SLACK_CLIENT_ID: Optional[str] = None
    SLACK_CLIENT_SECRET: Optional[str] = None
    SLACK_SIGNING_SECRET: Optional[str] = None
    SLACK_VERIFICATION_TOKEN: Optional[str] = None
    SLACK_BOT_TOKEN: Optional[str] = None  # xoxb-... token for bot actions
    
    # Feature Flags
    ENABLE_TELEMETRY: bool = True
    ENABLE_KNOWLEDGE_VAULT: bool = True
    ENABLE_WORK_ORDERS: bool = True
    ENABLE_ANOMALY_DETECTION: bool = True
    ENABLE_CLOUD_BACKUP: bool = False
    ENABLE_REAL_TELEMETRY: bool = False
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "./logs/indexfield.log"
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins string into list."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]
    
    @property
    def debug_bool(self) -> bool:
        """Convert DEBUG string to boolean."""
        if isinstance(self.DEBUG, bool):
            return self.DEBUG
        return str(self.DEBUG).lower() in ('true', '1', 'yes', 'on')
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"
    


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
