# UGC Video Manager

UGC 영상을 자동으로 분석하여 적절한 유튜브 채널에 할당하고, SEO 최적화된 메타데이터를 생성하여 업로드 큐를 관리하는 AI 기반 시스템

## 🎯 주요 기능

- **자동 영상 감지**: 지정 폴더 모니터링 및 자동 처리
- **AI 영상 분석**: Gemini Vision API를 통한 제품/콘텐츠 분석
- **채널 자동 매칭**: 카테고리별 최적 채널 자동 선택
- **SEO 최적화**: AI 기반 제목, 설명, 태그 자동 생성
- **큐 관리**: 우선순위 기반 업로드 스케줄링
- **제한 추적**: 채널별 일일 업로드 제한 관리

## 🚀 빠른 시작

### 1. 저장소 클론
```bash
git clone https://github.com/teamclington-jpg/ugc-video-manager.git
cd ugc-video-manager
```

### 2. 가상환경 설정
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 3. 의존성 설치
```bash
pip install -r requirements.txt
```

### 4. 환경 변수 설정
`.env` 파일을 생성하고 다음 내용을 입력:

```env
# Supabase
SUPABASE_URL=your_supabase_url
SUPABASE_ANON_KEY=your_anon_key
SUPABASE_SERVICE_KEY=your_service_key

# Google APIs
GEMINI_API_KEY=your_gemini_api_key
GOOGLE_CUSTOM_SEARCH_API_KEY=your_search_api_key
GOOGLE_SEARCH_ENGINE_ID=your_search_engine_id

# Paths
WATCH_FOLDER_PATH=./watch_folder
TEMP_FOLDER_PATH=./temp
LOG_FOLDER_PATH=./logs

# Settings
MAX_DAILY_UPLOADS_PER_CHANNEL=3
MAX_FILE_SIZE_MB=150
MIN_FILE_SIZE_MB=10
```

### 5. 데이터베이스 설정
```bash
# Supabase 대시보드에서 SQL 실행
# scripts/setup_database.sql 파일 내용 복사하여 실행
```

### 6. 서버 실행
```bash
python -m uvicorn src.api.main:app --reload
```

## 📂 프로젝트 구조

```
ugc-video-manager/
├── src/
│   ├── watchers/        # 영상 감지 모듈
│   ├── analyzers/       # AI 영상 분석
│   ├── matchers/        # 채널/제품 매칭
│   ├── generators/      # SEO 콘텐츠 생성
│   ├── queue/           # 업로드 큐 관리
│   ├── trackers/        # 제한 추적
│   └── api/             # FastAPI 엔드포인트
├── scripts/             # 설정 스크립트
├── tests/               # 테스트 코드
└── docs/                # 문서
```

## 🛠️ 기술 스택

- **Backend**: Python 3.11+, FastAPI
- **Database**: Supabase (PostgreSQL)
- **AI/ML**: Google Gemini Vision API
- **Async**: asyncio, aiohttp

## 📖 상세 문서

- [기술 명세서](./TECHNICAL_SPECIFICATION.md) - 전체 시스템 아키텍처
- [데이터베이스 스키마](./DATABASE_SCHEMA.md) - 테이블 구조 및 관계
- [API 문서](http://localhost:8000/docs) - 서버 실행 후 접속

## 🔧 개발 상태

- ✅ 기술 설계 완료
- ✅ 데이터베이스 스키마 구현
- 🔄 Phase 1: 기본 인프라 구축 중
- ⏳ Phase 2: 핵심 기능 구현 예정
- ⏳ Phase 3: 통합 테스트 예정
- ⏳ Phase 4: 웹서버 확장 예정

## 📝 라이센스

MIT License

## 🤝 기여하기

이슈 및 PR 환영합니다!

## 📧 문의

- GitHub Issues: [https://github.com/teamclington-jpg/ugc-video-manager/issues](https://github.com/teamclington-jpg/ugc-video-manager/issues)