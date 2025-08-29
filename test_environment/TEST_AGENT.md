# Test Agent Configuration

## 🤖 Test Agent Role
자동화된 테스트 실행 및 품질 보증을 담당하는 전문 에이전트

## 📋 Test Agent Responsibilities

### 1. Unit Testing
- 개별 모듈 기능 테스트
- Mock 객체 활용
- 엣지 케이스 검증

### 2. Integration Testing  
- 모듈 간 통합 테스트
- API 엔드포인트 테스트
- 데이터베이스 연동 테스트

### 3. Performance Testing
- 부하 테스트 (200개 동시 처리)
- 응답 시간 측정
- 메모리 사용량 모니터링

### 4. Security Testing
- 인증/인가 테스트
- SQL Injection 방지 검증
- 암호화 검증

## 🛠️ Test Environment Setup

### Required Tools
```bash
# Test dependencies
pytest>=7.0.0
pytest-asyncio>=0.21.0
pytest-cov>=4.0.0
pytest-mock>=3.10.0
httpx>=0.24.0  # For API testing
faker>=18.0.0  # For test data generation
```

### Test Database
- Separate test database in Supabase
- Automatic setup/teardown
- Test data seeding

## 📂 Test Structure
```
test_environment/
├── unit_tests/
│   ├── test_video_watcher.py
│   ├── test_video_analyzer.py
│   ├── test_channel_matcher.py
│   ├── test_seo_generator.py
│   ├── test_product_matcher.py
│   ├── test_queue_manager.py
│   └── test_limit_tracker.py
├── integration_tests/
│   ├── test_api_endpoints.py
│   ├── test_database_operations.py
│   ├── test_workflow_complete.py
│   └── test_external_services.py
├── performance_tests/
│   ├── test_concurrent_processing.py
│   ├── test_api_load.py
│   └── test_memory_usage.py
├── security_tests/
│   ├── test_authentication.py
│   ├── test_encryption.py
│   └── test_sql_injection.py
├── fixtures/
│   ├── sample_videos/
│   ├── mock_data.py
│   └── test_config.py
└── reports/
    ├── coverage/
    └── performance/
```

## 🎯 Test Commands

### Run All Tests
```bash
pytest test_environment/ -v
```

### Run Specific Category
```bash
# Unit tests only
pytest test_environment/unit_tests/ -v

# Integration tests
pytest test_environment/integration_tests/ -v

# With coverage report
pytest test_environment/ --cov=src --cov-report=html
```

### Performance Testing
```bash
# Load testing
python test_environment/performance_tests/test_concurrent_processing.py

# Memory profiling
python -m memory_profiler test_environment/performance_tests/test_memory_usage.py
```

## 📊 Test Metrics

### Coverage Goals
- Unit Tests: >80% coverage
- Integration Tests: >70% coverage
- Critical paths: 100% coverage

### Performance Benchmarks
- API Response: <200ms (p95)
- Video Processing: <5s per video
- Database queries: <100ms

### Success Criteria
- ✅ All unit tests pass
- ✅ Integration tests pass
- ✅ Performance benchmarks met
- ✅ Security tests pass
- ✅ No memory leaks detected

## 🔄 CI/CD Integration

### GitHub Actions Workflow
```yaml
name: Test Suite

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Setup Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-test.txt
      - name: Run tests
        run: pytest test_environment/ -v --cov=src
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

## 📝 Test Documentation

### Test Case Template
```python
"""
Test ID: TC-001
Module: VideoWatcher
Function: detect_new_video
Description: Verify new video detection in watch folder
Prerequisites: Watch folder exists and is accessible
"""

@pytest.mark.asyncio
async def test_detect_new_video():
    # Arrange
    watcher = VideoWatcher("/test/folder")
    test_video = create_test_video()
    
    # Act
    result = await watcher.detect_new_video(test_video)
    
    # Assert
    assert result.detected == True
    assert result.file_path == test_video.path
```

## 🚨 Error Reporting

### Test Failure Format
```
FAILED: test_video_analyzer.py::test_gemini_api_connection
Reason: API key invalid or expired
Action: Check GEMINI_API_KEY in .env.test
Priority: HIGH
```

## 🔧 Mock Services

### Gemini API Mock
```python
class MockGeminiAPI:
    async def analyze_video(self, video_path):
        return {
            "products": ["Product A", "Product B"],
            "category": "technology",
            "confidence": 0.95
        }
```

### Supabase Mock
```python
class MockSupabase:
    async def insert(self, table, data):
        return {"id": "mock-uuid", **data}
```

## 🎯 Test Agent Workflow

1. **Environment Check**
   - Verify test database connection
   - Check API keys availability
   - Ensure test folders exist

2. **Pre-test Setup**
   - Clear test database
   - Seed test data
   - Initialize mocks

3. **Test Execution**
   - Run tests by category
   - Collect metrics
   - Generate reports

4. **Post-test Cleanup**
   - Remove test files
   - Clear database
   - Archive reports

5. **Result Analysis**
   - Coverage analysis
   - Performance metrics
   - Security vulnerabilities

## 📈 Continuous Improvement

### Weekly Tasks
- Review failed tests
- Update test cases
- Improve coverage
- Optimize slow tests

### Monthly Tasks
- Security audit
- Performance baseline update
- Test infrastructure review
- Documentation update

---

*Test Agent v1.0 - Ensuring Quality Through Automation*