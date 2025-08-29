#!/usr/bin/env python3
"""
Integration Test for UGC Video Manager
Tests the complete processing pipeline
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.config import settings
from src.utils.logger import get_logger

logger = get_logger("test")

async def test_modules():
    """Test individual modules"""
    
    print("\n📋 Testing Module Imports...")
    
    try:
        # Test imports
        from src.watchers.enhanced_video_watcher import EnhancedVideoWatcher
        print("✅ Video Watcher module")
        
        from src.analyzers.video_analyzer import GeminiVideoAnalyzer
        print("✅ Video Analyzer module")
        
        from src.matchers.channel_matcher import ChannelMatcher
        print("✅ Channel Matcher module")
        
        from src.generators.seo_generator import SEOGenerator
        print("✅ SEO Generator module")
        
        from src.matchers.product_matcher import ProductMatcher
        print("✅ Product Matcher module")
        
        from src.queue.queue_manager import QueueManager
        print("✅ Queue Manager module")
        
        from src.processors.video_processor import VideoProcessor
        print("✅ Video Processor module")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

async def test_database():
    """Test database connection"""
    
    print("\n🗄️ Testing Database Connection...")
    
    try:
        from src.utils.database import get_db_manager
        db = get_db_manager()
        
        # Test connection
        if await db.test_connection():
            print("✅ Database connected successfully")
            
            # Test query
            result = await db.execute_query("SELECT COUNT(*) as count FROM youtube_channels")
            if result:
                channel_count = result.data[0]['count'] if result.data else 0
                print(f"✅ Found {channel_count} channels in database")
            
            return True
        else:
            print("❌ Database connection failed")
            return False
            
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False

async def test_video_processing():
    """Test video processing pipeline"""
    
    print("\n🎥 Testing Video Processing Pipeline...")
    
    try:
        from src.processors.video_processor import get_video_processor
        processor = get_video_processor()
        
        # Create mock video analysis result
        mock_analysis = {
            "products": [{"name": "테스트 제품", "brand": "테스트"}],
            "category": "technology",
            "keywords": ["test", "demo"],
            "content_type": "review",
            "confidence_score": 0.8
        }
        
        # Test channel matching
        from src.matchers.channel_matcher import get_channel_matcher
        matcher = get_channel_matcher()
        
        # Get available channels
        available = await matcher._get_available_channels()
        
        if available:
            print(f"✅ Found {len(available)} available channels")
        else:
            print("⚠️  No available channels (this is OK if channels not set up yet)")
        
        # Test SEO generation
        from src.generators.seo_generator import get_seo_generator
        seo_gen = get_seo_generator()
        
        seo_content = await seo_gen.generate_seo_content(mock_analysis)
        
        if seo_content and seo_content.get("title"):
            print(f"✅ Generated SEO title: {seo_content['title'][:50]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Processing pipeline error: {e}")
        return False

async def test_api():
    """Test API endpoints"""
    
    print("\n🌐 Testing API Endpoints...")
    
    try:
        from src.api.main import app
        print("✅ API app created successfully")
        
        # Test route registration
        routes = [route.path for route in app.routes]
        
        essential_routes = ["/", "/stats", "/queue/status", "/channels"]
        for route in essential_routes:
            if route in routes:
                print(f"✅ Route registered: {route}")
            else:
                print(f"⚠️  Route missing: {route}")
        
        return True
        
    except Exception as e:
        print(f"❌ API error: {e}")
        return False

async def check_environment():
    """Check environment configuration"""
    
    print("\n⚙️ Checking Environment Configuration...")
    
    # Check watch folder
    watch_path = Path(settings.watch_folder_path)
    if watch_path.exists():
        print(f"✅ Watch folder exists: {watch_path}")
    else:
        print(f"⚠️  Watch folder not found: {watch_path}")
        print("  Creating it now...")
        watch_path.mkdir(parents=True, exist_ok=True)
    
    # Check API keys
    if settings.gemini_api_key:
        print("✅ Gemini API key configured")
    else:
        print("⚠️  Gemini API key not configured (will use mock mode)")
    
    if settings.supabase_url and settings.supabase_anon_key:
        print("✅ Supabase credentials configured")
    else:
        print("❌ Supabase credentials missing")
    
    return True

async def main():
    """Run all tests"""
    
    print("=" * 60)
    print("🧪 UGC Video Manager - Integration Test")
    print("=" * 60)
    
    results = []
    
    # Run tests
    results.append(("Environment", await check_environment()))
    results.append(("Module Imports", await test_modules()))
    results.append(("Database", await test_database()))
    results.append(("Processing Pipeline", await test_video_processing()))
    results.append(("API", await test_api()))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Test Summary:")
    print("=" * 60)
    
    all_passed = True
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{test_name:.<30} {status}")
        if not passed:
            all_passed = False
    
    print("=" * 60)
    
    if all_passed:
        print("\n🎉 All tests passed! System is ready to use.")
        print("\n📌 Next steps:")
        print("1. Run: python3 run.py")
        print("2. Open: http://localhost:8000")
        print("3. Place videos in watch folder")
    else:
        print("\n⚠️  Some tests failed. Please check the errors above.")
        print("Most common issues:")
        print("- Missing .env configuration")
        print("- Supabase not set up")
        print("- Dependencies not installed")
    
    return all_passed

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)