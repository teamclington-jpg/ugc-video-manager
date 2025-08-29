"""
Admin endpoints for managing channels, queue, and utilities
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import csv
from pathlib import Path

from src.utils.database import get_db_manager
from src.utils.logger import get_logger
from src.matchers.product_matcher import get_product_matcher
from src.processors.video_processor import get_video_processor

router = APIRouter()
logger = get_logger("admin")


class ChannelUpdate(BaseModel):
    channel_name: Optional[str] = None
    channel_type: Optional[str] = Field(None, pattern="^(main|sub)$")
    parent_channel_id: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    max_daily_uploads: Optional[int] = Field(None, ge=1, le=20)
    is_active: Optional[bool] = None


class ChannelCreate(ChannelUpdate):
    channel_name: str
    channel_url: str
    account_id: str
    account_password: str


@router.get("/channels")
async def list_channels_all():
    db = get_db_manager()
    try:
        channels = await db.list_channels_all()
        # Clean up channels data for API response
        cleaned_channels = []
        for ch in channels:
            # Ensure all required fields exist with defaults
            cleaned_ch = {
                "id": ch.get("id"),
                "channel_name": ch.get("channel_name", "Unknown"),
                "channel_url": ch.get("channel_url", ""),
                "channel_type": ch.get("channel_type", "main"),
                "category": ch.get("category", "general"),
                "description": ch.get("description", ""),
                "account_id": ch.get("account_id", ""),
                "max_daily_uploads": ch.get("max_daily_uploads", 3),
                "is_active": ch.get("is_active", True),
                "infocrlink_url": ch.get("infocrlink_url", ""),
                "created_at": ch.get("created_at", ""),
                "updated_at": ch.get("updated_at", "")
            }
            cleaned_channels.append(cleaned_ch)
        return cleaned_channels
    except Exception as e:
        logger.error(f"Error listing channels: {e}")
        # Return empty array instead of error to keep UI working
        return []


@router.post("/channels")
async def create_channel(channel: ChannelCreate):
    db = get_db_manager()
    try:
        rec = await db.create_channel(channel.dict())
        if not rec:
            raise HTTPException(status_code=500, detail="Failed to create channel")
        return rec
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating channel: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/channels/{channel_id}")
async def update_channel(channel_id: str, updates: ChannelUpdate):
    db = get_db_manager()
    try:
        data = {k: v for k, v in updates.dict().items() if v is not None}
        if not data:
            return await db.get_channel(channel_id)
        rec = await db.update_channel(channel_id, data)
        if not rec:
            raise HTTPException(status_code=404, detail="Channel not found or update failed")
        return rec
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating channel {channel_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class AssignRequest(BaseModel):
    channel_id: str
    keep_status: bool = False


@router.post("/queue/{queue_id}/assign")
async def assign_queue_item(queue_id: str, payload: AssignRequest):
    db = get_db_manager()
    try:
        updates = {"channel_id": payload.channel_id}
        if not payload.keep_status:
            updates["status"] = "pending"
        rec = await db.update_queue_item(queue_id, updates)
        if not rec:
            raise HTTPException(status_code=404, detail="Queue item not found")
        return rec
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error assigning queue item {queue_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class InfocrlinkRequest(BaseModel):
    coupang_url: str
    channel_id: str


@router.post("/queue/{queue_id}/infocrlink")
async def generate_infocrlink(queue_id: str, payload: InfocrlinkRequest):
    db = get_db_manager()
    matcher = get_product_matcher()
    try:
        link = await matcher.generate_infocrlink(payload.coupang_url, payload.channel_id)
        rec = await db.update_queue_item(queue_id, {"coupang_url": payload.coupang_url, "infocrlink_data": {"url": link}})
        if not rec:
            raise HTTPException(status_code=404, detail="Queue item not found")
        return {"queue_id": queue_id, "infocrlink": link}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating infocrlink for {queue_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

class ProcessVideoRequest(BaseModel):
    video_path: str
    channel_hint: Optional[str] = None

@router.post("/process-video")
async def admin_process_video(req: ProcessVideoRequest):
    """Trigger processing for a specific video path (admin utility)."""
    try:
        processor = get_video_processor()
        result = await processor.process_video(req.video_path, channel_hint=req.channel_hint)
        return result
    except Exception as e:
        logger.error(f"Admin process-video error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

class ImportChannelsRequest(BaseModel):
    csv_path: str = Field(..., description="Absolute path to CSV file")
    delimiter: str = Field(default=",", description="CSV delimiter")
    encoding: str = Field(default="utf-8-sig", description="File encoding")
    update_if_exists: bool = True
    preview: bool = False

@router.post("/import-channels")
async def import_channels(req: ImportChannelsRequest):
    """Import channels from a CSV file on disk.

    Expected columns (case-insensitive, flexible):
    - channel_name (or 채널명)
    - channel_url (or URL)
    - channel_type (main/sub or 메인/서브)
    - category (or 카테고리)
    - description (or 설명)
    - max_daily_uploads (or 일일업로드, 업로드제한)
    - is_active (true/false, Y/N, 활성/비활성)
    - infocrlink_url (or 인포크링크)
    - account_id, account_password (optional)
    """
    db = get_db_manager()
    p = Path(req.csv_path)
    if not p.exists():
        raise HTTPException(status_code=404, detail="CSV file not found")

    def norm(s: str) -> str:
        return (s or '').strip().lower()

    def map_bool(v: str) -> bool:
        t = norm(v)
        return t in ("true", "1", "y", "yes", "활성", "사용", "on")

    def map_type(v: str) -> str:
        t = norm(v)
        if t in ("main", "메인", "주", "primary"):
            return "main"
        if t in ("sub", "서브", "부", "secondary"):
            return "sub"
        return "sub"

    imported = 0
    updated = 0
    errors: List[Dict[str, Any]] = []
    preview_rows: List[Dict[str, Any]] = []

    try:
        with open(p, "r", encoding=req.encoding, newline="") as f:
            reader = csv.DictReader(f, delimiter=req.delimiter)
            headers = [h for h in (reader.fieldnames or [])]

            # Normalize header mapping
            def get(row: Dict[str, str], *keys: str) -> str:
                for key in keys:
                    if key in row:
                        return row.get(key) or ""
                    # try case-insensitive lookup
                    for rk in row.keys():
                        if rk.lower().strip() == key.lower().strip():
                            return row.get(rk) or ""
                return ""

            for idx, row in enumerate(reader):
                try:
                    payload = {
                        "channel_name": get(row, "channel_name", "채널명").strip(),
                        "channel_url": get(row, "channel_url", "url", "채널url").strip(),
                        "channel_type": map_type(get(row, "channel_type", "채널타입", "타입")),
                        "parent_channel_id": None,
                        "category": get(row, "category", "카테고리").strip() or "lifestyle",
                        "description": get(row, "description", "설명").strip(),
                        "account_id": get(row, "account_id", "아이디").strip() or "imported",
                        "account_password": get(row, "account_password", "비밀번호").strip() or "imported",
                        "max_daily_uploads": int((get(row, "max_daily_uploads", "일일업로드", "업로드제한") or "3").strip()),
                        "is_active": map_bool(get(row, "is_active", "활성")),
                    }
                    infocrlink_url = get(row, "infocrlink_url", "인포크링크").strip()
                    if infocrlink_url:
                        payload["infocrlink_url"] = infocrlink_url

                    if req.preview:
                        preview_rows.append(payload)
                        continue

                    name = payload["channel_name"]
                    if not name:
                        raise ValueError("Missing channel_name")

                    # Upsert by channel_name
                    existing = await db.get_channel_by_name(name)
                    if existing and req.update_if_exists:
                        updated_rec = await db.update_channel(existing['id'], payload)
                        if updated_rec:
                            updated += 1
                        else:
                            raise RuntimeError("Update failed")
                    else:
                        rec = await db.create_channel(payload)
                        if rec:
                            imported += 1
                        else:
                            raise RuntimeError("Insert failed")
                except Exception as e:
                    errors.append({"row": idx + 1, "error": str(e)})

        result = {
            "imported": imported,
            "updated": updated,
            "errors": errors,
            "preview": preview_rows if req.preview else None,
            "headers": headers,
            "total_rows": len(preview_rows) if req.preview else (imported + updated + len(errors))
        }
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error importing channels: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/diagnostics")
async def diagnostics():
    """Quick connectivity and configuration diagnostics."""
    db = get_db_manager()
    info: Dict[str, Any] = {
        "supabase_url": getattr(db, 'client', None) is not None,
        "pg_dsn_present": bool(getattr(db, 'pg_dsn', None)),
    }
    # Try a lightweight Supabase call
    try:
        if db.client:
            res = db.client.table('upload_queue').select("id").limit(1).execute()
            info["supabase_select_ok"] = True
            info["upload_queue_rows_sample"] = len(res.data or [])
        else:
            info["supabase_select_ok"] = False
    except Exception as e:
        info["supabase_select_ok"] = False
        info["supabase_error"] = str(e)

    # Test Postgres DSN connectivity
    try:
        ok = await db.test_connection()
        info["pg_dsn_connect_ok"] = ok
    except Exception as e:
        info["pg_dsn_connect_ok"] = False
        info["pg_error"] = str(e)

    return info
