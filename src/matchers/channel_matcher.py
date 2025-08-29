"""
Channel Matcher Module
Matches analyzed videos to appropriate YouTube channels based on category and content
"""

import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, date
import json

from src.config import settings
from src.utils.logger import get_logger
from src.utils.database import get_db_manager

logger = get_logger("channel_matcher")

class ChannelMatcher:
    """Matches videos to appropriate YouTube channels"""
    
    def __init__(self):
        """Initialize Channel Matcher"""
        self.db = get_db_manager()
        self.category_mapping = self._initialize_category_mapping()
        self.content_type_weights = self._initialize_content_weights()
        logger.info("Channel Matcher initialized")
    
    def _initialize_category_mapping(self) -> Dict[str, List[str]]:
        """Initialize category to channel category mapping"""
        return {
            # Video categories -> Channel categories
            "technology": ["technology", "tech", "gadget", "review"],
            "tech": ["technology", "tech", "gadget", "review"],
            "beauty": ["beauty", "cosmetics", "makeup", "lifestyle"],
            "fashion": ["fashion", "style", "clothing", "lifestyle"],
            "food": ["food", "cooking", "recipe", "lifestyle"],
            "lifestyle": ["lifestyle", "general", "vlog", "daily"],
            "gaming": ["gaming", "game", "esports", "entertainment"],
            "sports": ["sports", "fitness", "health", "lifestyle"],
            "home": ["home", "interior", "diy", "lifestyle"],
            "kids": ["kids", "toy", "children", "family"],
            "pet": ["pet", "animal", "lifestyle"],
            "travel": ["travel", "tourism", "lifestyle"],
            "unknown": ["general", "lifestyle", "misc"]
        }
    
    def _initialize_content_weights(self) -> Dict[str, Dict[str, float]]:
        """Initialize content type preference weights for channel types"""
        return {
            "review": {
                "main": 1.0,
                "sub": 0.8
            },
            "unboxing": {
                "main": 0.9,
                "sub": 0.9
            },
            "tutorial": {
                "main": 0.8,
                "sub": 1.0
            },
            "comparison": {
                "main": 1.0,
                "sub": 0.7
            },
            "haul": {
                "main": 0.7,
                "sub": 1.0
            },
            "unknown": {
                "main": 0.5,
                "sub": 0.5
            }
        }
    
    async def find_best_channel(self, analysis_results: Dict[str, Any]) -> Optional[str]:
        """
        Find the best matching channel for a video based on analysis
        
        Args:
            analysis_results: Video analysis results from Gemini
            
        Returns:
            Channel ID if match found, None otherwise
        """
        try:
            category = analysis_results.get("category", "unknown")
            content_type = analysis_results.get("content_type", "unknown")
            confidence = analysis_results.get("confidence_score", 0.5)
            
            logger.info(f"Finding channel for category: {category}, type: {content_type}")
            
            # Get available channels
            available_channels = await self._get_available_channels()
            
            if not available_channels:
                logger.warning("No available channels found")
                return None
            
            # Score channels
            channel_scores = await self._score_channels(
                available_channels,
                category,
                content_type,
                confidence
            )
            
            # Select best channel
            if channel_scores:
                best_channel = max(channel_scores.items(), key=lambda x: x[1])
                channel_id = best_channel[0]
                score = best_channel[1]
                
                if score > 0.3:  # Minimum score threshold
                    logger.info(f"Selected channel {channel_id} with score {score:.2f}")
                    return channel_id
                else:
                    logger.warning(f"No channel with sufficient score (max: {score:.2f})")
            
            return None
            
        except Exception as e:
            logger.error(f"Error finding channel: {e}")
            return None
    
    async def _get_available_channels(self) -> List[Dict[str, Any]]:
        """
        Get list of available channels (not at upload limit)
        
        Returns:
            List of available channels
        """
        try:
            # If no direct SQL connection (development), use DatabaseManager fallback
            if not getattr(self.db, 'pg_dsn', None):
                channels = await self.db.get_available_channels()
                logger.info(f"Found {len(channels)} available channels (fallback)")
                return channels

            # Get channels with remaining upload capacity via SQL
            query = """
            SELECT 
                c.id,
                c.channel_name,
                c.channel_type,
                c.category,
                c.max_daily_uploads,
                COALESCE(l.upload_count, 0) as today_uploads
            FROM youtube_channels c
            LEFT JOIN channel_upload_limits l 
                ON c.id = l.channel_id 
                AND l.upload_date = CURRENT_DATE
            WHERE c.is_active = true
                AND (l.upload_count IS NULL OR l.upload_count < c.max_daily_uploads)
            ORDER BY 
                c.channel_type ASC,  -- Prefer main channels
                (c.max_daily_uploads - COALESCE(l.upload_count, 0)) DESC
            """

            result = await self.db.execute_query(query)

            if result and result.data:
                logger.info(f"Found {len(result.data)} available channels")
                return result.data

            return []

        except Exception as e:
            logger.error(f"Error getting available channels: {e}")
            # Fallback to REST/memory path if available
            try:
                channels = await self.db.get_available_channels()
                if channels:
                    logger.info(f"Found {len(channels)} available channels (fallback)")
                return channels
            except Exception:
                return []
    
    async def _score_channels(
        self,
        channels: List[Dict[str, Any]],
        video_category: str,
        content_type: str,
        confidence: float
    ) -> Dict[str, float]:
        """
        Score channels based on video characteristics
        
        Args:
            channels: List of available channels
            video_category: Video category
            content_type: Video content type
            confidence: Analysis confidence score
            
        Returns:
            Dictionary of channel_id -> score
        """
        scores = {}
        
        # Get matching channel categories
        matching_categories = self.category_mapping.get(
            video_category.lower(), 
            ["general", "lifestyle"]
        )
        
        for channel in channels:
            score = 0.0
            channel_id = channel['id']
            channel_category = channel.get('category', '').lower()
            channel_type = channel.get('channel_type', 'sub')
            remaining_uploads = channel.get('max_daily_uploads', 3) - channel.get('today_uploads', 0)
            
            # Category match score (0-1)
            if channel_category in matching_categories:
                # Direct match gets higher score
                if channel_category == video_category.lower():
                    score += 1.0
                else:
                    # Related category gets partial score
                    score += 0.6
            elif channel_category in ["general", "lifestyle", "misc"]:
                # Generic channels can accept any content
                score += 0.3
            
            # Content type preference (0-1)
            content_weight = self.content_type_weights.get(
                content_type, 
                {"main": 0.5, "sub": 0.5}
            )
            score += content_weight.get(channel_type, 0.5)
            
            # Upload capacity bonus (0-0.5)
            capacity_bonus = min(0.5, remaining_uploads * 0.1)
            score += capacity_bonus
            
            # Channel type preference (0-0.3)
            if channel_type == "main":
                score += 0.3
            else:
                score += 0.1
            
            # Apply confidence factor
            score *= confidence
            
            scores[channel_id] = score
            
            logger.debug(
                f"Channel {channel.get('channel_name')} scored {score:.2f} "
                f"(cat: {channel_category}, type: {channel_type})"
            )
        
        return scores
    
    async def assign_channel(
        self,
        video_path: str,
        analysis_results: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Assign a video to a channel and create queue entry
        
        Args:
            video_path: Path to video file
            analysis_results: Video analysis results
            
        Returns:
            Queue entry if successful, None otherwise
        """
        try:
            # Find best matching channel
            channel_id = await self.find_best_channel(analysis_results)
            
            if not channel_id:
                logger.warning(f"No suitable channel found for {video_path}")
                return None
            
            # Get channel details
            channel = await self._get_channel_details(channel_id)
            
            if not channel:
                logger.error(f"Channel {channel_id} not found")
                return None
            
            logger.info(
                f"Assigned video to channel: {channel.get('channel_name')} "
                f"({channel.get('channel_type')})"
            )
            
            return {
                "channel_id": channel_id,
                "channel_name": channel.get("channel_name"),
                "channel_type": channel.get("channel_type"),
                "channel_category": channel.get("category")
            }
            
        except Exception as e:
            logger.error(f"Error assigning channel: {e}")
            return None
    
    async def _get_channel_details(self, channel_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a channel
        
        Args:
            channel_id: Channel UUID
            
        Returns:
            Channel details or None
        """
        try:
            query = """
            SELECT 
                id,
                channel_name,
                channel_url,
                channel_type,
                category,
                description,
                infocrlink_url,
                max_daily_uploads,
                is_active
            FROM youtube_channels
            WHERE id = %s
            """
            
            result = await self.db.execute_query(query, (channel_id,))
            
            if result and result.data:
                return result.data[0]
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting channel details: {e}")
            return None
    
    async def check_channel_limit(self, channel_id: str) -> bool:
        """
        Check if channel has reached upload limit
        
        Args:
            channel_id: Channel UUID
            
        Returns:
            True if under limit, False otherwise
        """
        try:
            query = """
            SELECT check_channel_upload_limit(%s) as can_upload
            """
            
            result = await self.db.execute_query(query, (channel_id,))
            
            if result and result.data:
                return result.data[0].get('can_upload', False)
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking channel limit: {e}")
            return False
    
    async def get_channel_statistics(self, channel_id: str) -> Dict[str, Any]:
        """
        Get upload statistics for a channel
        
        Args:
            channel_id: Channel UUID
            
        Returns:
            Channel statistics
        """
        try:
            query = """
            SELECT 
                c.channel_name,
                c.max_daily_uploads,
                COALESCE(l.upload_count, 0) as today_uploads,
                c.max_daily_uploads - COALESCE(l.upload_count, 0) as remaining_uploads,
                COUNT(DISTINCT h.id) as total_uploads,
                COUNT(DISTINCT CASE 
                    WHEN h.upload_time > NOW() - INTERVAL '7 days' 
                    THEN h.id 
                END) as uploads_last_7_days
            FROM youtube_channels c
            LEFT JOIN channel_upload_limits l 
                ON c.id = l.channel_id 
                AND l.upload_date = CURRENT_DATE
            LEFT JOIN upload_history h 
                ON c.id = h.channel_id
            WHERE c.id = %s
            GROUP BY c.id, c.channel_name, c.max_daily_uploads, l.upload_count
            """
            
            result = await self.db.execute_query(query, (channel_id,))
            
            if result and result.data:
                return result.data[0]
            
            return {}
            
        except Exception as e:
            logger.error(f"Error getting channel statistics: {e}")
            return {}
    
    async def balance_channel_load(self) -> Dict[str, Any]:
        """
        Get channel load balancing information
        
        Returns:
            Load distribution across channels
        """
        try:
            query = """
            SELECT 
                c.channel_name,
                c.channel_type,
                c.category,
                c.max_daily_uploads,
                COALESCE(l.upload_count, 0) as today_uploads,
                c.max_daily_uploads - COALESCE(l.upload_count, 0) as remaining_capacity,
                ROUND(
                    (COALESCE(l.upload_count, 0)::float / c.max_daily_uploads) * 100, 
                    2
                ) as utilization_percent
            FROM youtube_channels c
            LEFT JOIN channel_upload_limits l 
                ON c.id = l.channel_id 
                AND l.upload_date = CURRENT_DATE
            WHERE c.is_active = true
            ORDER BY utilization_percent DESC, c.channel_type ASC
            """
            
            result = await self.db.execute_query(query)
            
            if result and result.data:
                return {
                    "channels": result.data,
                    "total_capacity": sum(ch['max_daily_uploads'] for ch in result.data),
                    "used_capacity": sum(ch['today_uploads'] for ch in result.data),
                    "available_capacity": sum(ch['remaining_capacity'] for ch in result.data)
                }
            
            return {"channels": [], "total_capacity": 0, "used_capacity": 0, "available_capacity": 0}
            
        except Exception as e:
            logger.error(f"Error getting load balance info: {e}")
            return {"channels": [], "total_capacity": 0, "used_capacity": 0, "available_capacity": 0}

# Global matcher instance
_matcher: Optional[ChannelMatcher] = None

def get_channel_matcher() -> ChannelMatcher:
    """Get or create global channel matcher"""
    global _matcher
    if _matcher is None:
        _matcher = ChannelMatcher()
    return _matcher
