"""
FastAPI Application Setup
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
from typing import Dict, Any
from pathlib import Path

from src.config import settings
from src.utils.logger import get_logger

# Setup logger
logger = get_logger("api")

def create_app() -> FastAPI:
    """Create and configure FastAPI application"""
    
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="UGC Video Manager API - Automated video processing and upload queue management",
        docs_url="/docs",
        redoc_url="/redoc"
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Add routes
    setup_routes(app)
    
    # Add exception handlers
    setup_exception_handlers(app)
    
    # Add startup/shutdown events
    setup_events(app)
    
    return app

def setup_routes(app: FastAPI):
    """Setup API routes"""
    
    # Import routers
    from src.api.routes import health, channels, queue, analyze, admin
    
    # Include routers
    app.include_router(health.router, tags=["Health"])
    app.include_router(channels.router, prefix="/api/channels", tags=["Channels"])
    app.include_router(queue.router, prefix="/api/queue", tags=["Queue"])
    app.include_router(analyze.router, prefix="/api/analyze", tags=["Analysis"])
    app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])
    
    # Mount static files
    static_dir = Path(__file__).parent.parent.parent / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    
    # Serve dashboard at root
    @app.get("/")
    async def serve_dashboard():
        index_file = static_dir / "index.html"
        if index_file.exists():
            return FileResponse(str(index_file))
        return {"message": "UGC Video Manager API", "docs": "/docs"}
    
    # Dashboard API endpoints
    @app.get("/stats")
    async def get_stats():
        """Get system statistics"""
        from src.processors.video_processor import get_video_processor
        processor = get_video_processor()
        stats = await processor.get_processing_stats()
        
        queue_stats = stats.get("queue", {})
        return {
            "total_videos": queue_stats.get("total", 0),
            "today_uploads": queue_stats.get("today_uploads", 0),
            "pending_count": queue_stats.get("by_status", {}).get("pending", {}).get("count", 0),
            "processing_count": queue_stats.get("by_status", {}).get("processing", {}).get("count", 0),
        }
    
    @app.get("/queue/status")
    async def get_queue_status():
        """Get queue status"""
        from src.queue.queue_manager import get_queue_manager
        manager = get_queue_manager()
        items = await manager.get_queue_status(limit=10)
        return {"items": items}
    
    @app.get("/channels")
    async def get_channels():
        """Get channel information"""
        from src.matchers.channel_matcher import get_channel_matcher
        matcher = get_channel_matcher()
        channel_stats = await matcher.balance_channel_load()
        return channel_stats
    
    @app.get("/history/recent")
    async def get_recent_history(limit: int = 5):
        """Get recent upload history"""
        from src.utils.database import get_db_manager
        db = get_db_manager()
        
        query = """
        SELECT 
            h.*,
            c.channel_name
        FROM upload_history h
        LEFT JOIN youtube_channels c ON h.channel_id = c.id
        ORDER BY h.upload_time DESC
        LIMIT %s
        """
        
        result = await db.execute_query(query, (limit,))
        return {"items": result.data if result else []}

def setup_exception_handlers(app: FastAPI):
    """Setup global exception handlers"""
    
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request, exc):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.detail,
                "status_code": exc.status_code
            }
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request, exc):
        logger.error(f"Unhandled exception: {exc}")
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "detail": str(exc) if settings.debug_mode else "An error occurred"
            }
        )

def setup_events(app: FastAPI):
    """Setup startup and shutdown events"""
    
    @app.on_event("startup")
    async def startup_event():
        logger.info("API server starting...")
        # Initialize database connection
        from src.utils.database import get_db_manager
        db = get_db_manager()
        # Consider both Supabase REST and direct Postgres DSN
        try:
            pg_ok = await db.test_connection()
        except Exception:
            pg_ok = False
        if db.client or pg_ok:
            logger.info("✅ Database connected")
        else:
            logger.warning("⚠️ Database not connected")
    
    @app.on_event("shutdown")
    async def shutdown_event():
        logger.info("API server shutting down...")

async def start_server(app: FastAPI, host: str, port: int):
    """Start the uvicorn server"""
    config = uvicorn.Config(
        app=app,
        host=host,
        port=port,
        log_level="debug" if settings.debug_mode else "info",
        # Important: programmatic reload is unstable; keep False here
        reload=False
    )
    server = uvicorn.Server(config)
    await server.serve()

# Create default app instance
app = create_app()
