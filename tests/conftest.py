"""
Pytest configuration and fixtures
"""

import pytest
import asyncio
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)

@pytest.fixture
def mock_video_file(temp_dir):
    """Create a mock video file"""
    video_path = temp_dir / "test_video.mp4"
    video_path.write_bytes(b"mock video content")
    return video_path

@pytest.fixture
def mock_db_manager():
    """Create a mock database manager"""
    mock_db = AsyncMock()
    mock_db.test_connection = AsyncMock(return_value=True)
    mock_db.execute_query = AsyncMock(return_value=MagicMock(data=[]))
    return mock_db

@pytest.fixture
def mock_analysis_result():
    """Create a mock video analysis result"""
    return {
        "products": [
            {"name": "테스트 제품", "brand": "테스트 브랜드"}
        ],
        "category": "technology",
        "keywords": ["test", "demo", "sample"],
        "content_type": "review",
        "confidence_score": 0.85,
        "summary": "테스트 영상 분석 결과"
    }

@pytest.fixture
def mock_seo_content():
    """Create mock SEO content"""
    return {
        "title": "테스트 제품 리뷰 | 2025년 최신",
        "description": "테스트 제품에 대한 상세 리뷰입니다.",
        "tags": ["테스트", "제품", "리뷰"],
        "thumbnail": None
    }

@pytest.fixture
def mock_channel_info():
    """Create mock channel information"""
    return {
        "channel_id": "test_channel_001",
        "channel_name": "테스트 채널",
        "uploads_today": 0,
        "category_match": 0.8,
        "reason": "카테고리 매칭"
    }

@pytest.fixture
def mock_product_matches():
    """Create mock product matches"""
    return [
        {
            "product_name": "테스트 제품",
            "coupang_url": "https://link.coupang.com/test",
            "image_url": "https://example.com/image.jpg",
            "price": "₩50,000",
            "confidence": 0.9
        }
    ]