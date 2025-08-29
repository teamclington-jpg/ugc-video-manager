#!/usr/bin/env python3
"""
Supabase Database Setup Script
Run this to create all necessary tables and functions
"""

import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from supabase import create_client, Client
from src.config import settings
import asyncio

def get_supabase_client() -> Client:
    """Get Supabase client with service role key"""
    return create_client(
        settings.supabase_url,
        settings.supabase_service_key  # Use service key for admin operations
    )

async def create_tables():
    """Create all database tables"""
    
    client = get_supabase_client()
    
    # SQL statements for table creation
    sql_statements = [
        # Enable UUID extension
        """
        CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
        """,
        
        # youtube_channels table
        """
        CREATE TABLE IF NOT EXISTS youtube_channels (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            channel_name VARCHAR(255) NOT NULL,
            channel_url VARCHAR(500) NOT NULL,
            channel_type VARCHAR(10) NOT NULL CHECK (channel_type IN ('main', 'sub')),
            parent_channel_id UUID REFERENCES youtube_channels(id) ON DELETE SET NULL,
            category VARCHAR(100) NOT NULL,
            description TEXT,
            account_id VARCHAR(255) NOT NULL,
            account_password TEXT NOT NULL,
            infocrlink_url VARCHAR(500),
            max_daily_uploads INT DEFAULT 3,
            is_active BOOLEAN DEFAULT true,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        """,
        
        # Indexes for youtube_channels
        """
        CREATE INDEX IF NOT EXISTS idx_channel_category ON youtube_channels(category);
        CREATE INDEX IF NOT EXISTS idx_channel_active ON youtube_channels(is_active);
        CREATE INDEX IF NOT EXISTS idx_channel_type ON youtube_channels(channel_type);
        CREATE INDEX IF NOT EXISTS idx_parent_channel ON youtube_channels(parent_channel_id);
        """,
        
        # upload_queue table
        """
        CREATE TABLE IF NOT EXISTS upload_queue (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            video_file_path TEXT NOT NULL,
            video_file_name VARCHAR(500) NOT NULL,
            file_size_mb DECIMAL(10,2),
            channel_id UUID REFERENCES youtube_channels(id) ON DELETE SET NULL,
            title VARCHAR(500) NOT NULL,
            description TEXT NOT NULL,
            tags TEXT[],
            coupang_url VARCHAR(1000),
            infocrlink_data JSONB,
            status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'ready', 'uploaded', 'failed')),
            priority INT DEFAULT 50,
            scheduled_time TIMESTAMP WITH TIME ZONE,
            error_message TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        """,
        
        # Indexes for upload_queue
        """
        CREATE INDEX IF NOT EXISTS idx_queue_status ON upload_queue(status);
        CREATE INDEX IF NOT EXISTS idx_queue_priority ON upload_queue(priority DESC);
        CREATE INDEX IF NOT EXISTS idx_queue_scheduled ON upload_queue(scheduled_time);
        CREATE INDEX IF NOT EXISTS idx_queue_channel ON upload_queue(channel_id);
        CREATE INDEX IF NOT EXISTS idx_queue_created ON upload_queue(created_at DESC);
        """,
        
        # upload_history table
        """
        CREATE TABLE IF NOT EXISTS upload_history (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            queue_id UUID REFERENCES upload_queue(id) ON DELETE SET NULL,
            channel_id UUID REFERENCES youtube_channels(id) ON DELETE SET NULL,
            video_file_name VARCHAR(500) NOT NULL,
            upload_time TIMESTAMP WITH TIME ZONE NOT NULL,
            youtube_video_id VARCHAR(100),
            youtube_video_url VARCHAR(500),
            views_count INT DEFAULT 0,
            likes_count INT DEFAULT 0,
            comments_count INT DEFAULT 0,
            revenue_data JSONB,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        """,
        
        # Indexes for upload_history
        """
        CREATE INDEX IF NOT EXISTS idx_history_channel ON upload_history(channel_id);
        CREATE INDEX IF NOT EXISTS idx_history_date ON upload_history(upload_time);
        CREATE INDEX IF NOT EXISTS idx_history_queue ON upload_history(queue_id);
        """,
        
        # channel_upload_limits table
        """
        CREATE TABLE IF NOT EXISTS channel_upload_limits (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            channel_id UUID REFERENCES youtube_channels(id) ON DELETE CASCADE,
            upload_date DATE NOT NULL,
            upload_count INT DEFAULT 0,
            last_upload_time TIMESTAMP WITH TIME ZONE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            UNIQUE(channel_id, upload_date)
        );
        """,
        
        # Indexes for channel_upload_limits
        """
        CREATE INDEX IF NOT EXISTS idx_limits_date ON channel_upload_limits(upload_date);
        CREATE INDEX IF NOT EXISTS idx_limits_channel_date ON channel_upload_limits(channel_id, upload_date);
        """,
        
        # infocrlink_mapping table
        """
        CREATE TABLE IF NOT EXISTS infocrlink_mapping (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            channel_id UUID REFERENCES youtube_channels(id) ON DELETE CASCADE,
            infocrlink_url VARCHAR(500) NOT NULL,
            infocrlink_type VARCHAR(100),
            commission_rate DECIMAL(5,2),
            is_active BOOLEAN DEFAULT true,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        """,
        
        # Indexes for infocrlink_mapping
        """
        CREATE INDEX IF NOT EXISTS idx_infocrlink_channel ON infocrlink_mapping(channel_id);
        CREATE INDEX IF NOT EXISTS idx_infocrlink_active ON infocrlink_mapping(is_active);
        """,
        
        # video_analysis_cache table
        """
        CREATE TABLE IF NOT EXISTS video_analysis_cache (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            video_file_hash VARCHAR(64) NOT NULL UNIQUE,
            video_file_name VARCHAR(500) NOT NULL,
            analysis_result JSONB NOT NULL,
            gemini_response JSONB,
            extracted_products TEXT[],
            detected_category VARCHAR(100),
            keywords TEXT[],
            confidence_score DECIMAL(3,2),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            expires_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() + INTERVAL '7 days'
        );
        """,
        
        # Indexes for video_analysis_cache
        """
        CREATE INDEX IF NOT EXISTS idx_analysis_hash ON video_analysis_cache(video_file_hash);
        CREATE INDEX IF NOT EXISTS idx_analysis_expires ON video_analysis_cache(expires_at);
        """
    ]
    
    # Execute SQL statements
    for i, sql in enumerate(sql_statements, 1):
        try:
            # Use RPC to execute raw SQL
            # Note: This requires enabling the SQL Editor in Supabase Dashboard
            print(f"Executing statement {i}/{len(sql_statements)}...")
            
            # For Supabase Python client, we need to use the REST API
            # Tables will be created via Supabase Dashboard SQL Editor
            
        except Exception as e:
            print(f"Error executing statement {i}: {e}")
            print(f"SQL: {sql[:100]}...")

