#!/usr/bin/env python3
"""
Simple startup script for UGC Video Manager
"""

import os
import sys
import time

# Add project path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    print("=" * 60)
    print("         UGC Video Manager v1.0.0")
    print("     영상 자동 처리 및 업로드 큐 관리 시스템")
    print("=" * 60)
    
    # Check environment
    if not os.path.exists(".env"):
        print("\n❌ ERROR: .env 파일이 없습니다!")
        print("API 키를 설정해 주세요.")
        return
    
    print("\n🔍 환경 확인 중...")
    
    try:
        from src.config import settings
        print("✅ 설정 로드 완료")
        
        print(f"📁 감시 폴더: {settings.watch_folder_path}")
        print(f"🌐 API 서버: http://localhost:{settings.api_port}")
        print(f"📊 API 문서: http://localhost:{settings.api_port}/docs")
        
    except Exception as e:
        print(f"❌ 설정 로드 실패: {e}")
        return
    
    print("\n🚀 서버 시작 중...")
    print("종료하려면 Ctrl+C를 누르세요\n")
    
    try:
        # Use minimal main for now
        from main_minimal import main as run_main
        import asyncio
        
        # Run the application
        asyncio.run(run_main())
        
    except KeyboardInterrupt:
        print("\n\n✅ 사용자에 의해 종료됨")
    except ImportError as e:
        print(f"\n❌ Import 오류: {e}")
        print("필요한 패키지가 설치되지 않았습니다.")
        print("다음 명령어를 실행하세요:")
        print("  pip3 install -r requirements.txt")
    except Exception as e:
        print(f"\n❌ 실행 오류: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n프로그램이 종료되었습니다.")

if __name__ == "__main__":
    main()
    input("\n엔터를 눌러 종료...")