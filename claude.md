# Claude.md - UGC Video Manager Project Context

## 프로젝트 개요
UGC 영상을 자동으로 분석하여 적절한 유튜브 채널에 할당하고, SEO 최적화된 메타데이터를 생성하여 업로드 큐를 관리하는 시스템

## 📚 핵심 문서

### 1. [기술 명세서](./TECHNICAL_SPECIFICATION.md)
- 전체 시스템 아키텍처
- 7개 핵심 모듈 설계
- API 엔드포인트 설계
- 구현 로드맵 (8-10주)
- 기술 스택 및 환경 설정

### 2. [데이터베이스 스키마](./DATABASE_SCHEMA.md)
- Supabase PostgreSQL 기반
- 6개 핵심 테이블
- 3개 뷰, 2개 함수
- RLS 보안 정책
- 시각적 ERD 다이어그램

### 3. [데이터베이스 설정 스크립트](./scripts/setup_database.sql)
- 전체 테이블 생성 SQL
- 인덱스 및 트리거 설정
- 함수 및 뷰 정의
- RLS 정책 설정

## 🎯 주요 요구사항

### 시스템 규모
- 일일 200개 이상 영상 처리
- 파일 크기: 10MB ~ 150MB
- 유튜브 채널: 10 ~ 50개 관리
- 로컬 구동 (웹서버 확장 가능)

### 핵심 기능
1. **영상 감지 및 분석**
   - 지정 폴더 모니터링
   - Gemini Vision API 연동
   - 제품 정보/기능 추출

2. **채널 관리**
   - 메인/서브 채널 구분
   - 24시간 3개 업로드 제한
   - 카테고리별 매칭

3. **SEO 최적화**
   - 자동 제목 생성
   - 설명문 최적화
   - 태그 추천

4. **큐 시스템**
   - 우선순위 관리
   - 스케줄링 지원
   - 에러 추적

5. **제품 매칭**
   - Google Images 검색
   - 쿠팡 링크 연결
   - 인포크링크 관리

## 🛠️ 기술 스택

### 백엔드
- **언어**: Python 3.11+
- **프레임워크**: FastAPI
- **비동기**: asyncio, aiohttp

### 데이터베이스
- **Primary**: Supabase (PostgreSQL)
- **Cache**: Redis (옵션)

### 외부 서비스
- Gemini Vision API
- Google Images API
- Coupang Partners API (옵션)

## 📂 프로젝트 구조
```
ugc-video-manager/
├── src/
│   ├── watchers/        # 영상 감지
│   ├── analyzers/       # 영상 분석
│   ├── matchers/        # 채널/제품 매칭
│   ├── generators/      # SEO 생성
│   ├── queue/           # 큐 관리
│   ├── trackers/        # 제한 추적
│   └── api/             # API 엔드포인트
├── scripts/             # 설정 스크립트
├── tests/               # 테스트
└── docs/                # 문서
```

## 🚀 구현 로드맵

### Phase 1: 기본 인프라 (1-2주)
- [ ] 프로젝트 구조 생성
- [x] Supabase 스키마 생성
- [ ] 기본 API 구성
- [ ] 환경 설정

### Phase 2: 핵심 기능 (3-4주)
- [ ] Video Watcher 구현
- [ ] Gemini API 연동
- [ ] Channel Matcher 구현
- [ ] SEO Generator 개발
- [ ] Queue Manager 구현

### Phase 3: 통합 테스트 (2-3주)
- [ ] 모듈 통합
- [ ] API 완성
- [ ] 테스트 작성
- [ ] 성능 최적화

### Phase 4: 웹서버 확장 (1-2주)
- [ ] Docker 설정
- [ ] 웹 대시보드
- [ ] 배포 준비
- [ ] 모니터링

## 🔐 보안 고려사항
- 계정 정보 AES-256 암호화
- API 키 환경변수 분리
- RLS 정책 적용
- JWT 인증 (API)

## 📝 환경 변수 (.env)
```bash
# API Keys
GEMINI_API_KEY=
GOOGLE_CUSTOM_SEARCH_API_KEY=
GOOGLE_SEARCH_ENGINE_ID=

# Database
SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_KEY=

# Paths
WATCH_FOLDER_PATH=
TEMP_FOLDER_PATH=
LOG_FOLDER_PATH=

# Settings
MAX_DAILY_UPLOADS_PER_CHANNEL=3
MAX_FILE_SIZE_MB=150
MIN_FILE_SIZE_MB=10
```

## 🔄 현재 진행 상황
- ✅ 기술 명세서 작성 완료
- ✅ 데이터베이스 스키마 설계 완료
- ✅ 데이터베이스 설정 스크립트 생성
- ✅ 시각적 스키마 문서 생성
- 🔄 Phase 1 인프라 구축 진행 중

## 💡 참고 사항
- Supabase MCP 연동 가능
- 로컬에서 시작, 웹서버로 확장 가능한 구조
- 모듈식 설계로 기능 추가 용이
- 추후 자동 업로드 기능 확장 가능