async def create_functions():
    """Create database functions"""
    
    functions_sql = [
        # Function to update updated_at timestamp
        """
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ language 'plpgsql';
        """,
        
        # Function to check channel upload limits
        """
        CREATE OR REPLACE FUNCTION check_channel_upload_limit(p_channel_id UUID)
        RETURNS BOOLEAN AS $$
        DECLARE
            v_count INT;
            v_max_uploads INT;
        BEGIN
            SELECT max_daily_uploads INTO v_max_uploads
            FROM youtube_channels
            WHERE id = p_channel_id AND is_active = true;
            
            IF v_max_uploads IS NULL THEN
                RETURN false;
            END IF;
            
            SELECT upload_count INTO v_count
            FROM channel_upload_limits
            WHERE channel_id = p_channel_id
            AND upload_date = CURRENT_DATE;
            
            IF v_count IS NULL THEN
                v_count := 0;
            END IF;
            
            RETURN v_count < v_max_uploads;
        END;
        $$ LANGUAGE plpgsql;
        """,
        
        # Function to increment upload count
        """
        CREATE OR REPLACE FUNCTION increment_upload_count(p_channel_id UUID)
        RETURNS VOID AS $$
        BEGIN
            INSERT INTO channel_upload_limits (channel_id, upload_date, upload_count, last_upload_time)
            VALUES (p_channel_id, CURRENT_DATE, 1, NOW())
            ON CONFLICT (channel_id, upload_date)
            DO UPDATE SET 
                upload_count = channel_upload_limits.upload_count + 1,
                last_upload_time = NOW();
        END;
        $$ LANGUAGE plpgsql;
        """
    ]
    
    print("\n📝 Functions SQL generated")
    return functions_sql

async def create_views():
    """Create database views"""
    
    views_sql = [
        # View for available channels
        """
        CREATE OR REPLACE VIEW available_channels AS
        SELECT 
            c.*,
            COALESCE(l.upload_count, 0) as today_uploads,
            c.max_daily_uploads - COALESCE(l.upload_count, 0) as remaining_uploads
        FROM youtube_channels c
        LEFT JOIN channel_upload_limits l 
            ON c.id = l.channel_id 
            AND l.upload_date = CURRENT_DATE
        WHERE c.is_active = true
            AND (l.upload_count IS NULL OR l.upload_count < c.max_daily_uploads);
        """,
        
        # View for queue status overview
        """
        CREATE OR REPLACE VIEW queue_status_overview AS
        SELECT 
            status,
            COUNT(*) as count,
            MIN(created_at) as oldest_item,
            MAX(created_at) as newest_item
        FROM upload_queue
        GROUP BY status;
        """,
        
        # View for channel statistics
        """
        CREATE OR REPLACE VIEW channel_statistics AS
        SELECT 
            c.id,
            c.channel_name,
            c.channel_type,
            COUNT(DISTINCT h.id) as total_uploads,
            COUNT(DISTINCT CASE WHEN h.upload_time > NOW() - INTERVAL '7 days' THEN h.id END) as uploads_last_7_days,
            COUNT(DISTINCT CASE WHEN h.upload_time > NOW() - INTERVAL '30 days' THEN h.id END) as uploads_last_30_days,
            SUM(h.views_count) as total_views,
            SUM(h.likes_count) as total_likes,
            AVG(h.views_count) as avg_views_per_video
        FROM youtube_channels c
        LEFT JOIN upload_history h ON c.id = h.channel_id
        GROUP BY c.id, c.channel_name, c.channel_type;
        """
    ]
    
    print("📊 Views SQL generated")
    return views_sql

def generate_full_sql():
    """Generate complete SQL script"""
    
    print("""
╔══════════════════════════════════════════════════╗
║      Supabase Database Setup Script             ║
║                                                  ║
║  이 SQL을 Supabase Dashboard에서 실행하세요:    ║
║  1. Supabase Dashboard 접속                      ║
║  2. SQL Editor 탭 클릭                          ║
║  3. 아래 SQL 복사하여 붙여넣기                  ║
║  4. Run 버튼 클릭                               ║
╚══════════════════════════════════════════════════╝
    """)
    
    # Create output file with all SQL
    output_file = Path(__file__).parent / "complete_setup.sql"
    
    with open(output_file, "w") as f:
        f.write("-- UGC Video Manager - Complete Database Setup\n")
        f.write("-- Generated SQL for Supabase\n\n")
        
        # Read from setup_database.sql if exists
        setup_file = Path(__file__).parent / "setup_database.sql"
        if setup_file.exists():
            with open(setup_file, "r") as setup:
                f.write(setup.read())
        else:
            f.write("-- Original setup_database.sql not found\n")
            f.write("-- Using generated SQL\n\n")
            
            # Generate basic SQL here
            f.write("""
-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Tables creation SQL goes here
-- (Copy from setup_database.sql)
            """)
    
    print(f"\n✅ SQL 파일 생성됨: {output_file}")
    print("\n이 파일을 Supabase SQL Editor에 복사하여 실행하세요!")
    
    return str(output_file)

async def test_connection():
    """Test Supabase connection"""
    try:
        client = get_supabase_client()
        
        # Try to query a simple table
        response = client.table('youtube_channels').select("*").limit(1).execute()
        
        print("✅ Supabase 연결 성공!")
        return True
        
    except Exception as e:
        print(f"❌ Supabase 연결 실패: {e}")
        print("\n다음을 확인하세요:")
        print("1. .env 파일의 SUPABASE_URL")
        print("2. .env 파일의 SUPABASE_SERVICE_KEY")
        print("3. Supabase 프로젝트가 활성 상태인지")
        return False

async def insert_sample_data():
    """Insert sample data for testing"""
    
    client = get_supabase_client()
    
    sample_channels = [
        {
            "channel_name": "메인채널",
            "channel_url": "https://youtube.com/@mainchannel",
            "channel_type": "main",
            "category": "technology",
            "description": "기술 리뷰 메인 채널",
            "account_id": "encrypted_id_1",
            "account_password": "encrypted_pass_1",
            "max_daily_uploads": 3
        },
        {
            "channel_name": "게임채널",
            "channel_url": "https://youtube.com/@gamechannel",
            "channel_type": "main",
            "category": "gaming",
            "description": "게임 콘텐츠 채널",
            "account_id": "encrypted_id_2",
            "account_password": "encrypted_pass_2",
            "max_daily_uploads": 3
        },
        {
            "channel_name": "주부채널",
            "channel_url": "https://youtube.com/@lifestylechannel",
            "channel_type": "main",
            "category": "lifestyle",
            "description": "라이프스타일 채널",
            "account_id": "encrypted_id_3",
            "account_password": "encrypted_pass_3",
            "max_daily_uploads": 3
        }
    ]
    
    try:
        for channel in sample_channels:
            response = client.table('youtube_channels').insert(channel).execute()
            print(f"✅ 샘플 채널 추가됨: {channel['channel_name']}")
    except Exception as e:
        print(f"샘플 데이터 추가 중 오류: {e}")

def main():
    """Main execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Supabase Database Setup")
    parser.add_argument("--test", action="store_true", help="Test connection only")
    parser.add_argument("--generate-sql", action="store_true", help="Generate SQL file")
    parser.add_argument("--sample-data", action="store_true", help="Insert sample data")
    
    args = parser.parse_args()
    
    if args.test:
        asyncio.run(test_connection())
    elif args.generate_sql:
        generate_full_sql()
    elif args.sample_data:
        asyncio.run(insert_sample_data())
    else:
        # Default: generate SQL
        sql_file = generate_full_sql()
        
        print("\n다음 단계:")
        print("1. Supabase Dashboard (https://app.supabase.com) 접속")
        print("2. 프로젝트 선택")
        print("3. SQL Editor 클릭")
        print(f"4. {sql_file} 파일 내용 복사하여 붙여넣기")
        print("5. Run 버튼 클릭")
        
        # Test connection
        print("\n연결 테스트 중...")
        asyncio.run(test_connection())

if __name__ == "__main__":
    main()