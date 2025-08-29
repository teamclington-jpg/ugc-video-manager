#!/bin/bash

# UGC Video Manager 실행 스크립트 (Mac용)
# 이 파일을 더블클릭하여 실행하세요

# 스크립트 위치로 이동
cd "$(dirname "$0")"

# 터미널 제목 설정
echo -e "\033]0;UGC Video Manager\007"

# 색상 설정
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 배너 출력
clear
echo -e "${BLUE}"
echo "╔══════════════════════════════════════════════════════╗"
echo "║         UGC Video Manager v1.0.0                    ║"
echo "║     영상 자동 처리 및 업로드 큐 관리 시스템          ║"
echo "╚══════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Python 경로 확인
echo -e "${YELLOW}🔍 시스템 점검 중...${NC}"
PYTHON_CMD=""

if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
    echo -e "${GREEN}✅ Python3 발견: $(which python3)${NC}"
else
    echo -e "${RED}❌ Python3가 설치되어 있지 않습니다.${NC}"
    echo "Python3를 설치해 주세요: https://www.python.org/downloads/"
    echo "종료하려면 아무 키나 누르세요..."
    read -n 1
    exit 1
fi

# 의존성 확인
echo -e "${YELLOW}📦 필수 패키지 확인 중...${NC}"
if ! $PYTHON_CMD -c "import fastapi" 2>/dev/null; then
    echo -e "${YELLOW}📦 필수 패키지 설치 중... (첫 실행시 시간이 걸립니다)${NC}"
    $PYTHON_CMD -m pip install -r requirements.txt
    echo -e "${GREEN}✅ 패키지 설치 완료${NC}"
fi

# .env 파일 확인
if [ ! -f ".env" ]; then
    echo -e "${RED}❌ .env 파일이 없습니다!${NC}"
    echo "API 키를 설정해 주세요."
    echo "종료하려면 아무 키나 누르세요..."
    read -n 1
    exit 1
fi

#############################################
# 애플리케이션 시작 (가상환경 포함)
#############################################
echo ""
echo -e "${GREEN}🚀 UGC Video Manager 시작...${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "📁 감시 폴더: ${YELLOW}/Users/thecity17/Desktop/teamclingotondrive/상품쇼츠DB${NC}"
echo -e "🌐 웹 인터페이스: ${YELLOW}http://localhost:8000${NC}"
echo -e "📊 API 문서: ${YELLOW}http://localhost:8000/docs${NC}"
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${YELLOW}종료하려면 Ctrl+C를 누르세요${NC}"
echo ""

# 가상환경 경로 설정 (.venv 우선)
VENV_DIR=".venv"
if [ ! -d "$VENV_DIR" ]; then
  VENV_DIR="venv"
fi

if [ ! -d "$VENV_DIR" ]; then
  echo -e "${YELLOW}🔧 가상환경 생성 중...${NC}"
  $PYTHON_CMD -m venv .venv
  VENV_DIR=".venv"
  echo -e "${GREEN}✅ 가상환경 생성 완료${NC}"
fi

# Python/Pip 경로 결정
if [[ "$(uname -s)" == "MINGW" || "$(uname -s)" == *"NT"* ]]; then
  VENV_PY="$VENV_DIR/Scripts/python.exe"
  VENV_PIP="$VENV_DIR/Scripts/pip.exe"
else
  VENV_PY="$VENV_DIR/bin/python"
  VENV_PIP="$VENV_DIR/bin/pip"
fi

echo -e "${BLUE}[정보] Python 경로: ${VENV_PY}${NC}"

# 의존성 설치 확인 및 설치
if [ -f "requirements.txt" ]; then
  echo -e "${YELLOW}📦 필요한 패키지 확인 중...${NC}"
  export PYTHONIOENCODING=utf-8
  export PIP_DISABLE_PIP_VERSION_CHECK=1
  # stamp 기반 변경 감지
  STAMP_FILE="$VENV_DIR/.deps.stamp"
  REQ_HASH=$(shasum -a 256 requirements.txt | awk '{print $1}')
  NEED_INSTALL=0
  if [ ! -f "$STAMP_FILE" ]; then NEED_INSTALL=1; else PREV=$(cat "$STAMP_FILE"); [ "$REQ_HASH" != "$PREV" ] && NEED_INSTALL=1; fi
  # 잘못된 백포트 패키지 제거 (표준 asyncio를 덮어쓰는 문제 방지)
  $VENV_PIP uninstall -y asyncio >/dev/null 2>&1 || true
  if [ $NEED_INSTALL -eq 1 ]; then
    echo -e "${YELLOW}📦 패키지(변경 감지) 설치/업데이트 중...${NC}"
    $VENV_PIP install -r requirements.txt
    if [ $? -ne 0 ]; then
      echo -e "${RED}❌ 패키지 설치에 실패했습니다. 인터넷 연결 또는 프록시 설정을 확인해주세요.${NC}"
      echo "창을 닫으려면 아무 키나 누르세요..."; read -n 1; exit 1
    fi
    echo "$REQ_HASH" > "$STAMP_FILE"
    echo -e "${GREEN}✅ 패키지 설치/업데이트 완료${NC}"
  fi
  # Supabase 클라이언트 강제 업데이트(프록시 인자 이슈 방지)
  $VENV_PIP show supabase >/dev/null 2>&1
  if [ $? -eq 0 ]; then
    VER=$($VENV_PIP show supabase | awk '/Version/{print $2}')
    python - <<'PY'
import os, sys
ver=os.environ.get('VER','0')
from packaging.version import Version
if Version(ver)<Version('2.6.0'):
    sys.exit(1)
sys.exit(0)
PY
    if [ $? -ne 0 ]; then
      echo -e "${YELLOW}📦 Supabase 클라이언트 업데이트 중(>=2.6.0)...${NC}"
      $VENV_PIP install --upgrade supabase==2.6.0
    fi
  else
    echo -e "${YELLOW}📦 Supabase 클라이언트 설치 중(2.6.0)...${NC}"
    $VENV_PIP install supabase==2.6.0
  fi
fi

# Force unbuffered output for Python
export PYTHONUNBUFFERED=1
# Avoid proxy-related issues for Supabase client
unset HTTP_PROXY HTTPS_PROXY http_proxy https_proxy

# 메인 서버 실행 (현재 쉘 프로세스를 대체)
exec "$VENV_PY" main.py
STATUS=$?  # exec 실패 시에만 이 줄에 도달

# 종료 메시지
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
if [ $STATUS -eq 0 ]; then
  echo -e "${GREEN}✅ 프로그램이 정상적으로 종료되었습니다.${NC}"
else
  echo -e "${RED}❌ 프로그램이 오류로 종료되었습니다. 위 로그를 확인하세요.${NC}"
fi
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "창을 닫으려면 아무 키나 누르세요..."
read -n 1
