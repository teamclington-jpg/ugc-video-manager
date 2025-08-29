"""
Video Watcher Module
Monitors a folder for new video files and triggers processing
"""

import asyncio
import hashlib
from pathlib import Path
from typing import Set, Optional, Callable
from datetime import datetime
import os

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent, FileModifiedEvent

from src.config import settings
from src.utils.logger import get_logger
from src.utils.database import get_db_manager

logger = get_logger("video_watcher")

class VideoFileHandler(FileSystemEventHandler):
    """Handler for video file events"""
    
    def __init__(self, watcher: 'VideoWatcher'):
        self.watcher = watcher
        self.processing_files: Set[str] = set()
        
    def on_created(self, event):
        """Handle file creation event"""
        if not event.is_directory:
            self._handle_video_file(event.src_path, "created")
    
    def on_modified(self, event):
        """Handle file modification event"""
        if not event.is_directory:
            # Check if file size has stabilized (finished copying)
            self._handle_video_file(event.src_path, "modified")
    
    def _handle_video_file(self, file_path: str, event_type: str):
        """Process video file if valid"""
        path = Path(file_path)
        
        # Check if it's a video file
        if not settings.is_valid_video_file(path.name):
            return
        
        # Skip if already processing
        if file_path in self.processing_files:
            return
        
        # Skip temporary or hidden files
        if path.name.startswith('.') or path.name.startswith('~'):
            return
        
        logger.info(f"Detected {event_type} video file: {path.name}")
        
        # Add to processing queue
        self.processing_files.add(file_path)
        
        # Schedule processing
        asyncio.create_task(self.watcher.process_video(file_path))

