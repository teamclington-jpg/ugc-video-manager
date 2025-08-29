"""
Main Application Module
Coordinates all components of the UGC Video Manager
"""

import asyncio
import signal
import sys
from pathlib import Path
from typing import Optional

from src.config import settings
from src.utils.logger import get_logger
from src.watchers.enhanced_video_watcher import EnhancedVideoWatcher
from src.processors.video_processor import get_video_processor
from src.utils.database import get_db_manager

logger = get_logger("main_app")

class UGCVideoManager:
    """Main application class for UGC Video Manager"""
    
    def __init__(self):
        """Initialize the application"""
        self.video_processor = get_video_processor()
        self.video_watcher = None
        self.db_manager = get_db_manager()
        self.running = False
        self.tasks = []
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        logger.info("UGC Video Manager initialized")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, shutting down...")
        self.stop()
        sys.exit(0)
    
    async def initialize(self):
        """Initialize all components"""
        try:
            logger.info("Initializing components...")
            
            # Test database connection
            if not await self.db_manager.test_connection():
                logger.error("Database connection failed")
                return False
            
            # Initialize video watcher
            watch_path = Path(settings.watch_folder_path)
            if not watch_path.exists():
                logger.error(f"Watch folder does not exist: {watch_path}")
                logger.info(f"Creating watch folder: {watch_path}")
                watch_path.mkdir(parents=True, exist_ok=True)
            
            self.video_watcher = EnhancedVideoWatcher(str(watch_path))
            
            # Set up video processing callback
            async def process_new_video(video_path: str):
                """Callback for new video detection"""
                logger.info(f"New video detected: {video_path}")
                await self.video_processor.process_video(video_path)
            
            self.video_watcher.on_new_video = process_new_video
            
            logger.info("✅ All components initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error during initialization: {e}")
            return False
    
    async def start(self):
        """Start the application"""
        try:
            logger.info("Starting UGC Video Manager...")
            
            # Initialize components
            if not await self.initialize():
                logger.error("Failed to initialize components")
                return
            
            self.running = True
            
            # Start video watcher
            watcher_task = asyncio.create_task(self._run_watcher())
            self.tasks.append(watcher_task)
            
            # Start queue processor
            queue_task = asyncio.create_task(self._run_queue_processor())
            self.tasks.append(queue_task)
            
            # Start maintenance tasks
            maintenance_task = asyncio.create_task(self._run_maintenance())
            self.tasks.append(maintenance_task)
            
            # Start statistics reporting
            stats_task = asyncio.create_task(self._run_statistics())
            self.tasks.append(stats_task)
            
            logger.info("=" * 60)
            logger.info("🚀 UGC Video Manager is running!")
            logger.info(f"📁 Watching: {settings.watch_folder_path}")
            logger.info(f"🌐 API Server: http://localhost:{settings.api_port}")
            logger.info(f"📊 Dashboard: http://localhost:{settings.api_port}")
            logger.info("=" * 60)
            
            # Wait for all tasks
            await asyncio.gather(*self.tasks)
            
        except Exception as e:
            logger.error(f"Error in main application: {e}")
        finally:
            self.stop()
    
    async def _run_watcher(self):
        """Run the video watcher"""
        try:
            if self.video_watcher:
                await self.video_watcher.start()
        except Exception as e:
            logger.error(f"Error in video watcher: {e}")
    
    async def _run_queue_processor(self):
        """Run the queue processor"""
        try:
            await self.video_processor.process_queue()
        except Exception as e:
            logger.error(f"Error in queue processor: {e}")
    
    async def _run_maintenance(self):
        """Run periodic maintenance tasks"""
        while self.running:
            try:
                # Clean old queue entries every 24 hours
                await asyncio.sleep(86400)  # 24 hours
                
                logger.info("Running maintenance tasks...")
                
                # Clean old entries
                cleaned = await self.video_processor.queue_manager.clean_old_entries(30)
                logger.info(f"Cleaned {cleaned} old queue entries")
                
                # Reprocess failed entries
                retried = await self.video_processor.reprocess_failed()
                logger.info(f"Retried {retried} failed entries")
                
            except Exception as e:
                logger.error(f"Error in maintenance tasks: {e}")
                await asyncio.sleep(3600)  # Wait 1 hour on error
    
    async def _run_statistics(self):
        """Report statistics periodically"""
        while self.running:
            try:
                await asyncio.sleep(300)  # Every 5 minutes
                
                stats = await self.video_processor.get_processing_stats()
                
                # Log queue status
                queue_stats = stats.get("queue", {})
                logger.info("📊 Queue Statistics:")
                for status, data in queue_stats.get("by_status", {}).items():
                    logger.info(f"  - {status}: {data.get('count', 0)} videos")
                
                # Log channel utilization
                channel_stats = stats.get("channels", {})
                logger.info(f"📺 Channel Utilization:")
                logger.info(f"  - Total capacity: {channel_stats.get('total_capacity', 0)}")
                logger.info(f"  - Used today: {channel_stats.get('used_capacity', 0)}")
                logger.info(f"  - Available: {channel_stats.get('available_capacity', 0)}")
                
            except Exception as e:
                logger.error(f"Error reporting statistics: {e}")
    
    def stop(self):
        """Stop the application"""
        logger.info("Stopping UGC Video Manager...")
        self.running = False
        
        # Stop video watcher
        if self.video_watcher:
            self.video_watcher.stop()
        
        # Cancel all tasks
        for task in self.tasks:
            if not task.done():
                task.cancel()
        
        logger.info("UGC Video Manager stopped")
    
    async def process_existing_videos(self):
        """Process existing videos in watch folder"""
        try:
            logger.info("Scanning for existing videos...")
            
            watch_path = Path(settings.watch_folder_path)
            if not watch_path.exists():
                logger.warning(f"Watch path does not exist: {watch_path}")
                return
            
            video_count = 0
            
            # Pattern: 채널명_날짜 folders
            for channel_folder in watch_path.iterdir():
                if channel_folder.is_dir() and '_' in channel_folder.name:
                    # Check for video files
                    for video_file in channel_folder.iterdir():
                        if video_file.suffix.lower() in ['.mp4', '.avi', '.mov', '.mkv']:
                            logger.info(f"Found existing video: {video_file}")
                            await self.video_processor.process_video(str(video_file))
                            video_count += 1
                            
                            # Process in batches to avoid overwhelming
                            if video_count % 10 == 0:
                                await asyncio.sleep(5)
            
            logger.info(f"Processed {video_count} existing videos")
            
        except Exception as e:
            logger.error(f"Error processing existing videos: {e}")

async def main():
    """Main entry point"""
    app = UGCVideoManager()
    
    # Process existing videos first
    await app.process_existing_videos()
    
    # Start the main application
    await app.start()

if __name__ == "__main__":
    asyncio.run(main())