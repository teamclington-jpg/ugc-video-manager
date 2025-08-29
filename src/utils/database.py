"""
Database connection and utilities supporting Supabase and direct Postgres SQL.

Provides a unified async API used across the app:
- execute_query: run raw SQL (uses psycopg2 under the hood if DSN is provided)
- test_connection: check DB connectivity
- transaction: async context manager for transactional operations

Falls back gracefully in development when DB is not configured.
"""

from typing import Optional, Dict, Any, List
from types import SimpleNamespace
from contextlib import asynccontextmanager
import os
import asyncio
from datetime import datetime, timedelta

from supabase import create_client, Client
import psycopg2
from psycopg2.extras import RealDictCursor
import socket
from urllib.parse import urlparse

from src.config import settings
from src.utils.encryption import get_encryption_manager

class DatabaseManager:
    """Manages Supabase database operations"""
    
    def __init__(self):
        """Initialize Supabase client"""
        self.client: Optional[Client] = None
        # Optional direct Postgres connection string for raw SQL
        self.pg_dsn: Optional[str] = (
            os.getenv("SUPABASE_DB_URL")
            or os.getenv("DATABASE_URL")
            or os.getenv("POSTGRES_URL")
        )
        # Transaction-scoped connection (async context)
        self._tx_conn = None
        self.encryption = get_encryption_manager()
        # In-memory fallback stores (development without DB)
        self._memory_enabled = not bool(self.pg_dsn)
        self._mem_queue: Dict[str, Dict[str, Any]] = {}
        self._mem_channels: Dict[str, Dict[str, Any]] = {}
        self._mem_history: List[Dict[str, Any]] = []
        self._mem_analysis_cache: Dict[str, Dict[str, Any]] = {}
        self._mem_channel_uploads: Dict[str, int] = {}
        self._connect()
    
    def _connect(self):
        """Create Supabase client connection"""
        # Always use Supabase REST API client if available
        try:
            if settings.supabase_url and settings.supabase_anon_key:
                self.client = create_client(
                    settings.supabase_url,
                    settings.supabase_anon_key
                )
                print("✅ Connected to Supabase REST API")
                # Disable DSN for now to avoid connection errors
                self.pg_dsn = None
            else:
                self.client = None
                print("⚠️  No Supabase credentials configured")
        except Exception as e:
            # Graceful fallback if library/env mismatch
            self.client = None
            self.pg_dsn = None
            print(f"⚠️  Supabase client init failed: {e}. Falling back to in-memory store.")

    async def test_connection(self) -> bool:
        """Test database connectivity (Postgres DSN if available)."""
        if not self.pg_dsn:
            # No DSN configured
            return False
        try:
            def _probe():
                conn = psycopg2.connect(self.pg_dsn)
                conn.close()
                return True
            return await asyncio.to_thread(_probe)
        except Exception:
            return False

    async def execute_query(self, query: str, params: Optional[tuple] = None):
        """
        Execute a SQL query using psycopg2.
        Returns an object with .data (list[dict]) and .rowcount (int).
        In development without DB, returns empty result to keep app running.
        """
        if not self.pg_dsn:
            # Graceful fallback: return empty result
            return SimpleNamespace(data=[], rowcount=0)

        def _run_query():
            # Use transaction-scoped connection if present
            conn = self._tx_conn or psycopg2.connect(self.pg_dsn)
            try:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(query, params or ())
                    rows = cur.fetchall() if cur.description else []
                    rowcount = cur.rowcount
                if not self._tx_conn:
                    conn.commit()
                return SimpleNamespace(data=list(rows), rowcount=rowcount)
            finally:
                if not self._tx_conn:
                    conn.close()

        return await asyncio.to_thread(_run_query)

    @asynccontextmanager
    async def transaction(self):
        """Async transaction context manager for multi-statement operations."""
        if not self.pg_dsn:
            # No-op transaction for development
            yield
            return
        conn = None
        try:
            def _open():
                return psycopg2.connect(self.pg_dsn)
            conn = await asyncio.to_thread(_open)
            conn.autocommit = False
            self._tx_conn = conn
            yield
            await asyncio.to_thread(conn.commit)
        except Exception as e:
            if conn:
                await asyncio.to_thread(conn.rollback)
            raise e
        finally:
            if conn:
                await asyncio.to_thread(conn.close)
            self._tx_conn = None
    
    # Channel Operations
    async def create_channel(self, channel_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new YouTube channel entry"""
        # For now, skip encryption to avoid issues with existing data
        # We'll re-enable this once we ensure all data is properly handled
        encrypted_data = channel_data.copy()
        
        # Postgres path
        if self.pg_dsn:
            keys = [
                'channel_name','channel_url','channel_type','parent_channel_id','category',
                'description','account_id','account_password','max_daily_uploads','is_active','infocrlink_url'
            ]
            cols = []
            vals = []
            params = []
            for k in keys:
                if k in encrypted_data and encrypted_data[k] is not None:
                    cols.append(k)
                    vals.append('%s')
                    params.append(encrypted_data[k])
            query = f"INSERT INTO youtube_channels ({', '.join(cols)}) VALUES ({', '.join(vals)}) RETURNING *"
            result = await self.execute_query(query, tuple(params))
            return result.data[0] if result and result.data else None
        # Supabase path
        if self.client:
            result = self.client.table('youtube_channels').insert(encrypted_data).execute()
            return result.data[0] if result.data else None
        # In-memory fallback
        import uuid
        channel_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        record = {
            **encrypted_data,
            'id': channel_id,
            'is_active': True,
            'max_daily_uploads': encrypted_data.get('max_daily_uploads', 3),
            'created_at': now,
            'updated_at': now
        }
        self._mem_channels[channel_id] = record
        return record
    
    async def get_channel(self, channel_id: str) -> Dict[str, Any]:
        """Get channel by ID"""
        if self.pg_dsn:
            query = "SELECT * FROM youtube_channels WHERE id = %s"
            result = await self.execute_query(query, (channel_id,))
            if result.data:
                return result.data[0]
            return None
        if self.client:
            result = self.client.table('youtube_channels').select("*").eq('id', channel_id).execute()
            if result.data:
                return self.encryption.decrypt_dict(
                    result.data[0],
                    ['account_id', 'account_password']
                )
            return None
        # Memory
        return self._mem_channels.get(channel_id)

    async def get_channel_by_name(self, channel_name: str) -> Optional[Dict[str, Any]]:
        """Get channel by name"""
        if self.pg_dsn:
            query = "SELECT * FROM youtube_channels WHERE channel_name = %s LIMIT 1"
            result = await self.execute_query(query, (channel_name,))
            return result.data[0] if result and result.data else None
        if self.client:
            result = self.client.table('youtube_channels').select("*").eq('channel_name', channel_name).limit(1).execute()
            if result.data:
                return self.encryption.decrypt_dict(result.data[0], ['account_id', 'account_password'])
            return None
        # Memory
        for ch in self._mem_channels.values():
            if ch.get('channel_name') == channel_name:
                return ch
        return None
    async def list_channels_all(self) -> List[Dict[str, Any]]:
        """List all channels (active and inactive)."""
        if self.pg_dsn:
            query = "SELECT * FROM youtube_channels ORDER BY channel_name"
            result = await self.execute_query(query)
            return result.data if result else []
        if self.client:
            result = self.client.table('youtube_channels').select("*").order('channel_name').execute()
            return [
                self.encryption.decrypt_dict(r, ['account_id', 'account_password'])
                for r in (result.data or [])
            ]
        return list(self._mem_channels.values())

    async def update_channel(self, channel_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update channel fields"""
        if self.pg_dsn:
            # Simplified; build dynamic SQL
            set_clause = ", ".join([f"{k} = %s" for k in updates.keys()])
            params = list(updates.values()) + [channel_id]
            query = f"UPDATE youtube_channels SET {set_clause}, updated_at = NOW() WHERE id = %s RETURNING *"
            result = await self.execute_query(query, tuple(params))
            return result.data[0] if result and result.data else None
        if self.client:
            # Skip encryption for now
            result = self.client.table('youtube_channels').update(updates).eq('id', channel_id).execute()
            return result.data[0] if result.data else None
        # Memory
        rec = self._mem_channels.get(channel_id)
        if not rec:
            return None
        rec.update(updates)
        self._mem_channels[channel_id] = rec
        return rec
    
    async def get_available_channels(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get channels that haven't reached upload limit"""
        if self.client:
            # Get all active channels first
            query = self.client.table('youtube_channels').select("*").eq('is_active', True)
            if category:
                query = query.eq('category', category)
            result = query.execute()
            
            channels = []
            for channel in result.data:
                # Get today's upload count for this channel
                today = datetime.now().date().isoformat()
                upload_result = self.client.table('channel_upload_limits').select("upload_count").eq('channel_id', channel['id']).eq('upload_date', today).execute()
                today_uploads = upload_result.data[0]['upload_count'] if upload_result.data else 0
                
                # Check if channel is available
                max_uploads = channel.get('max_daily_uploads', 3)
                if today_uploads < max_uploads:
                    decrypted = self.encryption.decrypt_dict(
                        channel,
                        ['account_id', 'account_password']
                    )
                    decrypted['today_uploads'] = today_uploads
                    decrypted['remaining_uploads'] = max_uploads - today_uploads
                    channels.append(decrypted)
            return channels
        
        # Memory fallback
        items = list(self._mem_channels.values())
        if category:
            items = [c for c in items if c.get('category') == category]
        # compute uploads today
        for c in items:
            c['today_uploads'] = self._mem_channel_uploads.get(c['id'], 0)
        return items
    
    # Queue Operations
    async def add_to_queue(self, queue_item: Dict[str, Any]) -> Dict[str, Any]:
        """Add item to upload queue"""
        if self.pg_dsn:
            # Not implemented: prefer high-level QueueManager SQL path
            return None
        if self.client:
            result = self.client.table('upload_queue').insert(queue_item).execute()
            return result.data[0] if result.data else None
        # Memory
        import uuid
        now = datetime.now().isoformat()
        qid = str(uuid.uuid4())
        record = {
            'id': qid,
            'status': 'pending',
            'created_at': now,
            'updated_at': now,
            'error_message': None,
            **queue_item
        }
        self._mem_queue[qid] = record
        return record
    
    async def get_queue_items(self, status: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Get items from upload queue"""
        if self.pg_dsn:
            return []
        if self.client:
            query = self.client.table('upload_queue').select("*")
            if status:
                query = query.eq('status', status)
            query = query.order('priority', desc=True).limit(limit)
            result = query.execute()
            return result.data
        # Memory
        items = list(self._mem_queue.values())
        if status:
            items = [i for i in items if i.get('status') == status]
        items.sort(key=lambda x: (-int(x.get('priority', 0)), x.get('created_at', '')))
        return items[:limit]
    
    async def update_queue_item(self, queue_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update queue item status"""
        updates['updated_at'] = datetime.now().isoformat()
        if self.pg_dsn:
            return None
        if self.client:
            result = self.client.table('upload_queue').update(updates).eq('id', queue_id).execute()
            return result.data[0] if result.data else None
        # Memory
        rec = self._mem_queue.get(queue_id)
        if not rec:
            return None
        rec.update(updates)
        self._mem_queue[queue_id] = rec
        return rec
    
    # Upload Limit Operations
    async def check_channel_limit(self, channel_id: str) -> bool:
        """Check if channel can upload more videos today"""
        if self.pg_dsn:
            return True
        if self.client:
            result = self.client.rpc('check_channel_upload_limit', {'p_channel_id': channel_id}).execute()
            return result.data if result.data is not None else False
        # Memory: simple limit check
        max_daily = self._mem_channels.get(channel_id, {}).get('max_daily_uploads', 3)
        used = self._mem_channel_uploads.get(channel_id, 0)
        return used < max_daily
    
    async def increment_upload_count(self, channel_id: str):
        """Increment upload count for channel"""
        if self.pg_dsn:
            return
        if self.client:
            self.client.rpc('increment_upload_count', {'p_channel_id': channel_id}).execute()
            return
        self._mem_channel_uploads[channel_id] = self._mem_channel_uploads.get(channel_id, 0) + 1
    
    # History Operations
    async def record_upload(self, upload_data: Dict[str, Any]) -> Dict[str, Any]:
        """Record successful upload in history"""
        if self.pg_dsn:
            return None
        if self.client:
            result = self.client.table('upload_history').insert(upload_data).execute()
            if upload_data.get('channel_id'):
                await self.increment_upload_count(upload_data['channel_id'])
            return result.data[0] if result.data else None
        # Memory
        self._mem_history.append(upload_data)
        if upload_data.get('channel_id'):
            await self.increment_upload_count(upload_data['channel_id'])
        return upload_data
    
    # Analysis Cache Operations
    async def get_cached_analysis(self, video_hash: str) -> Optional[Dict[str, Any]]:
        """Get cached video analysis if exists"""
        if self.pg_dsn:
            return None
        if self.client:
            result = self.client.table('video_analysis_cache').select("*").eq('video_file_hash', video_hash).execute()
            if result.data:
                cache_entry = result.data[0]
                expires_at = datetime.fromisoformat(cache_entry['expires_at'])
                if expires_at > datetime.now():
                    return cache_entry
            return None
        # Memory
        return self._mem_analysis_cache.get(video_hash)
    
    async def cache_analysis(self, video_hash: str, analysis_data: Dict[str, Any]) -> Dict[str, Any]:
        """Cache video analysis results"""
        cache_entry = {
            'video_file_hash': video_hash,
            'video_file_name': analysis_data.get('filename', ''),
            'analysis_result': analysis_data,
            'gemini_response': analysis_data.get('gemini_response'),
            'extracted_products': analysis_data.get('products', []),
            'detected_category': analysis_data.get('category'),
            'keywords': analysis_data.get('keywords', []),
            'confidence_score': analysis_data.get('confidence', 0.0),
            'expires_at': (datetime.now() + timedelta(days=7)).isoformat()
        }
        if self.pg_dsn:
            return cache_entry
        if self.client:
            result = self.client.table('video_analysis_cache').insert(cache_entry).execute()
            return result.data[0] if result.data else None
        # Memory
        self._mem_analysis_cache[video_hash] = cache_entry
        return cache_entry
    
    # Statistics Operations
    async def get_channel_statistics(self, channel_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get channel upload statistics"""
        if self.pg_dsn:
            return []
        if self.client:
            query = self.client.table('channel_statistics').select("*")
            if channel_id:
                query = query.eq('id', channel_id)
            result = query.execute()
            return result.data
        # Memory
        stats = []
        channels = [self._mem_channels.get(channel_id)] if channel_id else list(self._mem_channels.values())
        for ch in channels:
            if not ch:
                continue
            cid = ch['id']
            today = self._mem_channel_uploads.get(cid, 0)
            stats.append({
                'id': cid,
                'channel_name': ch.get('channel_name', ''),
                'max_daily_uploads': ch.get('max_daily_uploads', 3),
                'today_uploads': today,
                'remaining_uploads': ch.get('max_daily_uploads', 3) - today
            })
        return stats
    
    async def get_queue_overview(self) -> Dict[str, Any]:
        """Get queue status overview"""
        if self.pg_dsn:
            return {}
        if self.client:
            result = self.client.table('queue_status_overview').select("*").execute()
            overview = {}
            for item in result.data:
                overview[item['status']] = {
                    'count': item['count'],
                    'oldest': item['oldest_item'],
                    'newest': item['newest_item']
                }
            return overview
        # Memory
        from collections import defaultdict
        grouped = defaultdict(list)
        for rec in self._mem_queue.values():
            grouped[rec.get('status', 'pending')].append(rec)
        overview = {}
        for status, items in grouped.items():
            items_sorted = sorted(items, key=lambda x: x.get('created_at', ''))
            overview[status] = {
                'count': len(items),
                'oldest': items_sorted[0].get('created_at') if items_sorted else None,
                'newest': items_sorted[-1].get('created_at') if items_sorted else None
            }
        return overview

# Global database manager instance
_db_manager: Optional[DatabaseManager] = None

def get_db_manager() -> DatabaseManager:
    """Get or create global database manager"""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager
