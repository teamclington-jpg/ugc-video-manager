#!/usr/bin/env python3
"""
UGC Video Manager - Minimal working version
"""

import asyncio
import signal
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

print("Starting UGC Video Manager (Minimal Version)...")

async def main():
    """Minimal main application"""
    print("\n" + "="*60)
    print("     UGC Video Manager v1.0.0 - Running")
    print("="*60)
    
    # Load settings
    try:
        from src.config import settings
        print(f"\n✅ Configuration loaded")
        print(f"📁 Watch folder: {settings.watch_folder_path}")
        print(f"🌐 API Port: {settings.api_port}")
    except Exception as e:
        print(f"❌ Failed to load settings: {e}")
        return
    
    # Simple API server
    try:
        from fastapi import FastAPI
        import uvicorn
        
        app = FastAPI(title="UGC Video Manager", version="1.0.0")
        
        @app.get("/")
        async def root():
            return {"message": "UGC Video Manager is running", "version": "1.0.0"}
        
        @app.get("/health")
        async def health():
            return {"status": "healthy"}
        
        # Create server config
        config = uvicorn.Config(
            app=app,
            host=settings.api_host,
            port=settings.api_port,
            log_level="info"
        )
        
        server = uvicorn.Server(config)
        
        print(f"\n🚀 Starting server at http://{settings.api_host}:{settings.api_port}")
        print(f"📊 API docs at http://localhost:{settings.api_port}/docs")
        print("\n종료하려면 Ctrl+C를 누르세요\n")
        
        # Run server
        await server.serve()
        
    except ImportError as e:
        print(f"❌ Missing required package: {e}")
        print("Please run: pip3 install fastapi uvicorn")
    except Exception as e:
        print(f"❌ Server error: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n✅ Application stopped by user")
    except Exception as e:
        print(f"\n❌ Application error: {e}")
        import traceback
        traceback.print_exc()