"""
Test Configuration File
Contains all test environment settings and configurations
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load test environment variables
TEST_ENV_PATH = Path(__file__).parent.parent / '.env.test'
load_dotenv(TEST_ENV_PATH)

class TestConfig:
    """Test environment configuration"""
    
    # Test Database Configuration
    TEST_SUPABASE_URL = os.getenv('TEST_SUPABASE_URL', 'https://test.supabase.co')
    TEST_SUPABASE_ANON_KEY = os.getenv('TEST_SUPABASE_ANON_KEY', 'test_anon_key')
    TEST_SUPABASE_SERVICE_KEY = os.getenv('TEST_SUPABASE_SERVICE_KEY', 'test_service_key')
    
    # Test API Keys (Mock by default)
    TEST_GEMINI_API_KEY = os.getenv('TEST_GEMINI_API_KEY', 'mock_gemini_key')
    TEST_GOOGLE_API_KEY = os.getenv('TEST_GOOGLE_API_KEY', 'mock_google_key')
    
    # Test Paths
    TEST_BASE_DIR = Path(__file__).parent.parent
    TEST_VIDEO_DIR = TEST_BASE_DIR / 'fixtures' / 'sample_videos'
    TEST_TEMP_DIR = TEST_BASE_DIR / 'temp'
    TEST_REPORTS_DIR = TEST_BASE_DIR / 'reports'
    
    # Test Settings
    TEST_MAX_DAILY_UPLOADS = 3
    TEST_MAX_FILE_SIZE_MB = 150
    TEST_MIN_FILE_SIZE_MB = 10
    TEST_BATCH_SIZE = 5
    
    # Performance Test Settings
    LOAD_TEST_USERS = 10
    LOAD_TEST_DURATION = 60  # seconds
    MAX_RESPONSE_TIME = 200  # milliseconds
    
    # Test Data Settings
    SAMPLE_CHANNELS_COUNT = 5
    SAMPLE_VIDEOS_COUNT = 10
    
    # Mock Service Settings
    USE_MOCK_GEMINI = True
    USE_MOCK_GOOGLE = True
    USE_MOCK_COUPANG = True
    
    # Timeout Settings
    API_TIMEOUT = 30  # seconds
    DB_TIMEOUT = 10  # seconds
    
    @classmethod
    def setup_test_environment(cls):
        """Create necessary test directories"""
        cls.TEST_VIDEO_DIR.mkdir(parents=True, exist_ok=True)
        cls.TEST_TEMP_DIR.mkdir(parents=True, exist_ok=True)
        cls.TEST_REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        (cls.TEST_REPORTS_DIR / 'coverage').mkdir(exist_ok=True)
        (cls.TEST_REPORTS_DIR / 'performance').mkdir(exist_ok=True)
    
    @classmethod
    def cleanup_test_environment(cls):
        """Clean up test files and directories"""
        import shutil
        if cls.TEST_TEMP_DIR.exists():
            shutil.rmtree(cls.TEST_TEMP_DIR)
        cls.TEST_TEMP_DIR.mkdir(parents=True, exist_ok=True)