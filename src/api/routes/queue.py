"""
Upload queue management endpoints
"""

from fastapi import APIRouter, HTTPException, Query, File, UploadFile, BackgroundTasks
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime

from src.utils.database import get_db_manager
from src.utils.logger import get_logger

router = APIRouter()
logger = get_logger("queue")

# Pydantic models
class QueueItemCreate(BaseModel):
    video_file_path: str = Field(..., min_length=1)
    video_file_name: str = Field(..., min_length=1, max_length=500)
    file_size_mb: Optional[float] = Field(None, ge=0)
    channel_id: Optional[str] = None
    title: str = Field(..., min_length=1, max_length=500)
    description: str = Field(..., min_length=1)
    tags: Optional[List[str]] = []
    coupang_url: Optional[str] = None
    infocrlink_data: Optional[dict] = None
    priority: int = Field(default=50, ge=0, le=100)
    scheduled_time: Optional[datetime] = None

class QueueItemUpdate(BaseModel):
    channel_id: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    coupang_url: Optional[str] = None
    status: Optional[str] = Field(None, pattern="^(pending|processing|ready|uploaded|failed)$")
    priority: Optional[int] = Field(None, ge=0, le=100)
    scheduled_time: Optional[datetime] = None
    error_message: Optional[str] = None

class QueueItemResponse(BaseModel):
    id: str
    video_file_path: str
    video_file_name: str
    file_size_mb: Optional[float]
    channel_id: Optional[str]
    title: str
    description: str
    tags: List[str]
    coupang_url: Optional[str]
    infocrlink_data: Optional[dict]
    status: str
    priority: int
    scheduled_time: Optional[datetime]
    error_message: Optional[str]
    created_at: datetime
    updated_at: datetime

@router.post("/", response_model=QueueItemResponse)
async def add_to_queue(item: QueueItemCreate):
    """Add a video to the upload queue"""
    try:
        db = get_db_manager()
        
        # Check channel exists if provided
        if item.channel_id:
            channel = await db.get_channel(item.channel_id)
            if not channel:
                raise HTTPException(status_code=404, detail="Channel not found")
            
            # Check upload limit
            can_upload = await db.check_channel_limit(item.channel_id)
            if not can_upload:
                raise HTTPException(
                    status_code=400, 
                    detail="Channel has reached daily upload limit"
                )
        
        # Add to queue
        result = await db.add_to_queue(item.dict())
        
        if not result:
            raise HTTPException(status_code=500, detail="Failed to add to queue")
        
        logger.info(f"Added to queue: {result['id']}")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding to queue: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/", response_model=List[QueueItemResponse])
async def list_queue_items(
    status: Optional[str] = Query(None, pattern="^(pending|processing|ready|uploaded|failed)$"),
    channel_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """List items in the upload queue"""
    try:
        db = get_db_manager()
        
        # Get queue items
        items = await db.get_queue_items(status=status, limit=limit)
        
        # Filter by channel if specified
        if channel_id:
            items = [i for i in items if i.get('channel_id') == channel_id]
        
        # Apply offset
        items = items[offset:]
        
        return items
        
    except Exception as e:
        logger.error(f"Error listing queue items: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{queue_id}", response_model=QueueItemResponse)
async def get_queue_item(queue_id: str):
    """Get a specific queue item"""
    try:
        db = get_db_manager()
        
        # Get single item (using list method with filter)
        items = await db.get_queue_items(limit=1)
        item = next((i for i in items if i['id'] == queue_id), None)
        
        if not item:
            raise HTTPException(status_code=404, detail="Queue item not found")
        
        return item
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting queue item {queue_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/{queue_id}", response_model=QueueItemResponse)
async def update_queue_item(queue_id: str, updates: QueueItemUpdate):
    """Update a queue item"""
    try:
        db = get_db_manager()
        
        # Check item exists
        items = await db.get_queue_items(limit=100)
        item = next((i for i in items if i['id'] == queue_id), None)
        
        if not item:
            raise HTTPException(status_code=404, detail="Queue item not found")
        
        # Prepare updates (exclude None values)
        update_data = {k: v for k, v in updates.dict().items() if v is not None}
        
        # Update item
        result = await db.update_queue_item(queue_id, update_data)
        
        if not result:
            raise HTTPException(status_code=500, detail="Failed to update queue item")
        
        logger.info(f"Updated queue item: {queue_id}")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating queue item {queue_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{queue_id}/process")
async def process_queue_item(queue_id: str, background_tasks: BackgroundTasks):
    """Start processing a queue item"""
    try:
        db = get_db_manager()

        # Update status to processing
        result = await db.update_queue_item(queue_id, {"status": "processing"})

        if not result:
            raise HTTPException(status_code=404, detail="Queue item not found")

        # Simulate processing in background then mark as ready
        async def _simulate_and_mark_ready(qid: str):
            try:
                import asyncio
                logger.info(f"Simulating processing for queue item: {qid}")
                await asyncio.sleep(5)
                await db.update_queue_item(qid, {"status": "ready"})
                logger.info(f"Queue item {qid} marked as ready")
            except Exception as e:
                logger.error(f"Error simulating processing for {qid}: {e}")
                await db.update_queue_item(qid, {"status": "failed", "error_message": str(e)})

        background_tasks.add_task(_simulate_and_mark_ready, queue_id)

        logger.info(f"Started processing queue item: {queue_id}")

        return {
            "message": "Processing started",
            "queue_id": queue_id,
            "status": "processing"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing queue item {queue_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats/overview")
async def get_queue_overview():
    """Get queue statistics overview"""
    try:
        db = get_db_manager()
        
        overview = await db.get_queue_overview()
        
        return {
            "timestamp": datetime.now().isoformat(),
            "statistics": overview,
            "total_items": sum(s.get('count', 0) for s in overview.values())
        }
        
    except Exception as e:
        logger.error(f"Error getting queue overview: {e}")
        raise HTTPException(status_code=500, detail=str(e))
