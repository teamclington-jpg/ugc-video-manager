"""
Enhanced Video Watcher Module
Monitors subdirectories with date patterns for new video files
"""

import asyncio
import hashlib
import re
from pathlib import Path
from typing import Set, Optional, Callable, Dict, List
from datetime import datetime, timedelta
import os

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent, FileModifiedEvent, DirCreatedEvent

from src.config import settings
from src.utils.logger import get_logger
from src.utils.database import get_db_manager

logger = get_logger("enhanced_video_watcher")

class EnhancedVideoFileHandler(FileSystemEventHandler):
    """Enhanced handler for video file events in subdirectories"""
    
    def __init__(self, watcher: 'EnhancedVideoWatcher'):
        self.watcher = watcher
        self.processing_files: Set[str] = set()
        # Pattern to match folders like "채널명_날짜" (e.g., "주부채널_0828")
        self.folder_pattern = re.compile(r'^(.+)_(\d{4}|\d{2}\d{2})$')
        
    def on_created(self, event):
        """Handle file/directory creation event"""
        if event.is_directory:
            self._handle_new_directory(event.src_path)
        else:
            self._handle_video_file(event.src_path, "created")
    
    def on_modified(self, event):
        """Handle file modification event"""
        if not event.is_directory:
            self._handle_video_file(event.src_path, "modified")
    
    def _handle_new_directory(self, dir_path: str):
        """Handle newly created directory"""
        dir_name = Path(dir_path).name
        
        # Check if it matches our date pattern
        if self.folder_pattern.match(dir_name):
            logger.info(f"Detected new date folder: {dir_name}")
            # Scan this directory for videos
            asyncio.create_task(self.watcher.scan_directory(dir_path))
    
    def _handle_video_file(self, file_path: str, event_type: str):
        """Process video file if valid and in correct folder structure"""
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
        
        # Check if file is in a date-pattern folder
        parent_folder = path.parent.name
        if not self.folder_pattern.match(parent_folder):
            logger.debug(f"Skipping file not in date folder: {file_path}")
            return
        
        logger.info(f"Detected {event_type} video in {parent_folder}: {path.name}")
        
        # Extract channel info from folder name and prefer top-level folder as channel hint
        match = self.folder_pattern.match(parent_folder)
        if match:
            channel_name = match.group(1)
            date_str = match.group(2)
            # Prefer the top-level channel folder if available (e.g., "2. 자취생 꿀템")
            try:
                top_folder = Path(file_path).parent.parent.name
                if top_folder and top_folder not in ("", "."):
                    channel_name = top_folder
            except Exception:
                pass
            
            # Add to processing queue with metadata
            self.processing_files.add(file_path)
            
            # Schedule processing with channel info
            asyncio.create_task(
                self.watcher.process_video(
                    file_path,
                    channel_name=channel_name,
                    date_str=date_str
                )
            )

