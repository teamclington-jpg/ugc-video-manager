-- UGC Video Manager Database Setup Script
-- For Supabase PostgreSQL

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- 1. youtube_channels table
-- ============================================
DROP TABLE IF EXISTS youtube_channels CASCADE;
CREATE TABLE youtube_channels (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    channel_name VARCHAR(255) NOT NULL,
    channel_url VARCHAR(500) NOT NULL,
    channel_type VARCHAR(10) NOT NULL CHECK (channel_type IN ('main', 'sub')),
    parent_channel_id UUID REFERENCES youtube_channels(id) ON DELETE SET NULL,
    category VARCHAR(100) NOT NULL,
    description TEXT,
    account_id VARCHAR(255) NOT NULL,  -- 암호화 저장
    account_password TEXT NOT NULL,     -- 암호화 저장
    infocrlink_url VARCHAR(500),
    max_daily_uploads INT DEFAULT 3,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for youtube_channels
CREATE INDEX idx_channel_category ON youtube_channels(category);
CREATE INDEX idx_channel_active ON youtube_channels(is_active);
CREATE INDEX idx_channel_type ON youtube_channels(channel_type);
CREATE INDEX idx_parent_channel ON youtube_channels(parent_channel_id);

-- ============================================
-- 2. upload_queue table
-- ============================================
DROP TABLE IF EXISTS upload_queue CASCADE;
CREATE TABLE upload_queue (
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

-- Indexes for upload_queue
CREATE INDEX idx_queue_status ON upload_queue(status);
CREATE INDEX idx_queue_priority ON upload_queue(priority DESC);
CREATE INDEX idx_queue_scheduled ON upload_queue(scheduled_time);
CREATE INDEX idx_queue_channel ON upload_queue(channel_id);
CREATE INDEX idx_queue_created ON upload_queue(created_at DESC);

-- ============================================
-- 3. upload_history table
-- ============================================
DROP TABLE IF EXISTS upload_history CASCADE;
CREATE TABLE upload_history (
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

-- Indexes for upload_history
CREATE INDEX idx_history_channel ON upload_history(channel_id);
CREATE INDEX idx_history_date ON upload_history(upload_time);
CREATE INDEX idx_history_queue ON upload_history(queue_id);

-- ============================================
-- 4. channel_upload_limits table
-- ============================================
DROP TABLE IF EXISTS channel_upload_limits CASCADE;
CREATE TABLE channel_upload_limits (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    channel_id UUID REFERENCES youtube_channels(id) ON DELETE CASCADE,
    upload_date DATE NOT NULL,
    upload_count INT DEFAULT 0,
    last_upload_time TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(channel_id, upload_date)
);

-- Indexes for channel_upload_limits
CREATE INDEX idx_limits_date ON channel_upload_limits(upload_date);
CREATE INDEX idx_limits_channel_date ON channel_upload_limits(channel_id, upload_date);

-- ============================================
-- 5. infocrlink_mapping table
-- ============================================
DROP TABLE IF EXISTS infocrlink_mapping CASCADE;
CREATE TABLE infocrlink_mapping (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    channel_id UUID REFERENCES youtube_channels(id) ON DELETE CASCADE,
    infocrlink_url VARCHAR(500) NOT NULL,
    infocrlink_type VARCHAR(100),
    commission_rate DECIMAL(5,2),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for infocrlink_mapping
CREATE INDEX idx_infocrlink_channel ON infocrlink_mapping(channel_id);
CREATE INDEX idx_infocrlink_active ON infocrlink_mapping(is_active);

-- ============================================
-- 6. video_analysis_cache table (추가)
-- ============================================
DROP TABLE IF EXISTS video_analysis_cache CASCADE;
CREATE TABLE video_analysis_cache (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    video_file_hash VARCHAR(64) NOT NULL UNIQUE, -- SHA256 hash of video file
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

-- Indexes for video_analysis_cache
CREATE INDEX idx_analysis_hash ON video_analysis_cache(video_file_hash);
CREATE INDEX idx_analysis_expires ON video_analysis_cache(expires_at);

-- ============================================
-- Functions and Triggers
-- ============================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply updated_at triggers
CREATE TRIGGER update_youtube_channels_updated_at BEFORE UPDATE
    ON youtube_channels FOR EACH ROW EXECUTE PROCEDURE update_updated_at_column();

CREATE TRIGGER update_upload_queue_updated_at BEFORE UPDATE
    ON upload_queue FOR EACH ROW EXECUTE PROCEDURE update_updated_at_column();

CREATE TRIGGER update_channel_upload_limits_updated_at BEFORE UPDATE
    ON channel_upload_limits FOR EACH ROW EXECUTE PROCEDURE update_updated_at_column();

CREATE TRIGGER update_infocrlink_mapping_updated_at BEFORE UPDATE
    ON infocrlink_mapping FOR EACH ROW EXECUTE PROCEDURE update_updated_at_column();

-- ============================================
-- Function to check channel upload limits
-- ============================================
CREATE OR REPLACE FUNCTION check_channel_upload_limit(p_channel_id UUID)
RETURNS BOOLEAN AS $$
DECLARE
    v_count INT;
    v_max_uploads INT;
BEGIN
    -- Get max uploads for channel
    SELECT max_daily_uploads INTO v_max_uploads
    FROM youtube_channels
    WHERE id = p_channel_id AND is_active = true;
    
    IF v_max_uploads IS NULL THEN
        RETURN false;
    END IF;
    
    -- Get today's upload count
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

-- ============================================
-- Function to increment upload count
-- ============================================
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

-- ============================================
-- View for available channels (not at limit)
-- ============================================
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

-- ============================================
-- View for queue status overview
-- ============================================
CREATE OR REPLACE VIEW queue_status_overview AS
SELECT 
    status,
    COUNT(*) as count,
    MIN(created_at) as oldest_item,
    MAX(created_at) as newest_item
FROM upload_queue
GROUP BY status;

-- ============================================
-- View for channel statistics
-- ============================================
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

-- ============================================
-- RLS (Row Level Security) Policies
-- ============================================

-- Enable RLS on all tables
ALTER TABLE youtube_channels ENABLE ROW LEVEL SECURITY;
ALTER TABLE upload_queue ENABLE ROW LEVEL SECURITY;
ALTER TABLE upload_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE channel_upload_limits ENABLE ROW LEVEL SECURITY;
ALTER TABLE infocrlink_mapping ENABLE ROW LEVEL SECURITY;
ALTER TABLE video_analysis_cache ENABLE ROW LEVEL SECURITY;

-- Create policies (adjust based on your authentication setup)
-- For now, allowing all operations for authenticated users
CREATE POLICY "Allow all operations for authenticated users" ON youtube_channels
    FOR ALL USING (true);

CREATE POLICY "Allow all operations for authenticated users" ON upload_queue
    FOR ALL USING (true);

CREATE POLICY "Allow all operations for authenticated users" ON upload_history
    FOR ALL USING (true);

CREATE POLICY "Allow all operations for authenticated users" ON channel_upload_limits
    FOR ALL USING (true);

CREATE POLICY "Allow all operations for authenticated users" ON infocrlink_mapping
    FOR ALL USING (true);

CREATE POLICY "Allow all operations for authenticated users" ON video_analysis_cache
    FOR ALL USING (true);

-- ============================================
-- Sample Data (Optional - Remove in production)
-- ============================================

-- Sample categories for reference
/*
INSERT INTO youtube_channels (channel_name, channel_url, channel_type, category, description, account_id, account_password, max_daily_uploads)
VALUES 
    ('Tech Reviews Main', 'https://youtube.com/@techreviews', 'main', 'technology', 'Main tech review channel', 'encrypted_id_1', 'encrypted_pass_1', 3),
    ('Gaming Highlights', 'https://youtube.com/@gaminghighlights', 'main', 'gaming', 'Gaming content channel', 'encrypted_id_2', 'encrypted_pass_2', 3),
    ('Lifestyle Tips', 'https://youtube.com/@lifestyletips', 'main', 'lifestyle', 'Lifestyle and tips channel', 'encrypted_id_3', 'encrypted_pass_3', 3);
*/

-- ============================================
-- Grant permissions (adjust based on your setup)
-- ============================================

-- Grant usage on schema
GRANT USAGE ON SCHEMA public TO anon, authenticated;

-- Grant permissions on tables
GRANT ALL ON ALL TABLES IN SCHEMA public TO authenticated;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO anon;

-- Grant permissions on sequences
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO authenticated;