# UGC 영상 자동 관리 시스템 - 기술 명세서

## 1. 프로젝트 개요

### 1.1 목적
UGC(User Generated Content) 영상을 자동으로 분석하여 적절한 유튜브 채널에 할당하고, SEO 최적화된 메타데이터를 생성하여 업로드 큐를 관리하는 시스템

### 1.2 핵심 기능
- 영상 자동 감지 및 내용 분석
- 지능형 채널 매칭
- SEO 최적화 메타데이터 생성
- 업로드 제한 관리 (24시간 3개)
- 제품 매칭 및 쿠팡 링크 연결

### 1.3 시스템 요구사항
- 일일 200개 이상 영상 처리
- 파일 크기: 10MB ~ 150MB
- 채널 규모: 10 ~ 50개
- 로컬 구동 (웹서버 확장 가능)

## 2. 시스템 아키텍처

### 2.1 전체 구조
```
┌─────────────────────────────────────────────────────────────┐
│                        사용자 인터페이스                        │
│                    (CLI → Web Dashboard)                     │
└───────────────┬─────────────────────────────────┬───────────┘
                │                                 │
┌───────────────▼─────────────┐   ┌──────────────▼──────────────┐
│         API Gateway         │   │      Admin Dashboard         │
│      (FastAPI/Flask)        │   │    (React/Vue - Phase 4)     │
└───────────────┬─────────────┘   └──────────────────────────────┘
                │
┌───────────────▼─────────────────────────────────────────────┐
│                      Core Processing Layer                   │
├───────────────┬─────────────────────────────────┬───────────┤
│  Video        │  Analysis & Matching            │  Queue    │
│  Watcher      │  ├─ Video Analyzer              │  Manager  │
│               │  ├─ Channel Matcher             │           │
│               │  ├─ SEO Generator               │           │
│               │  └─ Product Matcher             │           │
└───────────────┴─────────────────────────────────┴───────────┘
                │                                 │
┌───────────────▼─────────────────────────────────▼───────────┐
│                       Data Layer                            │
│                    (Supabase/Firebase)                      │
├──────────────────────────────────────────────────────────────┤
│  ├─ youtube_channels    ├─ upload_queue                    │
│  ├─ upload_history      ├─ channel_upload_limits           │
│  └─ infocrlink_mapping                                     │
└──────────────────────────────────────────────────────────────┘
                │                                 │
┌───────────────▼─────────────┐   ┌──────────────▼──────────────┐
│     External Services       │   │      File Storage           │
│  ├─ Gemini Vision API      │   │   (Local → S3/GCS)          │
│  ├─ Google Images Search   │   └──────────────────────────────┘
│  └─ Coupang API (Optional) │
└─────────────────────────────┘
```

### 2.2 데이터 흐름
1. **영상 감지**: Video Watcher가 지정 폴더 모니터링
2. **영상 분석**: Gemini Vision API로 내용 분석
3. **채널 매칭**: 분석 결과 기반 최적 채널 선택
4. **메타데이터 생성**: SEO 최적화된 제목/설명 생성
5. **제품 매칭**: Google Images로 쿠팡 제품 검색
6. **큐 등록**: 업로드 큐에 작업 등록
7. **제한 관리**: 채널별 업로드 제한 체크

## 3. 데이터베이스 스키마 (Supabase)

### 3.1 youtube_channels
```sql
CREATE TABLE youtube_channels (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    channel_name VARCHAR(255) NOT NULL,
    channel_url VARCHAR(500) NOT NULL,
    channel_type ENUM('main', 'sub') NOT NULL,
    parent_channel_id UUID REFERENCES youtube_channels(id),
    category VARCHAR(100) NOT NULL,
    description TEXT,
    account_id VARCHAR(255) NOT NULL,  -- 암호화 저장
    account_password TEXT NOT NULL,     -- 암호화 저장
    infocrlink_url VARCHAR(500),
    max_daily_uploads INT DEFAULT 3,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_channel_category ON youtube_channels(category);
CREATE INDEX idx_channel_active ON youtube_channels(is_active);
```

