#!/usr/bin/env python3
"""
Test script to debug startup issues
"""

import sys
import os

print("Python version:", sys.version)
print("Current directory:", os.getcwd())
print("Python path:", sys.path[:3])

# Test imports one by one
try:
    print("\n1. Testing basic imports...")
    import asyncio
    print("✅ asyncio imported")
    
    import signal
    print("✅ signal imported")
    
    from pathlib import Path
    print("✅ Path imported")
    
    print("\n2. Testing project imports...")
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    from src.config import settings
    print("✅ settings imported")
    print(f"   - Debug mode: {settings.debug_mode}")
    print(f"   - API port: {settings.api_port}")
    
    print("\n3. Testing API imports...")
    from src.api.main import create_app, start_server
    print("✅ API imports successful")
    
    print("\n4. Testing video watcher imports...")
    from src.watchers.video_watcher import VideoWatcher
    print("✅ VideoWatcher imported")
    
    print("\n5. Testing logger...")
    from src.utils.logger import setup_logger
    logger = setup_logger("test")
    print("✅ Logger setup successful")
    
    print("\n6. Running minimal async test...")
    async def test_async():
        print("   Async function running...")
        await asyncio.sleep(0.1)
        print("   Async function completed")
        return True
    
    result = asyncio.run(test_async())
    print(f"✅ Async test result: {result}")
    
    print("\n✅ ALL TESTS PASSED!")
    print("\nNow testing main function...")
    
    # Import main function
    from main import main
    print("✅ Main function imported")
    
    # Try to run main
    print("\nAttempting to run main()...")
    asyncio.run(main())
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    import traceback
    traceback.print_exc()
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()