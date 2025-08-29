"""
Configuration Settings Module
Manages all application settings and environment variables
"""

import os
from pathlib import Path
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, validator
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Normalize list-like envs for pydantic-settings v2 (expects JSON for complex types)
def _normalize_env_list(var: str, default_list):
    val = os.getenv(var, None)
    if val is None:
        # Set default JSON string so parsing works
        os.environ[var] = str(default_list).replace("'", '"')
        return
    # If empty or not JSON array, convert comma-separated values to JSON
    s = val.strip()
    if not s:
        os.environ[var] = str(default_list).replace("'", '"')
    elif not (s.startswith("[") and s.endswith("]")):
        items = [p.strip() for p in s.split(",") if p.strip()]
        os.environ[var] = str(items).replace("'", '"')

# Apply normalization before Settings model is created
_normalize_env_list("SUPPORTED_VIDEO_FORMATS", ["mp4", "avi", "mov", "mkv"])
_normalize_env_list("CORS_ORIGINS", ["http://localhost:3000"])

class Settings(BaseSettings):
    """Application configuration settings"""
    # Pydantic v2 settings config: ignore unrelated env keys, load .env, case insensitive
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )
    
    # API Keys
    gemini_api_key: str = Field(default="", env="GEMINI_API_KEY")
    google_api_key: str = Field(default="", env="GOOGLE_CUSTOM_SEARCH_API_KEY")
    google_search_engine_id: str = Field(default="", env="GOOGLE_SEARCH_ENGINE_ID")
    
    # Supabase Configuration
    supabase_url: str = Field(default="", env="SUPABASE_URL")
    supabase_anon_key: str = Field(default="", env="SUPABASE_ANON_KEY")
    supabase_service_key: str = Field(default="", env="SUPABASE_SERVICE_KEY")
    
    # Paths
    watch_folder_path: Path = Field(default=Path("/tmp/watch"), env="WATCH_FOLDER_PATH")
    temp_folder_path: Path = Field(default=Path("/tmp/temp"), env="TEMP_FOLDER_PATH")
    log_folder_path: Path = Field(default=Path("/tmp/logs"), env="LOG_FOLDER_PATH")
    
    # Video Processing Settings
    max_daily_uploads_per_channel: int = Field(default=3, env="MAX_DAILY_UPLOADS_PER_CHANNEL")
    max_file_size_mb: int = Field(default=150, env="MAX_FILE_SIZE_MB")
    min_file_size_mb: int = Field(default=10, env="MIN_FILE_SIZE_MB")
    supported_video_formats: List[str] = Field(
        default=["mp4", "avi", "mov", "mkv"],
        env="SUPPORTED_VIDEO_FORMATS"
    )
    batch_size: int = Field(default=10, env="BATCH_SIZE")
    worker_threads: int = Field(default=4, env="WORKER_THREADS")
    
    # Security
    encryption_key: str = Field(default="", env="ENCRYPTION_KEY")
    jwt_secret_key: str = Field(default="", env="JWT_SECRET_KEY")
    
    # API Server Settings
    api_host: str = Field(default="0.0.0.0", env="API_HOST")
    api_port: int = Field(default=8000, env="API_PORT")
    debug_mode: bool = Field(default=False, env="DEBUG_MODE")
    cors_origins: List[str] = Field(
        default=["http://localhost:3000"],
        env="CORS_ORIGINS"
    )
    
    # Optional Services
    coupang_access_key: Optional[str] = Field(default=None, env="COUPANG_ACCESS_KEY")
    coupang_secret_key: Optional[str] = Field(default=None, env="COUPANG_SECRET_KEY")
    redis_url: Optional[str] = Field(default=None, env="REDIS_URL")
    sentry_dsn: Optional[str] = Field(default=None, env="SENTRY_DSN")
    
    # Application Settings
    app_name: str = "UGC Video Manager"
    app_version: str = "1.0.0"
    
    @validator("supported_video_formats", pre=True)
    def parse_video_formats(cls, v):
        if isinstance(v, str):
            return v.split(",")
        return v
    
    @validator("cors_origins", pre=True)
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return v.split(",")
        return v
    
    @validator("watch_folder_path", "temp_folder_path", "log_folder_path")
    def create_folders(cls, v):
        """Create folders if they don't exist"""
        if v:
            path = Path(v)
            path.mkdir(parents=True, exist_ok=True)
            return path
        return v
    
    def validate_required_settings(self):
        """Validate that all required settings are present"""
        errors = []
        
        # Check required API keys
        if not self.gemini_api_key:
            errors.append("GEMINI_API_KEY is required")
        
        # Check Supabase settings
        if not self.supabase_url:
            errors.append("SUPABASE_URL is required")
        if not self.supabase_anon_key:
            errors.append("SUPABASE_ANON_KEY is required")
        
        # Check security keys
        if not self.encryption_key:
            errors.append("ENCRYPTION_KEY is required (32 bytes)")
        elif len(self.encryption_key) != 32:
            errors.append("ENCRYPTION_KEY must be exactly 32 bytes")
        
        if errors:
            raise ValueError(f"Configuration errors: {', '.join(errors)}")
    
    def get_video_extensions(self) -> List[str]:
        """Get video file extensions with dots"""
        return [f".{ext}" for ext in self.supported_video_formats]
    
    def is_valid_video_file(self, filename: str) -> bool:
        """Check if file is a valid video format"""
        return any(filename.lower().endswith(ext) for ext in self.get_video_extensions())
    
    def get_max_file_size_bytes(self) -> int:
        """Get max file size in bytes"""
        return self.max_file_size_mb * 1024 * 1024
    
    def get_min_file_size_bytes(self) -> int:
        """Get min file size in bytes"""
        return self.min_file_size_mb * 1024 * 1024
    
    # Pydantic v1 legacy Config not supported alongside model_config (removed)

# Create global settings instance
settings = Settings()

# Development/production import-time behavior
try:
    if settings.debug_mode:
        print("⚠️  Running in DEBUG mode")
        print(f"📁 Watch folder: {settings.watch_folder_path}")
        print(f"📁 Temp folder: {settings.temp_folder_path}")
        print(f"📁 Log folder: {settings.log_folder_path}")
    else:
        # Validate but DO NOT exit on import; let the app decide at runtime
        try:
            settings.validate_required_settings()
        except ValueError as e:
            # Surface the error for callers but avoid sys.exit during import
            settings.configuration_error = str(e)
            print(f"❌ Configuration Error (deferred): {e}")
except Exception as _e:
    # Never crash on import
    print(f"⚠️  Settings initialization warning: {_e}")