## 🤖 AI 어시스턴트 지침
이 프로젝트 작업 시:
1. 항상 기술 명세서 참고
2. 데이터베이스 변경 시 DATABASE_SCHEMA.md 업데이트
3. 모든 코드는 Python 3.11+ 기준
4. 비동기 처리 우선
5. 테스트 코드 작성 필수
6. 보안 최우선 고려

## 🧪 테스트 전략
- 모든 테스트는 `test_environment/` 폴더에서 관리
- Test Agent 구성: `test_environment/TEST_AGENT.md` 참조
- 테스트 실행 전 `test_config.py` 환경 설정 확인

## 🔗 Archon 통합 규칙

### 1. 프로젝트 관리 (Project Management)
```python
# Archon 프로젝트 생성 시 UGC Video Manager 메타데이터 포함
project_metadata = {
    "type": "ugc_video_manager",
    "version": "1.0",
    "modules": ["video_watcher", "analyzer", "queue_manager"],
    "database": "supabase",
    "api_framework": "fastapi"
}
```

### 2. 작업 관리 (Task Management)
- **작업 생성**: 각 Phase별 작업을 Archon 태스크로 등록
- **상태 추적**: `todo → doing → review → done`
- **담당자 할당**:
  - `Archon`: AI 개발 작업
  - `User`: 수동 설정 작업
  - `Test Agent`: 테스트 실행

### 3. 문서 관리 (Document Management)
- **PRP 문서**: 각 모듈별 Product Requirement Prompt 작성
- **버전 관리**: 모든 문서 변경사항 자동 버전 추적
- **동기화**: `claude.md` ↔ Archon 문서 동기화

### 4. 작업 흐름 (Workflow)

#### Phase별 Archon 태스크 구조:
```yaml
Phase 1 - Infrastructure:
  - task: "Setup project structure"
    assignee: "Archon"
    feature: "infrastructure"
  - task: "Configure Supabase database"
    assignee: "User"
    feature: "database"
  - task: "Create API framework"
    assignee: "Archon"
    feature: "api"

Phase 2 - Core Features:
  - task: "Implement Video Watcher"
    assignee: "Archon"
    feature: "video_processing"
  - task: "Integrate Gemini API"
    assignee: "Archon"
    feature: "ai_analysis"
  - task: "Test Video Analyzer"
    assignee: "Test Agent"
    feature: "testing"
```

### 5. RAG 쿼리 활용 (Knowledge Base)
- 기술 문서를 Archon RAG에 저장
- 코드 예제 검색 및 재사용
- 유사 문제 해결 방법 조회

### 6. 코드 예제 관리 (Code Examples)
```python
# Archon에 저장할 코드 예제 형식
code_example = {
    "title": "Gemini Vision API Integration",
    "module": "video_analyzer",
    "language": "python",
    "tags": ["api", "gemini", "async"],
    "code": "async def analyze_video(video_path: str) -> dict:",
    "description": "영상 분석 함수 구현"
}
```

### 7. 진행 상황 추적 (Progress Tracking)
- 일일 진행 상황을 Archon 태스크에 업데이트
- 주간 마일스톤 체크포인트
- 블로커 및 이슈 즉시 보고

### 8. 테스트 통합 (Test Integration)
```python
# Test Agent가 Archon에 보고할 테스트 결과 형식
test_result = {
    "task_id": "task_uuid",
    "test_type": "unit|integration|performance",
    "status": "passed|failed",
    "coverage": "85%",
    "details": "테스트 상세 결과"
}
```

### 9. 자동화 규칙 (Automation Rules)
- **자동 태스크 생성**: 새 모듈 추가 시 관련 태스크 자동 생성
- **상태 자동 업데이트**: 테스트 통과 시 태스크 상태 자동 변경
- **문서 자동 생성**: 코드 변경 시 관련 문서 자동 업데이트

### 10. 협업 프로토콜 (Collaboration Protocol)
1. **Morning Sync**: 일일 태스크 확인 및 우선순위 설정
2. **Code Review**: 모든 코드는 Archon 리뷰 후 머지
3. **Test First**: 기능 구현 전 테스트 케이스 먼저 작성
4. **Documentation**: 코드 작성과 동시에 문서 업데이트

### 11. 에러 처리 (Error Handling)
```python
# Archon 에러 보고 형식
error_report = {
    "module": "affected_module",
    "severity": "critical|high|medium|low",
    "error_type": "api|database|logic",
    "description": "에러 상세 설명",
    "suggested_fix": "제안된 해결 방법"
}
```

### 12. 배포 체크리스트 (Deployment Checklist)
- [ ] 모든 Archon 태스크 완료 확인
- [ ] 테스트 커버리지 80% 이상
- [ ] 문서 최신화 완료
- [ ] 성능 벤치마크 통과
- [ ] 보안 검증 완료

---
*Last Updated: 2025-08-28*
- 슈퍼베이스 구현은 슈퍼베이스 mcp 를 통해서 해줘 \
아니면 자체적으로슈퍼베이스를 구축할 수 있는 방법으로 해줘
- 암호화 할 필요없어 로컬호스트만 사용할꺼야