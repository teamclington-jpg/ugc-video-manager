"""
Configuration settings for UGC Video Manager
"""

import os
from pathlib import Path
from typing import List, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Settings:
    """Application settings"""
    
    def __init__(self):
        # Application
        self.app_name = "UGC Video Manager"
        self.app_version = "1.0.0"
        self.debug_mode = os.getenv("DEBUG_MODE", "false").lower() == "true"
        
        # API Server
        self.api_host = os.getenv("API_HOST", "0.0.0.0")
        self.api_port = int(os.getenv("API_PORT", "8000"))
        self.cors_origins = os.getenv("CORS_ORIGINS", "*").split(",")
        
        # Database
        self.supabase_url = os.getenv("SUPABASE_URL", "")
        self.supabase_anon_key = os.getenv("SUPABASE_ANON_KEY", "")
        self.supabase_service_key = os.getenv("SUPABASE_SERVICE_KEY", "")
        
        # API Keys
        self.gemini_api_key = os.getenv("GEMINI_API_KEY", "")
        self.google_api_key = os.getenv("GOOGLE_CUSTOM_SEARCH_API_KEY", "")
        self.google_search_engine_id = os.getenv("GOOGLE_SEARCH_ENGINE_ID", "")
        
        # Paths
        self.watch_folder_path = os.getenv(
            "WATCH_FOLDER_PATH",
            "/Users/thecity17/Desktop/teamclingotondrive/상품쇼츠DB/3. 주부채널"
        )
        self.temp_folder_path = os.getenv("TEMP_FOLDER_PATH", "/tmp/ugc_temp")
        self.log_folder_path = os.getenv("LOG_FOLDER_PATH", "./logs")
        
        # Video Settings
        self.max_file_size_mb = int(os.getenv("MAX_FILE_SIZE_MB", "150"))
        self.min_file_size_mb = int(os.getenv("MIN_FILE_SIZE_MB", "10"))
        self.supported_formats = os.getenv(
            "SUPPORTED_VIDEO_FORMATS", 
            ".mp4,.mov,.avi,.mkv,.webm"
        ).split(",")
        
        # Upload Limits
        self.max_daily_uploads_per_channel = int(
            os.getenv("MAX_DAILY_UPLOADS_PER_CHANNEL", "3")
        )
        self.upload_time_window_hours = int(
            os.getenv("UPLOAD_TIME_WINDOW_HOURS", "24")
        )
        
        # Processing
        self.batch_size = int(os.getenv("BATCH_SIZE", "5"))
        self.processing_interval_seconds = int(
            os.getenv("PROCESSING_INTERVAL_SECONDS", "60")
        )
        
        # Cache
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        self.cache_enabled = os.getenv("CACHE_ENABLED", "false").lower() == "true"
        self.cache_ttl_seconds = int(os.getenv("CACHE_TTL_SECONDS", "3600"))
        
        # Ensure paths exist
        self._ensure_paths()
    
    def _ensure_paths(self):
        """Ensure required paths exist"""
        for path_attr in ["temp_folder_path", "log_folder_path"]:
            path = getattr(self, path_attr)
            if path:
                Path(path).mkdir(parents=True, exist_ok=True)
    
    def get_watch_folders(self) -> List[Path]:
        """Get list of folders to watch"""
        base_path = Path(self.watch_folder_path)
        if not base_path.exists():
            return []
        
        # Look for folders matching pattern: 채널명_날짜
        watch_folders = []
        if base_path.is_dir():
            # Get all subdirectories
            for folder in base_path.iterdir():
                if folder.is_dir() and "_" in folder.name:
                    watch_folders.append(folder)
        
        return watch_folders
    
    def is_valid_video_file(self, file_path: Path) -> bool:
        """Check if file is a valid video file"""
        # Check extension
        if file_path.suffix.lower() not in self.supported_formats:
            return False
        
        # Check file size
        file_size_mb = file_path.stat().st_size / (1024 * 1024)
        if file_size_mb < self.min_file_size_mb or file_size_mb > self.max_file_size_mb:
            return False
        
        return True

# Create global settings instance
settings = Settings()