"""
Health check and status endpoints
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from datetime import datetime

from src.config import settings
from src.utils.database import get_db_manager
from src.utils.logger import get_logger

router = APIRouter()
logger = get_logger("health")

@router.get("/about")
async def about():
    """Basic service info"""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "timestamp": datetime.now().isoformat()
    }

@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """Health check endpoint"""
    
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": settings.app_version,
        "checks": {}
    }
    
    # Check database connection
    try:
        db = get_db_manager()
        if db.client:
            # Try a simple query
            result = await db.get_queue_overview()
            health_status["checks"]["database"] = {
                "status": "connected",
                "queue_stats": result
            }
        else:
            health_status["checks"]["database"] = {
                "status": "disconnected",
                "error": "No database client"
            }
            health_status["status"] = "degraded"
    except Exception as e:
        health_status["checks"]["database"] = {
            "status": "error",
            "error": str(e)
        }
        health_status["status"] = "unhealthy"
    
    # Check API keys
    health_status["checks"]["api_keys"] = {
        "gemini": bool(settings.gemini_api_key),
        "google_search": bool(settings.google_api_key),
        "coupang": bool(settings.coupang_access_key)
    }
    
    # Check folders
    health_status["checks"]["folders"] = {
        "watch_folder": settings.watch_folder_path.exists(),
        "temp_folder": settings.temp_folder_path.exists(),
        "log_folder": settings.log_folder_path.exists()
    }
    
    return health_status

@router.get("/health/stats")
async def health_stats() -> Dict[str, Any]:
    """Get system statistics"""
    
    try:
        db = get_db_manager()
        
        # Get queue overview
        queue_stats = await db.get_queue_overview()
        
        # Get channel statistics
        channel_stats = await db.get_channel_statistics()
        
        return {
            "timestamp": datetime.now().isoformat(),
            "queue": queue_stats,
            "channels": {
                "total": len(channel_stats),
                "statistics": channel_stats[:5]  # Top 5 channels
            },
            "system": {
                "debug_mode": settings.debug_mode,
                "max_daily_uploads": settings.max_daily_uploads_per_channel,
                "supported_formats": settings.supported_video_formats
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))
