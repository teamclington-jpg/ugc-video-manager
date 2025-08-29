#!/usr/bin/env python3
"""
Install essential dependencies for UGC Video Manager
"""

import subprocess
import sys

print("=" * 60)
print("     UGC Video Manager - 의존성 설치")
print("=" * 60)
print()

# Essential packages only (for quick start)
essential_packages = [
    "python-dotenv",
    "fastapi",
    "uvicorn[standard]",
    "aiofiles",
    "pydantic",
    "pydantic-settings"
]

print("🔧 필수 패키지 설치 중...")
print("설치할 패키지:")
for pkg in essential_packages:
    print(f"  - {pkg}")
print()

# Install packages
for package in essential_packages:
    print(f"📦 Installing {package}...")
    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", package],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        print(f"✅ {package} 설치 완료")
    except subprocess.CalledProcessError:
        print(f"❌ {package} 설치 실패")
    except Exception as e:
        print(f"❌ 오류: {e}")

print()
print("=" * 60)
print("✅ 필수 패키지 설치 완료!")
print("이제 프로그램을 실행할 수 있습니다.")
print("=" * 60)