### 3.2 upload_queue
```sql
CREATE TABLE upload_queue (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    video_file_path TEXT NOT NULL,
    video_file_name VARCHAR(500) NOT NULL,
    file_size_mb DECIMAL(10,2),
    channel_id UUID REFERENCES youtube_channels(id),
    title VARCHAR(500) NOT NULL,
    description TEXT NOT NULL,
    tags TEXT[],
    coupang_url VARCHAR(1000),
    infocrlink_data JSONB,
    status ENUM('pending', 'processing', 'ready', 'uploaded', 'failed') DEFAULT 'pending',
    priority INT DEFAULT 50,
    scheduled_time TIMESTAMP,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_queue_status ON upload_queue(status);
CREATE INDEX idx_queue_priority ON upload_queue(priority DESC);
CREATE INDEX idx_queue_scheduled ON upload_queue(scheduled_time);
```

### 3.3 upload_history
```sql
CREATE TABLE upload_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    queue_id UUID REFERENCES upload_queue(id),
    channel_id UUID REFERENCES youtube_channels(id),
    video_file_name VARCHAR(500) NOT NULL,
    upload_time TIMESTAMP NOT NULL,
    youtube_video_id VARCHAR(100),
    youtube_video_url VARCHAR(500),
    views_count INT DEFAULT 0,
    likes_count INT DEFAULT 0,
    comments_count INT DEFAULT 0,
    revenue_data JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_history_channel ON upload_history(channel_id);
CREATE INDEX idx_history_date ON upload_history(upload_time);
```

### 3.4 channel_upload_limits
```sql
CREATE TABLE channel_upload_limits (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    channel_id UUID REFERENCES youtube_channels(id),
    upload_date DATE NOT NULL,
    upload_count INT DEFAULT 0,
    last_upload_time TIMESTAMP,
    UNIQUE(channel_id, upload_date)
);

CREATE INDEX idx_limits_date ON channel_upload_limits(upload_date);
```

### 3.5 infocrlink_mapping
```sql
CREATE TABLE infocrlink_mapping (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    channel_id UUID REFERENCES youtube_channels(id),
    infocrlink_url VARCHAR(500) NOT NULL,
    infocrlink_type VARCHAR(100),
    commission_rate DECIMAL(5,2),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

## 4. 핵심 모듈 설계

### 4.1 Video Watcher
```python
# src/watchers/video_watcher.py
class VideoWatcher:
    """
    폴더 모니터링 및 새 영상 파일 감지
    - Watchdog 라이브러리 활용
    - 파일 필터링 (확장자, 크기)
    - 중복 처리 방지
    """
    
    def __init__(self, watch_folder: str):
        self.watch_folder = watch_folder
        self.processed_files = set()
        
    def start_watching(self):
        # 폴더 모니터링 시작
        pass
        
    def on_new_video(self, file_path: str):
        # 새 영상 감지 시 처리
        pass
```

### 4.2 Video Analyzer
```python
# src/analyzers/video_analyzer.py
class VideoAnalyzer:
    """
    Gemini Vision API를 활용한 영상 분석
    - 프레임 추출 및 분석
    - 제품 정보 추출
    - 콘텐츠 카테고리 분류
    """
    
    def __init__(self, api_key: str):
        self.gemini_client = self._init_gemini(api_key)
        
    async def analyze_video(self, video_path: str) -> dict:
        # 영상 분석 및 메타데이터 추출
        frames = await self.extract_key_frames(video_path)
        analysis = await self.gemini_analyze(frames)
        return {
            'products': analysis['products'],
            'category': analysis['category'],
            'keywords': analysis['keywords'],
            'tone': analysis['tone']
        }
```

### 4.3 Channel Matcher
```python
# src/matchers/channel_matcher.py
class ChannelMatcher:
    """
    영상 분석 결과 기반 최적 채널 매칭
    - 카테고리 매칭
    - 채널 성격 분석
    - 업로드 제한 체크
    """
    
    def __init__(self, db_client):
        self.db = db_client
        
    async def find_best_channel(self, video_analysis: dict) -> str:
        # 1. 카테고리 매칭
        # 2. 업로드 가능 채널 필터링
        # 3. 우선순위 기반 선택
        pass
