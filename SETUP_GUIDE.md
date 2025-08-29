# UGC Video Manager - Setup Guide

## 1. Supabase 프로젝트 생성

### 1.1 새 프로젝트 생성
1. [Supabase Dashboard](https://app.supabase.com) 접속
2. "New Project" 클릭
3. 프로젝트 정보 입력:
   - Project name: `ugc-video-manager`
   - Database Password: 강력한 비밀번호 설정
   - Region: 가장 가까운 지역 선택 (예: Northeast Asia)
4. "Create new project" 클릭

### 1.2 API 키 확인
프로젝트 생성 후 Settings > API에서:
- `Project URL` 복사 → `.env`의 `SUPABASE_URL`에 입력
- `anon/public` 키 복사 → `.env`의 `SUPABASE_ANON_KEY`에 입력
- `service_role` 키 복사 → `.env`의 `SUPABASE_SERVICE_KEY`에 입력

## 2. 데이터베이스 설정

### 2.1 SQL Editor 접속
1. Supabase Dashboard에서 SQL Editor 탭 클릭
2. 새 쿼리 생성

### 2.2 테이블 생성
`/scripts/setup_database.sql` 파일의 내용을 복사하여 SQL Editor에 붙여넣고 실행

또는 아래 명령어 순서대로 실행:

```sql
-- 1. UUID Extension 활성화
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 2. 테이블 생성 (setup_database.sql 내용)
-- 파일 내용 복사하여 실행
```

## 3. 로컬 환경 설정

### 3.1 Python 가상환경 설정
```bash
# 가상환경 생성
python3 -m venv venv

# 가상환경 활성화
# Mac/Linux:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt
```

### 3.2 환경변수 설정
`.env` 파일 수정:
```env
# Supabase Configuration (필수!)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your_anon_key_here
SUPABASE_SERVICE_KEY=your_service_key_here

# Gemini API (필수!)
GEMINI_API_KEY=your_gemini_api_key_here
```

### 3.3 폴더 생성
```bash
# 필요한 폴더 자동 생성
mkdir -p watch_folder temp logs
```

## 4. 애플리케이션 실행

### 4.1 개발 서버 실행
```bash
# FastAPI 서버 실행
python main.py

# 또는 uvicorn으로 직접 실행
uvicorn src.api.main:app --reload --port 8000
```

### 4.2 API 문서 확인
브라우저에서 접속:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 5. 테스트

### 5.1 단위 테스트 실행
```bash
# 모든 테스트 실행
pytest test_environment/

# 특정 테스트만 실행
pytest test_environment/unit_tests/
```

### 5.2 데이터베이스 연결 테스트
```python
# Python 콘솔에서 테스트
from src.utils.database import get_db_manager

db = get_db_manager()
channels = await db.get_available_channels()
print(channels)
```

## 6. 초기 데이터 입력

### 6.1 YouTube 채널 추가
Supabase Dashboard의 Table Editor에서 `youtube_channels` 테이블에 데이터 추가:

```sql
INSERT INTO youtube_channels (
    channel_name, 
    channel_url, 
    channel_type, 
    category, 
    account_id, 
    account_password,
    max_daily_uploads
) VALUES (
    '테스트 채널', 
    'https://youtube.com/@testchannel',
    'main',
    'technology',
    'encrypted_account_id',
    'encrypted_password',
    3
);
```

## 7. 트러블슈팅

### 문제: Supabase 연결 실패
- `.env` 파일의 SUPABASE_URL과 키가 올바른지 확인
- 프로젝트가 일시정지 상태가 아닌지 확인

### 문제: 모듈 import 에러
```bash
# PYTHONPATH 설정
export PYTHONPATH="${PYTHONPATH}:${PWD}"
```

### 문제: 권한 에러
- Supabase Dashboard에서 RLS 정책 확인
- Service Key 사용 여부 확인

## 8. 다음 단계

1. **Phase 1 완료**: 기본 인프라 구축 ✅
2. **Phase 2 시작**: 핵심 기능 구현
   - Video Watcher 모듈
   - Gemini API 연동
   - Channel Matcher 구현

---

문제가 발생하면 `/docs` 폴더의 문서를 참고하거나 이슈를 생성해주세요.