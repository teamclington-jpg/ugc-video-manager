#!/usr/bin/env python3
"""
UGC Video Manager - Main Application Entry Point
"""

import asyncio
import signal
import sys
from pathlib import Path
from typing import Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.config import settings
from src.api.main import create_app, start_server
from src.watchers.video_watcher import VideoWatcher
from src.utils.logger import setup_logger

# Setup logger
logger = setup_logger("main")

class UGCVideoManager:
    """Main application controller"""
    
    def __init__(self):
        self.video_watcher: Optional[VideoWatcher] = None
        self.shutdown_event = asyncio.Event()
        
    async def start_video_watcher(self):
        """Start the video folder watcher"""
        logger.info(f"Starting video watcher on: {settings.watch_folder_path}")
        
        from src.watchers.enhanced_video_watcher import EnhancedVideoWatcher
        self.video_watcher = EnhancedVideoWatcher(str(settings.watch_folder_path))
        
        # Start watching in background
        await self.video_watcher.start()
        
    async def start_services(self):
        """Start all background services"""
        try:
            # Start video watcher
            await self.start_video_watcher()
            logger.info("✅ Video watcher started")
            
            # Start video processor
            from src.processors.video_processor import get_video_processor
            self.video_processor = get_video_processor()
            
            # Start queue processor
            asyncio.create_task(self.video_processor.process_queue())
            logger.info("✅ Queue processor started")
            
            # Start maintenance tasks
            asyncio.create_task(self._run_maintenance())
            logger.info("✅ Maintenance tasks started")
            
        except Exception as e:
            logger.error(f"Failed to start services: {e}")
            raise
    
    async def _run_maintenance(self):
        """Run periodic maintenance tasks"""
        while not self.shutdown_event.is_set():
            try:
                await asyncio.sleep(3600)  # Every hour
                
                # Reprocess failed entries
                from src.processors.video_processor import get_video_processor
                processor = get_video_processor()
                await processor.reprocess_failed()
                
            except Exception as e:
                logger.error(f"Maintenance error: {e}")
    
    async def shutdown(self):
        """Gracefully shutdown all services"""
        logger.info("Shutting down services...")
        
        if self.video_watcher:
            await self.video_watcher.stop()
        
        self.shutdown_event.set()
        logger.info("All services stopped")
    
    def handle_signal(self, sig, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {sig}")
        asyncio.create_task(self.shutdown())

async def main():
    """Main application entry point"""
    
    # Print startup banner
    print("""
    ╔═══════════════════════════════════════╗
    ║      UGC Video Manager v1.0.0        ║
    ║   Automated Video Processing System   ║
    ╚═══════════════════════════════════════╝
    """)
    
    # Validate configuration
    if not settings.debug_mode:
        try:
            settings.validate_required_settings()
        except ValueError as e:
            logger.error(f"Configuration error: {e}")
            sys.exit(1)
    
    # Create application instance
    app_manager = UGCVideoManager()
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, app_manager.handle_signal)
    signal.signal(signal.SIGTERM, app_manager.handle_signal)
    
    # Start background services
    logger.info("Starting background services...")
    await app_manager.start_services()
    
    # Start API server
    logger.info(f"Starting API server on {settings.api_host}:{settings.api_port}")
    app = create_app()
    
    # Run server and services concurrently
    server_task = asyncio.create_task(
        start_server(app, settings.api_host, settings.api_port)
    )
    shutdown_task = asyncio.create_task(app_manager.shutdown_event.wait())
    
    # Wait for shutdown
    await asyncio.gather(server_task, shutdown_task)
    
    logger.info("Application shutdown complete")

def run_cli():
    """Run in CLI mode for testing"""
    import argparse
    
    parser = argparse.ArgumentParser(description="UGC Video Manager")
    parser.add_argument(
        "--mode", 
        choices=["server", "watcher", "test"],
        default="server",
        help="Run mode"
    )
    parser.add_argument(
        "--watch-folder",
        help="Override watch folder path"
    )
    
    args = parser.parse_args()
    
    if args.watch_folder:
        settings.watch_folder_path = Path(args.watch_folder)
    
    if args.mode == "server":
        # Run full application
        asyncio.run(main())
    elif args.mode == "watcher":
        # Run only video watcher for testing
        async def run_watcher():
            watcher = VideoWatcher(str(settings.watch_folder_path))
            await watcher.start()
            # Keep running
            await asyncio.Event().wait()
        
        asyncio.run(run_watcher())
    elif args.mode == "test":
        # Run test mode
        print("Test mode - checking configuration...")
        print(f"✅ Watch folder: {settings.watch_folder_path}")
        print(f"✅ Supabase URL: {settings.supabase_url[:30]}...")
        print(f"✅ API Keys configured: {bool(settings.gemini_api_key)}")

if __name__ == "__main__":
    print("Starting UGC Video Manager...")
    try:
        # Check if running with arguments
        if len(sys.argv) > 1:
            run_cli()
        else:
            # Default: run server
            print("Starting in server mode...")
            asyncio.run(main())
    except KeyboardInterrupt:
        print("\nApplication stopped by user")
        logger.info("Application stopped by user")
    except Exception as e:
        print(f"Application error: {e}")
        import traceback
        traceback.print_exc()
        logger.error(f"Application error: {e}")
        sys.exit(1)