```

### 4.4 SEO Generator
```python
# src/generators/seo_generator.py
class SEOGenerator:
    """
    SEO 최적화된 메타데이터 생성
    - 제목 생성 (60자 이내)
    - 설명 생성 (5000자 이내)
    - 태그 추천
    """
    
    def __init__(self):
        self.title_templates = self._load_templates()
        
    async def generate_metadata(self, video_analysis: dict) -> dict:
        title = await self.generate_title(video_analysis)
        description = await self.generate_description(video_analysis)
        tags = await self.generate_tags(video_analysis)
        
        return {
            'title': title,
            'description': description,
            'tags': tags
        }
```

### 4.5 Product Matcher
```python
# src/matchers/product_matcher.py
class ProductMatcher:
    """
    Google Images 검색을 통한 쿠팡 제품 매칭
    - 이미지 기반 제품 검색
    - 쿠팡 URL 추출
    - 가격 정보 수집
    """
    
    async def find_coupang_product(self, product_info: dict) -> str:
        # Google Images 역검색
        # 쿠팡 URL 추출
        pass
```

### 4.6 Queue Manager
```python
# src/queue/queue_manager.py
class QueueManager:
    """
    업로드 큐 관리
    - 우선순위 관리
    - 스케줄링
    - 상태 업데이트
    """
    
    def __init__(self, db_client):
        self.db = db_client
        
    async def add_to_queue(self, video_data: dict):
        # 큐에 작업 추가
        pass
        
    async def get_next_task(self) -> dict:
        # 다음 작업 가져오기
        pass
```

### 4.7 Limit Tracker
```python
# src/trackers/limit_tracker.py
class LimitTracker:
    """
    채널별 업로드 제한 관리
    - 24시간 3개 제한 추적
    - 가용 채널 확인
    """
    
    async def check_channel_availability(self, channel_id: str) -> bool:
        # 업로드 가능 여부 확인
        pass
        
    async def record_upload(self, channel_id: str):
        # 업로드 기록
        pass
