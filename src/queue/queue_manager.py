"""
Queue Manager Module
Manages upload queue with priority, scheduling, and status tracking
"""

import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from pathlib import Path
import json
import uuid

from src.config import settings
from src.utils.logger import get_logger
from src.utils.database import get_db_manager

logger = get_logger("queue_manager")

class QueueManager:
    """Manages the upload queue for videos"""
    
    def __init__(self):
        """Initialize Queue Manager"""
        self.db = get_db_manager()
        self.status_transitions = self._init_status_transitions()
        logger.info("Queue Manager initialized")
    
    def _init_status_transitions(self) -> Dict[str, List[str]]:
        """Initialize valid status transitions"""
        return {
            "pending": ["processing", "failed"],
            "processing": ["ready", "failed"],
            "ready": ["uploaded", "failed", "pending"],
            "uploaded": [],  # Terminal state
            "failed": ["pending"]  # Can retry
        }
    
    async def add_to_queue(
        self,
        video_path: str,
        channel_id: str,
        title: str,
        description: str,
        tags: List[str],
        coupang_url: Optional[str] = None,
        infocrlink_data: Optional[Dict] = None,
        priority: int = 50,
        scheduled_time: Optional[datetime] = None
    ) -> Optional[str]:
        """
        Add a video to the upload queue
        
        Args:
            video_path: Path to video file
            channel_id: Assigned channel ID
            title: Video title
            description: Video description
            tags: List of tags
            coupang_url: Product link
            infocrlink_data: Product match data
            priority: Queue priority (0-100, higher is more priority)
            scheduled_time: Optional scheduled upload time
            
        Returns:
            Queue ID if successful
        """
        try:
            video_path = Path(video_path)

            if not video_path.exists():
                logger.error(f"Video file not found: {video_path}")
                return None

            # Get file size
            file_size_mb = video_path.stat().st_size / (1024 * 1024)

            # Check file size limits
            if file_size_mb > settings.max_file_size_mb:
                logger.warning(f"File too large: {file_size_mb:.2f} MB")
                return None

            if file_size_mb < settings.min_file_size_mb:
                logger.warning(f"File too small: {file_size_mb:.2f} MB")
                return None

            # Generate queue ID
            queue_id = str(uuid.uuid4())

            # If no direct DB connection, use in-memory via DatabaseManager
            if not getattr(self.db, 'pg_dsn', None):
                queue_item = {
                    "id": queue_id,
                    "video_file_path": str(video_path),
                    "video_file_name": video_path.name,
                    "file_size_mb": file_size_mb,
                    "channel_id": channel_id,
                    "title": title,
                    "description": description,
                    "tags": tags,
                    "coupang_url": coupang_url,
                    "infocrlink_data": infocrlink_data,
                    "priority": priority,
                    "scheduled_time": scheduled_time,
                    "status": "pending",
                }
                rec = await self.db.add_to_queue(queue_item)
                if rec:
                    logger.info(f"Added video to queue (memory): {queue_id} - {video_path.name}")
                    return rec.get('id', queue_id)
                logger.error("Failed to add to memory queue")
                return None

            # Insert into SQL queue
            query = """
            INSERT INTO upload_queue (
                id,
                video_file_path,
                video_file_name,
                file_size_mb,
                channel_id,
                title,
                description,
                tags,
                coupang_url,
                infocrlink_data,
                status,
                priority,
                scheduled_time,
                created_at,
                updated_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW()
            )
            """

            params = (
                queue_id,
                str(video_path),
                video_path.name,
                file_size_mb,
                channel_id,
                title,
                description,
                tags,
                coupang_url,
                json.dumps(infocrlink_data) if infocrlink_data else None,
                "pending",
                priority,
                scheduled_time
            )

            await self.db.execute_query(query, params)

            logger.info(f"Added video to queue: {queue_id} - {video_path.name}")
            return queue_id

        except Exception as e:
            logger.error(f"Error adding to queue: {e}")
            return None
    
    async def get_next_video(self) -> Optional[Dict[str, Any]]:
        """
        Get the next video to process from queue
        
        Returns:
            Queue entry or None
        """
        try:
            # In-memory fallback
            if not getattr(self.db, 'pg_dsn', None):
                items = await self.db.get_queue_items(status='pending', limit=1)
                if items:
                    entry = items[0]
                    await self.db.update_queue_item(entry['id'], {"status": "processing"})
                    logger.info(f"Retrieved queue entry (memory): {entry['id']}")
                    return entry
                return None

            query = """
            SELECT 
                q.*,
                c.channel_name,
                c.channel_url,
                c.channel_type,
                c.category as channel_category,
                c.account_id,
                c.account_password,
                c.infocrlink_url as channel_infocrlink
            FROM upload_queue q
            JOIN youtube_channels c ON q.channel_id = c.id
            WHERE q.status = 'pending'
                AND c.is_active = true
                AND (q.scheduled_time IS NULL OR q.scheduled_time <= NOW())
                AND check_channel_upload_limit(q.channel_id) = true
            ORDER BY 
                q.priority DESC,
                q.created_at ASC
            LIMIT 1
            FOR UPDATE SKIP LOCKED
            """
            
            result = await self.db.execute_query(query)

            if result and result.data:
                queue_entry = result.data[0]

                # Update status to processing
                await self.update_status(queue_entry['id'], 'processing')

                logger.info(f"Retrieved queue entry: {queue_entry['id']}")
                return queue_entry

            return None

        except Exception as e:
            logger.error(f"Error getting next video: {e}")
            # Fallback to REST/memory queue
            try:
                items = await self.db.get_queue_items(status='pending', limit=1)
                if items:
                    entry = items[0]
                    await self.db.update_queue_item(entry['id'], {"status": "processing"})
                    logger.info(f"Retrieved queue entry (fallback): {entry['id']}")
                    return entry
            except Exception:
                pass
            return None
    
    async def update_status(
        self,
        queue_id: str,
        new_status: str,
        error_message: Optional[str] = None
    ) -> bool:
        """
        Update queue entry status
        
        Args:
            queue_id: Queue entry ID
            new_status: New status
            error_message: Optional error message
            
        Returns:
            Success status
        """
        try:
            # Get current status
            current_status = await self._get_current_status(queue_id)
            
            if not current_status:
                logger.error(f"Queue entry not found: {queue_id}")
                return False
            
            # Check if transition is valid
            valid_transitions = self.status_transitions.get(current_status, [])
            
            if new_status not in valid_transitions and new_status != current_status:
                logger.warning(
                    f"Invalid status transition: {current_status} -> {new_status}"
                )
                return False
            
            # Update status
            if not getattr(self.db, 'pg_dsn', None):
                await self.db.update_queue_item(queue_id, {"status": new_status, "error_message": error_message})
            else:
                query = """
                UPDATE upload_queue
                SET 
                    status = %s,
                    error_message = %s,
                    updated_at = NOW()
                WHERE id = %s
                """
                await self.db.execute_query(query, (new_status, error_message, queue_id))
            
            logger.info(f"Updated queue {queue_id}: {current_status} -> {new_status}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating status: {e}")
            return False
    
    async def _get_current_status(self, queue_id: str) -> Optional[str]:
        """Get current status of queue entry"""
        try:
            if not getattr(self.db, 'pg_dsn', None):
                items = await self.db.get_queue_items(limit=100)
                for it in items:
                    if it.get('id') == queue_id:
                        return it.get('status')
                return None

            query = "SELECT status FROM upload_queue WHERE id = %s"
            result = await self.db.execute_query(query, (queue_id,))
            if result and result.data:
                return result.data[0]['status']
            return None
            
        except Exception as e:
            logger.error(f"Error getting current status: {e}")
            return None
    
    async def get_queue_status(
        self,
        status_filter: Optional[str] = None,
        channel_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get queue entries by status
        
        Args:
            status_filter: Optional status filter
            channel_id: Optional channel filter
            limit: Maximum results
            
        Returns:
            List of queue entries
        """
        try:
            # In-memory fallback
            if not getattr(self.db, 'pg_dsn', None):
                items = await self.db.get_queue_items(status=status_filter, limit=limit)
                if channel_id:
                    items = [i for i in items if i.get('channel_id') == channel_id]
                return items

            conditions = []
            params = []

            if status_filter:
                conditions.append("q.status = %s")
                params.append(status_filter)

            if channel_id:
                conditions.append("q.channel_id = %s")
                params.append(channel_id)

            where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

            query = f"""
            SELECT 
                q.*,
                c.channel_name,
                c.channel_type,
                c.category as channel_category
            FROM upload_queue q
            LEFT JOIN youtube_channels c ON q.channel_id = c.id
            {where_clause}
            ORDER BY 
                CASE q.status
                    WHEN 'processing' THEN 1
                    WHEN 'ready' THEN 2
                    WHEN 'pending' THEN 3
                    WHEN 'failed' THEN 4
                    WHEN 'uploaded' THEN 5
                    ELSE 6
                END,
                q.priority DESC,
                q.created_at DESC
            LIMIT %s
            """

            params.append(limit)
            result = await self.db.execute_query(query, params)

            return result.data if result else []

        except Exception as e:
            logger.error(f"Error getting queue status: {e}")
            return []
    
    async def mark_as_uploaded(
        self,
        queue_id: str,
        youtube_video_id: str,
        youtube_video_url: str
    ) -> bool:
        """
        Mark video as uploaded and move to history
        
        Args:
            queue_id: Queue entry ID
            youtube_video_id: YouTube video ID
            youtube_video_url: YouTube video URL
            
        Returns:
            Success status
        """
        try:
            # Begin transaction
            async with self.db.transaction():
                # Update queue status
                await self.update_status(queue_id, "uploaded")
                
                # Get queue entry details
                query = """
                SELECT 
                    channel_id,
                    video_file_name
                FROM upload_queue
                WHERE id = %s
                """
                
                result = await self.db.execute_query(query, (queue_id,))
                
                if not result or not result.data:
                    raise Exception("Queue entry not found")
                
                queue_data = result.data[0]
                
                # Insert into history
                history_query = """
                INSERT INTO upload_history (
                    queue_id,
                    channel_id,
                    video_file_name,
                    upload_time,
                    youtube_video_id,
                    youtube_video_url,
                    created_at
                ) VALUES (
                    %s, %s, %s, NOW(), %s, %s, NOW()
                )
                """
                
                await self.db.execute_query(
                    history_query,
                    (
                        queue_id,
                        queue_data['channel_id'],
                        queue_data['video_file_name'],
                        youtube_video_id,
                        youtube_video_url
                    )
                )
                
                # Increment channel upload count
                await self._increment_upload_count(queue_data['channel_id'])
            
            logger.info(f"Marked as uploaded: {queue_id} -> {youtube_video_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error marking as uploaded: {e}")
            return False
    
    async def _increment_upload_count(self, channel_id: str):
        """Increment channel upload count for today"""
        try:
            query = "SELECT increment_upload_count(%s)"
            await self.db.execute_query(query, (channel_id,))
        except Exception as e:
            logger.error(f"Error incrementing upload count: {e}")
    
    async def retry_failed(self, queue_id: str) -> bool:
        """
        Retry a failed queue entry
        
        Args:
            queue_id: Queue entry ID
            
        Returns:
            Success status
        """
        try:
            # Reset to pending status
            return await self.update_status(queue_id, "pending", None)
            
        except Exception as e:
            logger.error(f"Error retrying failed entry: {e}")
            return False
    
    async def clean_old_entries(self, days: int = 30) -> int:
        """
        Clean old uploaded/failed entries
        
        Args:
            days: Days to keep
            
        Returns:
            Number of entries cleaned
        """
        try:
            query = """
            DELETE FROM upload_queue
            WHERE status IN ('uploaded', 'failed')
                AND updated_at < NOW() - INTERVAL '%s days'
            """
            
            result = await self.db.execute_query(query, (days,))
            
            count = result.rowcount if result else 0
            logger.info(f"Cleaned {count} old queue entries")
            
            return count
            
        except Exception as e:
            logger.error(f"Error cleaning old entries: {e}")
            return 0
    
    async def get_statistics(self) -> Dict[str, Any]:
        """
        Get queue statistics
        
        Returns:
            Queue statistics
        """
        try:
            query = """
            SELECT 
                status,
                COUNT(*) as count,
                MIN(created_at) as oldest,
                MAX(created_at) as newest,
                AVG(file_size_mb) as avg_file_size
            FROM upload_queue
            GROUP BY status
            """
            
            result = await self.db.execute_query(query)
            
            stats = {
                "by_status": {},
                "total": 0
            }
            
            if result and result.data:
                for row in result.data:
                    stats["by_status"][row['status']] = {
                        "count": row['count'],
                        "oldest": row['oldest'],
                        "newest": row['newest'],
                        "avg_file_size_mb": float(row['avg_file_size']) if row['avg_file_size'] else 0
                    }
                    stats["total"] += row['count']
            
            # Get today's uploads
            today_query = """
            SELECT COUNT(*) as today_count
            FROM upload_history
            WHERE upload_time >= CURRENT_DATE
            """
            
            today_result = await self.db.execute_query(today_query)
            if today_result and today_result.data:
                stats["today_uploads"] = today_result.data[0]['today_count']
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return {"by_status": {}, "total": 0, "today_uploads": 0}
    
    async def schedule_upload(
        self,
        queue_id: str,
        scheduled_time: datetime
    ) -> bool:
        """
        Schedule a queue entry for specific time
        
        Args:
            queue_id: Queue entry ID
            scheduled_time: Scheduled upload time
            
        Returns:
            Success status
        """
        try:
            query = """
            UPDATE upload_queue
            SET 
                scheduled_time = %s,
                updated_at = NOW()
            WHERE id = %s AND status = 'pending'
            """
            
            await self.db.execute_query(query, (scheduled_time, queue_id))
            
            logger.info(f"Scheduled {queue_id} for {scheduled_time}")
            return True
            
        except Exception as e:
            logger.error(f"Error scheduling upload: {e}")
            return False

# Global manager instance
_manager: Optional[QueueManager] = None

def get_queue_manager() -> QueueManager:
    """Get or create global queue manager"""
    global _manager
    if _manager is None:
        _manager = QueueManager()
    return _manager
