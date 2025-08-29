"""
YouTube channel management endpoints
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime

from src.utils.database import get_db_manager
from src.utils.logger import get_logger

router = APIRouter()
logger = get_logger("channels")

# Pydantic models
class ChannelCreate(BaseModel):
    channel_name: str = Field(..., min_length=1, max_length=255)
    channel_url: str = Field(..., min_length=1, max_length=500)
    channel_type: str = Field(..., pattern="^(main|sub)$")
    parent_channel_id: Optional[str] = None
    category: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    account_id: str = Field(..., min_length=1)
    account_password: str = Field(..., min_length=1)
    infocrlink_url: Optional[str] = None
    max_daily_uploads: int = Field(default=3, ge=1, le=10)

class ChannelUpdate(BaseModel):
    channel_name: Optional[str] = None
    channel_url: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    account_id: Optional[str] = None
    account_password: Optional[str] = None
    infocrlink_url: Optional[str] = None
    max_daily_uploads: Optional[int] = None
    is_active: Optional[bool] = None

class ChannelResponse(BaseModel):
    id: str
    channel_name: str
    channel_url: str
    channel_type: str
    parent_channel_id: Optional[str]
    category: str
    description: Optional[str]
    infocrlink_url: Optional[str]
    max_daily_uploads: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    # Sensitive fields excluded from response

@router.post("/", response_model=ChannelResponse)
async def create_channel(channel: ChannelCreate):
    """Create a new YouTube channel"""
    try:
        db = get_db_manager()
        
        # Prepare channel data
        channel_data = channel.dict()
        
        # Create channel
        result = await db.create_channel(channel_data)
        
        if not result:
            raise HTTPException(status_code=500, detail="Failed to create channel")
        
        logger.info(f"Created channel: {result['id']}")
        
        # Remove sensitive fields from response
        result.pop('account_id', None)
        result.pop('account_password', None)
        
        return result
        
    except Exception as e:
        logger.error(f"Error creating channel: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/", response_model=List[ChannelResponse])
async def list_channels(
    category: Optional[str] = Query(None, description="Filter by category"),
    channel_type: Optional[str] = Query(None, pattern="^(main|sub)$"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    limit: int = Query(50, ge=1, le=100)
):
    """List all YouTube channels"""
    try:
        db = get_db_manager()
        
        # For now, get all channels and filter in memory
        # In production, implement proper database filtering
        channels = await db.get_available_channels(category=category)
        
        # Apply filters
        if channel_type:
            channels = [c for c in channels if c.get('channel_type') == channel_type]
        
        if is_active is not None:
            channels = [c for c in channels if c.get('is_active') == is_active]
        
        # Limit results
        channels = channels[:limit]
        
        # Remove sensitive fields
        for channel in channels:
            channel.pop('account_id', None)
            channel.pop('account_password', None)
        
        return channels
        
    except Exception as e:
        logger.error(f"Error listing channels: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/available", response_model=List[ChannelResponse])
async def get_available_channels(
    category: Optional[str] = Query(None, description="Filter by category")
):
    """Get channels that haven't reached their daily upload limit"""
    try:
        db = get_db_manager()
        
        channels = await db.get_available_channels(category=category)
        
        # Remove sensitive fields
        for channel in channels:
            channel.pop('account_id', None)
            channel.pop('account_password', None)
        
        return channels
        
    except Exception as e:
        logger.error(f"Error getting available channels: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{channel_id}", response_model=ChannelResponse)
async def get_channel(channel_id: str):
    """Get a specific channel by ID"""
    try:
        db = get_db_manager()
        
        channel = await db.get_channel(channel_id)
        
        if not channel:
            raise HTTPException(status_code=404, detail="Channel not found")
        
        # Remove sensitive fields
        channel.pop('account_id', None)
        channel.pop('account_password', None)
        
        return channel
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting channel {channel_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{channel_id}/limits")
async def check_channel_limits(channel_id: str):
    """Check upload limits for a channel"""
    try:
        db = get_db_manager()
        
        # Check if channel exists
        channel = await db.get_channel(channel_id)
        if not channel:
            raise HTTPException(status_code=404, detail="Channel not found")
        
        # Check upload limit
        can_upload = await db.check_channel_limit(channel_id)
        
        return {
            "channel_id": channel_id,
            "channel_name": channel['channel_name'],
            "can_upload": can_upload,
            "max_daily_uploads": channel['max_daily_uploads'],
            "today_uploads": channel.get('today_uploads', 0),
            "remaining_uploads": channel.get('remaining_uploads', 0)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking limits for channel {channel_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))