```

## 5. API 엔드포인트

### 5.1 채널 관리
```
POST   /api/channels                 # 채널 추가
GET    /api/channels                 # 채널 목록
GET    /api/channels/{id}            # 채널 상세
PUT    /api/channels/{id}            # 채널 수정
DELETE /api/channels/{id}            # 채널 삭제
GET    /api/channels/{id}/limits     # 업로드 제한 확인
```

### 5.2 업로드 큐
```
GET    /api/queue                    # 큐 목록
POST   /api/queue                    # 큐 추가
GET    /api/queue/{id}               # 큐 항목 상세
PUT    /api/queue/{id}               # 큐 항목 수정
DELETE /api/queue/{id}               # 큐 항목 삭제
POST   /api/queue/{id}/process       # 작업 처리 시작
```

### 5.3 영상 분석
```
POST   /api/analyze/video            # 영상 분석 요청
GET    /api/analyze/{job_id}         # 분석 결과 조회
POST   /api/analyze/batch            # 배치 분석
```

### 5.4 통계 및 모니터링
```
GET    /api/stats/overview           # 전체 통계
GET    /api/stats/channels           # 채널별 통계
GET    /api/stats/uploads            # 업로드 통계
GET    /api/health                   # 시스템 상태
```

## 6. 프로젝트 구조

```
ugc-video-manager/
├── src/
│   ├── __init__.py
│   ├── watchers/
│   │   ├── __init__.py
│   │   └── video_watcher.py
│   ├── analyzers/
│   │   ├── __init__.py
│   │   └── video_analyzer.py
│   ├── matchers/
│   │   ├── __init__.py
│   │   ├── channel_matcher.py
│   │   └── product_matcher.py
│   ├── generators/
│   │   ├── __init__.py
│   │   └── seo_generator.py
│   ├── queue/
│   │   ├── __init__.py
│   │   └── queue_manager.py
│   ├── trackers/
│   │   ├── __init__.py
│   │   └── limit_tracker.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes/
│   │   │   ├── channels.py
│   │   │   ├── queue.py
│   │   │   ├── analyze.py
│   │   │   └── stats.py
│   │   └── main.py
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── encryption.py
│   │   ├── validators.py
│   │   └── helpers.py
│   └── config/
│       ├── __init__.py
│       └── settings.py
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
├── scripts/
│   ├── setup_db.py
│   ├── migrate.py
│   └── seed_data.py
├── docs/
│   ├── API.md
│   ├── SETUP.md
│   └── USAGE.md
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yml
├── requirements.txt
├── requirements-dev.txt
├── .env.example
├── .gitignore
├── README.md
└── setup.py
```

## 7. 기술 스택

### 7.1 백엔드
- **언어**: Python 3.11+
- **프레임워크**: FastAPI (비동기 처리, 고성능)
- **비동기**: asyncio, aiohttp
- **작업 큐**: Celery + Redis (옵션)

### 7.2 데이터베이스
- **Primary**: Supabase (PostgreSQL)
- **Cache**: Redis (옵션)
- **File Storage**: Local → S3/GCS (확장 시)

### 7.3 외부 서비스
- **Gemini Vision API**: 영상 분석
- **Google Images API**: 제품 검색
- **Coupang Partners API**: 제품 정보 (옵션)

### 7.4 모니터링 및 로깅
- **Logging**: Python logging + Loguru
- **Monitoring**: Prometheus + Grafana (Phase 4)
- **Error Tracking**: Sentry (옵션)

### 7.5 개발 도구
- **Testing**: pytest, pytest-asyncio
- **Code Quality**: black, flake8, mypy
- **Documentation**: Sphinx
- **CI/CD**: GitHub Actions

## 8. 구현 로드맵

### Phase 1: 기본 인프라 구축 (1-2주)
- [ ] 프로젝트 구조 생성
- [ ] Supabase 설정 및 스키마 생성
- [ ] 기본 API 프레임워크 구성
- [ ] 환경 설정 및 .env 구성
- [ ] 로깅 시스템 구축

### Phase 2: 핵심 기능 구현 (3-4주)
- [ ] Video Watcher 구현
- [ ] Gemini Vision API 연동
- [ ] Channel Matcher 로직 구현
- [ ] SEO Generator 개발
- [ ] Product Matcher 구현
- [ ] Queue Manager 개발
- [ ] Limit Tracker 구현

### Phase 3: 통합 및 테스트 (2-3주)
- [ ] 모듈 통합
- [ ] API 엔드포인트 완성
- [ ] 단위 테스트 작성
- [ ] 통합 테스트
- [ ] 성능 최적화
- [ ] 에러 핸들링 강화

### Phase 4: 웹서버 확장 준비 (1-2주)
- [ ] Docker 컨테이너화
- [ ] 웹 대시보드 프로토타입
- [ ] 배포 스크립트 작성
- [ ] 모니터링 시스템 구축
- [ ] 문서화 완성

## 9. 환경 설정 (.env)

```bash
# API Keys
GEMINI_API_KEY=your_gemini_api_key_here
GOOGLE_CUSTOM_SEARCH_API_KEY=your_google_api_key_here
GOOGLE_SEARCH_ENGINE_ID=your_search_engine_id_here

# Database
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your_anon_key_here
SUPABASE_SERVICE_KEY=your_service_key_here

# Paths
WATCH_FOLDER_PATH=/path/to/watch/folder
TEMP_FOLDER_PATH=/path/to/temp/folder
LOG_FOLDER_PATH=/path/to/logs

# Settings
MAX_DAILY_UPLOADS_PER_CHANNEL=3
MAX_FILE_SIZE_MB=150
MIN_FILE_SIZE_MB=10
SUPPORTED_VIDEO_FORMATS=mp4,avi,mov,mkv
BATCH_SIZE=10
WORKER_THREADS=4

# Security
ENCRYPTION_KEY=your_32_byte_encryption_key_here
JWT_SECRET_KEY=your_jwt_secret_key_here

# Server (Phase 4)
API_HOST=0.0.0.0
API_PORT=8000
DEBUG_MODE=False
CORS_ORIGINS=http://localhost:3000