class EnhancedVideoWatcher:
    """Enhanced video watcher for hierarchical folder structure"""
    
    def __init__(self, watch_folder: str):
        self.watch_folder = Path(watch_folder)
        self.observers: Dict[str, Observer] = {}  # Multiple observers for subdirectories
        self.handler = EnhancedVideoFileHandler(self)
        self.processed_files: Set[str] = set()
        self.processing_callback: Optional[Callable] = None
        self.is_running = False
        self.channel_folders: Dict[str, Path] = {}  # Map channel names to folders
        
        # Ensure watch folder exists
        if not self.watch_folder.exists():
            logger.warning(f"Watch folder does not exist: {self.watch_folder}")
            self.watch_folder.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Enhanced video watcher initialized for: {self.watch_folder}")
    
    async def start(self):
        """Start watching the folder and all subdirectories"""
        if self.is_running:
            logger.warning("Watcher is already running")
            return
        
        self.is_running = True
        
        # Scan for existing channel folders
        await self._discover_channel_folders()
        
        # Start observers for main folder and all subdirectories
        await self._start_observers()
        
        logger.info(f"Started watching: {self.watch_folder} and subdirectories")
        
        # Process existing files in date folders
        await self._process_existing_files()
    
    async def _discover_channel_folders(self):
        """Discover channel folders in the watch directory"""
        try:
            for item in self.watch_folder.iterdir():
                if item.is_dir() and not item.name.startswith('.'):
                    # This could be a channel folder
                    self.channel_folders[item.name] = item
                    logger.info(f"Discovered channel folder: {item.name}")
                    # In debug mode, auto-create a basic channel record if none exists
                    if settings.debug_mode:
                        try:
                            from src.utils.database import get_db_manager
                            db = get_db_manager()
                            existing = await db.get_available_channels()
                            if not any(c.get('channel_name') == item.name for c in existing):
                                await db.create_channel({
                                    'channel_name': item.name,
                                    'channel_url': f'https://youtube.com/@{item.name}',
                                    'channel_type': 'main',
                                    'parent_channel_id': None,
                                    'category': 'lifestyle',
                                    'description': 'Auto-created in debug mode from folder discovery',
                                    'account_id': 'debug',
                                    'account_password': 'debug',
                                    'max_daily_uploads': settings.max_daily_uploads_per_channel,
                                    'is_active': True,
                                })
                                logger.info(f"Auto-created channel in memory: {item.name}")
                        except Exception as e:
                            logger.warning(f"Channel auto-create skipped: {e}")
        except Exception as e:
            logger.error(f"Error discovering channel folders: {e}")
    
    async def _start_observers(self):
        """Start observers for all directories"""
        try:
            # Main observer for root directory
            main_observer = Observer()
            main_observer.schedule(
                self.handler, 
                str(self.watch_folder), 
                recursive=True  # Watch all subdirectories
            )
            main_observer.start()
            self.observers['main'] = main_observer
            
            logger.info(f"Started observer for main folder and all subdirectories")
            
        except Exception as e:
            logger.error(f"Error starting observers: {e}")
    
    async def stop(self):
        """Stop all observers"""
        if self.is_running:
            for name, observer in self.observers.items():
                observer.stop()
                observer.join()
                logger.info(f"Stopped observer: {name}")
            
            self.observers.clear()
            self.is_running = False
            logger.info("All observers stopped")
    
    async def _process_existing_files(self):
        """Process existing files in date-pattern folders"""
        try:
            folder_pattern = re.compile(r'^(.+)_(\d{4}|\d{2}\d{2})$')
            
            # Search through all channel folders
            for channel_folder in self.channel_folders.values():
                for date_folder in channel_folder.iterdir():
                    if date_folder.is_dir() and folder_pattern.match(date_folder.name):
                        logger.info(f"Scanning existing date folder: {date_folder}")
                        await self.scan_directory(str(date_folder))
            
        except Exception as e:
            logger.error(f"Error processing existing files: {e}")
    
    async def scan_directory(self, directory_path: str):
        """Scan a directory for video files"""
        try:
            dir_path = Path(directory_path)
            folder_pattern = re.compile(r'^(.+)_(\d{4}|\d{2}\d{2})$')
            
            # Extract channel info from folder name
            folder_name = dir_path.name
            match = folder_pattern.match(folder_name)
            
            if not match:
                logger.debug(f"Folder doesn't match date pattern: {folder_name}")
                return
            
            # Prefer top-level folder name as channel hint when present
            channel_name = match.group(1)
            try:
                top_folder = dir_path.parent.name
                if top_folder and top_folder not in ("", "."):
                    channel_name = top_folder
            except Exception:
                pass
            date_str = match.group(2)
            
            # Scan for video files
            for file_path in dir_path.iterdir():
                if file_path.is_file() and settings.is_valid_video_file(file_path.name):
                    # Check if not already processed
                    file_hash = self._calculate_file_hash(str(file_path))
                    if file_hash not in self.processed_files:
                        logger.info(f"Found video in {folder_name}: {file_path.name}")
                        await self.process_video(
                            str(file_path),
                            channel_name=channel_name,
                            date_str=date_str
                        )
                        
        except Exception as e:
            logger.error(f"Error scanning directory {directory_path}: {e}")
    
    async def process_video(
        self, 
        file_path: str,
        channel_name: Optional[str] = None,
        date_str: Optional[str] = None
    ):
        """Process a detected video file with metadata"""
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
            
            logger.info(
                f"Processing video: {path.name} "
                f"({file_size_mb:.1f} MB) "
                f"[Channel: {channel_name}, Date: {date_str}]"
            )
            
            # Create queue entry with metadata
            await self._create_queue_entry(
                path, 
                file_size_mb, 
                file_hash,
                channel_name=channel_name,
                date_str=date_str
            )
            
            # Mark as processed
            self.processed_files.add(file_hash)
            
            # Remove from processing queue
            if file_path in self.handler.processing_files:
                self.handler.processing_files.remove(file_path)
            
            # Call custom callback if set
            if self.processing_callback:
                await self.processing_callback(file_path, channel_name, date_str)
            
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
    
    async def _create_queue_entry(
        self, 
        file_path: Path, 
        file_size_mb: float, 
        file_hash: str,
        channel_name: Optional[str] = None,
        date_str: Optional[str] = None
    ):
        """Create an entry in the upload queue with metadata"""
        try:
            # Trigger the full processing pipeline instead of just adding to queue
            from src.processors.video_processor import get_video_processor
            processor = get_video_processor()
            
            logger.info(f"Processing video through pipeline: {file_path.name}")

            # Process video through complete pipeline, honoring folder channel hint if available
            result = await processor.process_video(str(file_path), channel_hint=channel_name)
            
            if result.get("success"):
                logger.info(f"Successfully processed: {file_path.name} (Queue ID: {result.get('queue_id')})")
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
            "channel_folders": len(self.channel_folders),
            "observers": len(self.observers),
            "processed_files": len(self.processed_files),
            "currently_processing": len(self.handler.processing_files) if self.handler else 0
        }
    
    def get_recent_folders(self, days: int = 7) -> List[Path]:
        """Get folders created in the last N days"""
        recent_folders = []
        folder_pattern = re.compile(r'^(.+)_(\d{4}|\d{2}\d{2})$')
        cutoff_time = datetime.now() - timedelta(days=days)
        
        try:
            for channel_folder in self.channel_folders.values():
                for date_folder in channel_folder.iterdir():
                    if date_folder.is_dir() and folder_pattern.match(date_folder.name):
                        # Check folder creation time
                        folder_stat = date_folder.stat()
                        folder_mtime = datetime.fromtimestamp(folder_stat.st_mtime)
                        
                        if folder_mtime > cutoff_time:
                            recent_folders.append(date_folder)
            
        except Exception as e:
            logger.error(f"Error getting recent folders: {e}")
        
        return recent_folders

# Standalone function for testing
async def watch_folder_enhanced(folder_path: str):
    """Run enhanced video watcher as standalone service"""
    watcher = EnhancedVideoWatcher(folder_path)
    
    try:
        await watcher.start()
        logger.info("Enhanced video watcher is running. Press Ctrl+C to stop.")
        
        # Keep running and show stats
        while True:
            await asyncio.sleep(30)
            stats = watcher.get_stats()
            logger.info(f"Watcher stats: {stats}")
            
            # Check recent folders
            recent = watcher.get_recent_folders(days=1)
            if recent:
                logger.info(f"Recent folders (last 24h): {[f.name for f in recent]}")
            
    except KeyboardInterrupt:
        logger.info("Stopping enhanced video watcher...")
        await watcher.stop()

if __name__ == "__main__":
    # Test the enhanced watcher
    import sys
    
    if len(sys.argv) > 1:
        watch_path = sys.argv[1]
    else:
        watch_path = "/Users/thecity17/Desktop/teamclingotondrive/상품쇼츠DB"
    
    asyncio.run(watch_folder_enhanced(watch_path))
