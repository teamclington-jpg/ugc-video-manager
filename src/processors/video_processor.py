"""
Video Processor Module
Orchestrates the complete video processing pipeline
"""

import asyncio
from pathlib import Path
from typing import Dict, Optional, Any
import hashlib

from src.config import settings
from src.utils.logger import get_logger
from src.utils.database import get_db_manager
from src.analyzers.video_analyzer import get_video_analyzer
from src.matchers.channel_matcher import get_channel_matcher
from src.matchers.product_matcher import get_product_matcher
from src.generators.seo_generator import get_seo_generator
from src.queue.queue_manager import get_queue_manager

logger = get_logger("video_processor")

class VideoProcessor:
    """Orchestrates the complete video processing pipeline"""
    
    def __init__(self):
        """Initialize Video Processor"""
        self.db = get_db_manager()
        self.video_analyzer = get_video_analyzer()
        self.channel_matcher = get_channel_matcher()
        self.product_matcher = get_product_matcher()
        self.seo_generator = get_seo_generator()
        self.queue_manager = get_queue_manager()
        self.processing_cache = set()  # Prevent duplicate processing
        logger.info("Video Processor initialized")
    
    async def process_video(self, video_path: str, channel_hint: Optional[str] = None) -> Dict[str, Any]:
        """
        Process a video through the complete pipeline
        
        Args:
            video_path: Path to video file
            
        Returns:
            Processing results
        """
        video_path = Path(video_path)
        result = {
            "video_path": str(video_path),
            "video_name": video_path.name,
            "success": False,
            "queue_id": None,
            "errors": []
        }
        
        try:
            # Check if already processing
            video_hash = self._get_file_hash(video_path)
            if video_hash in self.processing_cache:
                logger.info(f"Video already being processed: {video_path.name}")
                result["errors"].append("Already processing")
                return result
            
            self.processing_cache.add(video_hash)
            
            logger.info(f"Starting processing pipeline for: {video_path.name}")
            
            # Step 1: Analyze video content
            logger.info("Step 1: Analyzing video content...")
            analysis_results = await self.video_analyzer.analyze_video(str(video_path))
            
            if not analysis_results or analysis_results.get("confidence_score", 0) < 0.3:
                logger.warning("Video analysis confidence too low")
                result["errors"].append("Low analysis confidence")
                return result
            
            result["analysis"] = {
                "products": analysis_results.get("products", []),
                "category": analysis_results.get("category"),
                "keywords": analysis_results.get("keywords", []),
                "confidence": analysis_results.get("confidence_score")
            }
            
            # Step 2: Match to appropriate channel
            logger.info("Step 2: Matching to channel...")
            channel_assignment = None

            # If a channel hint is provided (e.g., from folder name), try it first
            if channel_hint:
                try:
                    available = await self.db.get_available_channels()
                    chosen = next((c for c in available if c.get('channel_name') == channel_hint), None)
                    if chosen:
                        channel_assignment = {
                            'channel_id': chosen['id'],
                            'channel_name': chosen.get('channel_name'),
                            'reason': 'folder_hint',
                        }
                        logger.info(f"Using hinted channel: {channel_assignment['channel_name']}")
                except Exception as e:
                    logger.warning(f"Channel hint lookup failed: {e}")

            if not channel_assignment:
                channel_assignment = await self.channel_matcher.assign_channel(
                    str(video_path),
                    analysis_results
                )
            
            if not channel_assignment:
                logger.warning("No suitable channel found")
                result["errors"].append("No channel available")
                return result
            
            result["channel"] = channel_assignment
            
            # Step 3: Generate SEO content
            logger.info("Step 3: Generating SEO content...")
            seo_content = await self.seo_generator.generate_seo_content(
                analysis_results,
                channel_assignment
            )
            
            result["seo"] = seo_content
            
            # Step 4: Match products to shopping links
            logger.info("Step 4: Matching products...")
            product_matches = await self.product_matcher.match_products(
                analysis_results
            )
            
            result["products"] = product_matches
            
            # Step 5: Generate affiliate link if applicable
            coupang_url = None
            if product_matches.get("coupang_links"):
                primary_link = product_matches["coupang_links"][0]["url"]
                coupang_url = await self.product_matcher.generate_infocrlink(
                    primary_link,
                    channel_assignment["channel_id"]
                )
            
            # Step 6: Add to upload queue
            logger.info("Step 6: Adding to upload queue...")
            queue_id = await self.queue_manager.add_to_queue(
                video_path=str(video_path),
                channel_id=channel_assignment["channel_id"],
                title=seo_content["title"],
                description=seo_content["description"],
                tags=seo_content["tags"],
                coupang_url=coupang_url,
                infocrlink_data=product_matches,
                priority=self._calculate_priority(analysis_results)
            )
            
            if queue_id:
                result["queue_id"] = queue_id
                result["success"] = True
                logger.info(f"Successfully processed: {video_path.name} -> Queue ID: {queue_id}")
            else:
                result["errors"].append("Failed to add to queue")
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing video: {e}")
            result["errors"].append(str(e))
            return result
        
        finally:
            # Remove from processing cache
            if video_hash in self.processing_cache:
                self.processing_cache.discard(video_hash)
    
    def _get_file_hash(self, file_path: Path) -> str:
        """Generate hash for file to prevent duplicates"""
        stat = file_path.stat()
        hash_string = f"{file_path.name}_{stat.st_size}_{stat.st_mtime}"
        return hashlib.md5(hash_string.encode()).hexdigest()
    
    def _calculate_priority(self, analysis_results: Dict[str, Any]) -> int:
        """
        Calculate queue priority based on analysis
        
        Args:
            analysis_results: Video analysis results
            
        Returns:
            Priority score (0-100)
        """
        priority = 50  # Base priority
        
        # Boost for high confidence
        confidence = analysis_results.get("confidence_score", 0.5)
        priority += int(confidence * 20)
        
        # Boost for popular categories
        category = analysis_results.get("category", "unknown")
        category_boost = {
            "technology": 10,
            "beauty": 8,
            "gaming": 7,
            "fashion": 6,
            "food": 5
        }
        priority += category_boost.get(category, 0)
        
        # Boost for content type
        content_type = analysis_results.get("content_type", "unknown")
        content_boost = {
            "review": 10,
            "unboxing": 8,
            "comparison": 7,
            "tutorial": 5,
            "haul": 4
        }
        priority += content_boost.get(content_type, 0)
        
        # Cap at 100
        return min(100, priority)
    
    async def process_queue(self):
        """Process videos from the queue"""
        while True:
            try:
                # Get next video from queue
                queue_entry = await self.queue_manager.get_next_video()
                
                if not queue_entry:
                    await asyncio.sleep(30)  # Wait before checking again
                    continue
                
                logger.info(f"Processing queue entry: {queue_entry['id']}")
                
                # Here you would implement actual upload logic
                # For now, we'll simulate processing
                await self._simulate_upload(queue_entry)
                
            except Exception as e:
                logger.error(f"Error processing queue: {e}")
                await asyncio.sleep(60)
    
    async def _simulate_upload(self, queue_entry: Dict[str, Any]):
        """
        Simulate video upload process
        
        Args:
            queue_entry: Queue entry data
        """
        try:
            logger.info(f"Simulating upload for: {queue_entry['video_file_name']}")
            
            # Simulate processing time
            await asyncio.sleep(5)
            
            # Mark as ready (would be uploaded in production)
            await self.queue_manager.update_status(
                queue_entry['id'],
                'ready'
            )
            
            logger.info(f"Queue entry {queue_entry['id']} marked as ready")
            
        except Exception as e:
            logger.error(f"Error in simulated upload: {e}")
            await self.queue_manager.update_status(
                queue_entry['id'],
                'failed',
                str(e)
            )
    
    async def reprocess_failed(self):
        """Reprocess failed queue entries"""
        try:
            # Get failed entries
            failed_entries = await self.queue_manager.get_queue_status(
                status_filter='failed',
                limit=10
            )
            
            for entry in failed_entries:
                logger.info(f"Retrying failed entry: {entry['id']}")
                await self.queue_manager.retry_failed(entry['id'])
            
            return len(failed_entries)
            
        except Exception as e:
            logger.error(f"Error reprocessing failed entries: {e}")
            return 0
    
    async def get_processing_stats(self) -> Dict[str, Any]:
        """Get processing statistics"""
        try:
            # Get queue statistics
            queue_stats = await self.queue_manager.get_statistics()
            
            # Get channel load balance
            channel_stats = await self.channel_matcher.balance_channel_load()
            
            return {
                "queue": queue_stats,
                "channels": channel_stats,
                "currently_processing": len(self.processing_cache)
            }
            
        except Exception as e:
            logger.error(f"Error getting processing stats: {e}")
            return {}

# Global processor instance
_processor: Optional[VideoProcessor] = None

def get_video_processor() -> VideoProcessor:
    """Get or create global video processor"""
    global _processor
    if _processor is None:
        _processor = VideoProcessor()
    return _processor