# Optional Services
COUPANG_ACCESS_KEY=
COUPANG_SECRET_KEY=
REDIS_URL=redis://localhost:6379/0
SENTRY_DSN=
```

## 10. 보안 고려사항

### 10.1 데이터 보안
- 계정 정보 AES-256 암호화
- API 키 환경변수 분리
- HTTPS 전용 통신 (웹서버)
- SQL Injection 방지

### 10.2 접근 제어
- JWT 기반 인증 (API)
- Rate Limiting
- IP 화이트리스트 (옵션)

### 10.3 모니터링
- 비정상 패턴 감지
- 실패 알림
- 감사 로그

## 11. 성능 최적화

### 11.1 병렬 처리
- 비동기 I/O 활용
- 멀티스레딩 영상 처리
- 배치 처리 최적화

### 11.2 캐싱
- Redis 캐싱 (채널 정보)
- 분석 결과 캐싱
- API 응답 캐싱

### 11.3 리소스 관리
- 메모리 사용량 모니터링
- 디스크 공간 관리
- 네트워크 대역폭 최적화

## 12. 확장성 고려사항

### 12.1 수평 확장
- 마이크로서비스 아키텍처 준비
- 메시지 큐 도입 가능
- 로드 밸런싱 지원

### 12.2 웹서버 마이그레이션
- RESTful API 설계
- 상태 비저장 구조
- 컨테이너화 준비

### 12.3 추가 기능 확장
- 자동 업로드 모듈 추가 용이
- 다양한 플랫폼 지원 가능
- AI 분석 고도화 가능

## 13. 테스트 전략

### 13.1 단위 테스트
```python
# tests/unit/test_video_analyzer.py
async def test_analyze_video():
    analyzer = VideoAnalyzer(api_key="test_key")
    result = await analyzer.analyze_video("test_video.mp4")
    assert 'products' in result
    assert 'category' in result
```

### 13.2 통합 테스트
```python
# tests/integration/test_workflow.py
async def test_complete_workflow():
    # 1. 영상 감지
    # 2. 분석
    # 3. 채널 매칭
    # 4. 큐 등록
    # 5. 제한 체크
    pass
```

### 13.3 부하 테스트
- 200개 동시 처리 테스트
- API 응답 시간 측정
- 메모리 누수 체크

## 14. 문서화

### 14.1 API 문서
- OpenAPI/Swagger 자동 생성
- Postman Collection 제공
- 사용 예제 포함

### 14.2 사용자 가이드
- 설치 가이드
- 설정 가이드
- 운영 매뉴얼

### 14.3 개발자 문서
- 아키텍처 설명
- 모듈 인터페이스
- 확장 가이드

## 15. 예상 일정 및 마일스톤

### 전체 일정: 8-10주

1. **Week 1-2**: 기본 인프라 및 환경 구축
2. **Week 3-4**: Video Watcher, Analyzer 구현
3. **Week 5-6**: Matcher, Generator 구현
4. **Week 7**: Queue Manager, Limit Tracker 구현
5. **Week 8**: 통합 테스트 및 버그 수정
6. **Week 9**: 성능 최적화 및 문서화
7. **Week 10**: 웹서버 확장 준비

### 주요 마일스톤
- **M1**: 기본 인프라 완성
- **M2**: 영상 분석 파이프라인 완성
- **M3**: 큐 시스템 완성
- **M4**: 전체 통합 및 테스트 완료
- **M5**: 프로덕션 준비 완료

## 16. 리스크 관리

### 16.1 기술적 리스크
- **Gemini API 제한**: Rate limiting 대응
- **대용량 영상 처리**: 청크 처리 구현
- **동시성 이슈**: 락 메커니즘 구현

### 16.2 운영 리스크
- **API 키 노출**: 환경변수 암호화
- **데이터 손실**: 백업 시스템 구축
- **서비스 중단**: 재시작 메커니즘

## 17. 결론

이 기술 명세서는 UGC 영상 자동 관리 시스템의 완전한 구현 가이드를 제공합니다. 로컬 환경에서 시작하여 점진적으로 웹서버로 확장 가능한 구조로 설계되었으며, 모든 요구사항을 충족하는 안정적이고 확장 가능한 시스템을 구축할 수 있습니다.

### 다음 단계
1. 이 명세서 검토 및 피드백
2. 개발 환경 구축
3. Phase 1 시작

---

*문서 버전: 1.0*  
*작성일: 2025-08-28*  
*작성자: Tech Spec Planner Agent*