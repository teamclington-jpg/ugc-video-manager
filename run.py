#!/usr/bin/env python3
"""
UGC Video Manager - 간편 실행 스크립트
이 파일을 더블클릭하면 프로그램이 시작됩니다.
"""

import os
import sys
import time
import subprocess
from pathlib import Path

# 프로젝트 루트 경로 설정
PROJECT_ROOT = Path(__file__).parent
os.chdir(PROJECT_ROOT)

def check_python():
    """Python 버전 체크"""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 이상이 필요합니다.")
        print(f"현재 버전: Python {sys.version}")
        input("\n엔터를 눌러 종료...")
        sys.exit(1)

def check_venv():
    """가상환경 확인 및 생성 (.venv 우선)"""
    preferred = PROJECT_ROOT / ".venv"
    fallback = PROJECT_ROOT / "venv"
    venv_path = preferred if preferred.exists() else fallback

    if not venv_path.exists():
        print("🔧 가상환경 생성 중...")
        # 기본적으로 .venv로 생성
        venv_path = preferred
        subprocess.run([sys.executable, "-m", "venv", str(venv_path)])
        print("✅ 가상환경 생성 완료")

    # 가상환경 Python 경로
    if os.name == 'nt':  # Windows
        python_path = venv_path / "Scripts" / "python.exe"
        pip_path = venv_path / "Scripts" / "pip.exe"
    else:  # Mac/Linux
        python_path = venv_path / "bin" / "python"
        pip_path = venv_path / "bin" / "pip"

    return str(python_path), str(pip_path), str(venv_path)

def install_dependencies(pip_path: str, venv_path: str):
    """필요한 패키지 설치 (요구사항 변경 시 자동 설치)"""
    requirements_file = PROJECT_ROOT / "requirements.txt"
    if not requirements_file.exists():
        return

    print("📦 필요한 패키지 확인 중...")

    stamp = Path(venv_path) / ".deps.stamp"
    req_hash = None
    try:
        import hashlib
        req_hash = hashlib.sha256(requirements_file.read_bytes()).hexdigest()
        prev = stamp.read_text().strip() if stamp.exists() else ""
    except Exception:
        prev = ""

    need_install = (req_hash != prev)

    if need_install:
        print("📦 패키지 설치/업데이트 중... (시간이 걸릴 수 있습니다)")
        try:
            subprocess.run([pip_path, "install", "-r", "requirements.txt"], check=False)
            if req_hash:
                stamp.write_text(req_hash)
            print("✅ 패키지 설치 완료")
        except Exception as e:
            print(f"⚠️ 패키지 설치 중 오류: {e}")

def check_env():
    """환경변수 파일 확인"""
    env_file = PROJECT_ROOT / ".env"
    env_example = PROJECT_ROOT / ".env.example"
    
    if not env_file.exists():
        if env_example.exists():
            print("⚠️ .env 파일이 없습니다. .env.example을 복사합니다...")
            import shutil
            shutil.copy(env_example, env_file)
            print("✅ .env 파일 생성됨 - API 키를 설정해주세요!")
        else:
            print("❌ .env 파일이 없습니다!")
            input("\n엔터를 눌러 종료...")
            sys.exit(1)

def run_application(python_path):
    """메인 애플리케이션 실행"""
    print("""
╔══════════════════════════════════════════════════╗
║       UGC Video Manager 시작 중...              ║
║                                                  ║
║  감시 폴더:                                      ║
║  /Users/thecity17/Desktop/teamclingotondrive/   ║
║  상품쇼츠DB                                      ║
║                                                  ║
║  웹 인터페이스:                                  ║
║  http://localhost:8000                          ║
║                                                  ║
║  API 문서:                                       ║
║  http://localhost:8000/docs                     ║
║                                                  ║
║  종료하려면 Ctrl+C 또는 창을 닫으세요           ║
╚══════════════════════════════════════════════════╝
    """)
    
    try:
        # main.py 실행
        print(f"[디버그] Python 경로: {python_path}")
        result = subprocess.run([python_path, "main.py"])
        if result.returncode != 0:
            print(f"❌ 앱이 비정상 종료되었습니다 (코드 {result.returncode}). 로그를 확인하세요.")
            input("\n엔터를 눌러 종료...")
    except KeyboardInterrupt:
        print("\n\n👋 프로그램을 종료합니다...")
        time.sleep(1)

def main():
    """메인 실행 함수"""
    try:
        print("🚀 UGC Video Manager 시작 준비 중...\n")
        
        # 1. Python 버전 체크
        check_python()
        
        # 2. 가상환경 설정
        python_path, pip_path, venv_path = check_venv()
        
        # 3. 의존성 설치
        install_dependencies(pip_path, venv_path)

        # 3.5 핵심 모듈 사전 점검
        print("🧪 핵심 모듈 점검 중...")
        preflight = subprocess.run([
            python_path,
            "-c",
            (
                "import importlib, sys;\n"
                "mods=['fastapi','uvicorn','watchdog.observers','pydantic_settings','loguru'];\n"
                "missing=[m for m in mods if importlib.util.find_spec(m) is None];\n"
                "sys.exit(1 if missing else 0)"
            )
        ])
        if preflight.returncode != 0:
            print("❌ 필수 패키지가 누락되었습니다. 설치를 다시 시도합니다...")
            install_dependencies(pip_path, venv_path)
            print("다시 시도 후에도 문제가 지속되면 인터넷 연결 또는 프록시 설정을 확인하세요.")
            # 계속 진행하여 오류 메시지를 노출
        
        # 4. 환경변수 확인
        check_env()
        
        # 5. 애플리케이션 실행
        run_application(python_path)
        
    except Exception as e:
        print(f"\n❌ 오류가 발생했습니다: {e}")
        input("\n엔터를 눌러 종료...")
        sys.exit(1)

if __name__ == "__main__":
    main()