class VideoWatcher:
    """Main video watcher class"""
    
    def __init__(self, watch_folder: str):
        self.watch_folder = Path(watch_folder)
        self.observer: Optional[Observer] = None
        self.handler = VideoFileHandler(self)
        self.processed_files: Set[str] = set()
        self.processing_callback: Optional[Callable] = None
        self.is_running = False
        
        # Ensure watch folder exists
        self.watch_folder.mkdir(parents=True, exist_ok=True)
        logger.info(f"Video watcher initialized for: {self.watch_folder}")
    
    async def start(self):
        """Start watching the folder"""
        if self.is_running:
            logger.warning("Watcher is already running")
            return
        
        self.observer = Observer()
        self.observer.schedule(self.handler, str(self.watch_folder), recursive=False)
        self.observer.start()
        self.is_running = True
        
        logger.info(f"Started watching: {self.watch_folder}")
        
        # Process existing files
        await self._process_existing_files()
    
    async def stop(self):
        """Stop watching the folder"""
        if self.observer and self.is_running:
            self.observer.stop()
            self.observer.join()
            self.is_running = False
            logger.info("Stopped watching folder")
    
    async def _process_existing_files(self):
        """Process files already in the watch folder"""
        try:
            for file_path in self.watch_folder.iterdir():
                if file_path.is_file() and settings.is_valid_video_file(file_path.name):
                    # Check if not already processed
                    if str(file_path) not in self.processed_files:
                        logger.info(f"Found existing video: {file_path.name}")
                        await self.process_video(str(file_path))
        except Exception as e:
            logger.error(f"Error processing existing files: {e}")
    
    async def process_video(self, file_path: str):
        """Process a detected video file"""
        try:
            path = Path(file_path)
            
            # Check file size
            file_size_mb = path.stat().st_size / (1024 * 1024)
            
            if file_size_mb < settings.min_file_size_mb:
                logger.warning(f"File too small ({file_size_mb:.1f} MB): {path.name}")
                return
            
            if file_size_mb > settings.max_file_size_mb:
                logger.warning(f"File too large ({file_size_mb:.1f} MB): {path.name}")
                return
            
            # Wait for file to be fully written
            await self._wait_for_file_ready(path)
            
            # Calculate file hash
            file_hash = self._calculate_file_hash(str(path))
            
            # Check if already processed
            if file_hash in self.processed_files:
                logger.info(f"File already processed: {path.name}")
                return
            
            logger.info(f"Processing video: {path.name} ({file_size_mb:.1f} MB)")
            
            # Create queue entry
            await self._create_queue_entry(path, file_size_mb, file_hash)
            
            # Mark as processed
            self.processed_files.add(file_hash)
            
            # Remove from processing queue
            if file_path in self.handler.processing_files:
                self.handler.processing_files.remove(file_path)
            
            # Call custom callback if set
            if self.processing_callback:
                await self.processing_callback(file_path)
            
        except Exception as e:
            logger.error(f"Error processing video {file_path}: {e}")
            # Remove from processing queue on error
            if file_path in self.handler.processing_files:
                self.handler.processing_files.remove(file_path)
    
    async def _wait_for_file_ready(self, file_path: Path, timeout: int = 30):
        """Wait for file to be fully written"""
        last_size = -1
        stable_count = 0
        check_interval = 0.5
        max_checks = int(timeout / check_interval)
        
        for _ in range(max_checks):
            try:
                current_size = file_path.stat().st_size
                
                if current_size == last_size:
                    stable_count += 1
                    if stable_count >= 3:  # File stable for 1.5 seconds
                        return
                else:
                    stable_count = 0
                
                last_size = current_size
                await asyncio.sleep(check_interval)
                
            except OSError:
                # File might be locked, wait and retry
                await asyncio.sleep(check_interval)
        
        logger.warning(f"File not stable after {timeout} seconds: {file_path.name}")
    
    def _calculate_file_hash(self, file_path: str) -> str:
        """Calculate SHA256 hash of file"""
        sha256_hash = hashlib.sha256()
        
        with open(file_path, "rb") as f:
            # Read in chunks for large files
            for byte_block in iter(lambda: f.read(65536), b""):
                sha256_hash.update(byte_block)
        
        return sha256_hash.hexdigest()
    
    async def _create_queue_entry(self, file_path: Path, file_size_mb: float, file_hash: str):
        """Process video through the full pipeline (legacy watcher)."""
        try:
            # Reuse the main processing pipeline for consistency with Enhanced watcher
            from src.processors.video_processor import get_video_processor
            processor = get_video_processor()
            logger.info(f"Processing video through pipeline: {file_path.name}")
            result = await processor.process_video(str(file_path))
            if result.get("success"):
                logger.info(
                    f"Successfully processed: {file_path.name} (Queue ID: {result.get('queue_id')})"
                )
            else:
                errors = result.get("errors", [])
                logger.error(f"Failed to process {file_path.name}: {', '.join(errors)}")
        except Exception as e:
            logger.error(f"Error processing video: {e}")
    
    def set_processing_callback(self, callback: Callable):
        """Set a custom callback for when a video is processed"""
        self.processing_callback = callback
    
    def get_stats(self) -> dict:
        """Get watcher statistics"""
        return {
            "watch_folder": str(self.watch_folder),
            "is_running": self.is_running,
            "processed_files": len(self.processed_files),
            "currently_processing": len(self.handler.processing_files) if self.handler else 0
        }

# Standalone function for testing
async def watch_folder_standalone(folder_path: str):
    """Run video watcher as standalone service"""
    watcher = VideoWatcher(folder_path)
    
    try:
        await watcher.start()
        logger.info("Video watcher is running. Press Ctrl+C to stop.")
        
        # Keep running
        while True:
            await asyncio.sleep(10)
            stats = watcher.get_stats()
            logger.debug(f"Watcher stats: {stats}")
            
    except KeyboardInterrupt:
        logger.info("Stopping video watcher...")
        await watcher.stop()

if __name__ == "__main__":
    # Test the watcher
    import sys
    
    if len(sys.argv) > 1:
        watch_path = sys.argv[1]
    else:
        watch_path = "./watch_folder"
    
    asyncio.run(watch_folder_standalone(watch_path))
