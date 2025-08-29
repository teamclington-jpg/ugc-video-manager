#!/usr/bin/env python3
"""
UGC Video Manager - Simple Server
"""

import asyncio
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

print("\n" + "="*60)
print("     UGC Video Manager v1.0.0")
print("     영상 자동 처리 및 업로드 큐 관리 시스템")
print("="*60)

async def main():
    """Run the application"""
    
    # Load configuration
    try:
        from src.config import settings
        print(f"\n✅ 설정 로드 완료")
        print(f"📁 감시 폴더: {settings.watch_folder_path}")
    except Exception as e:
        print(f"\n❌ 설정 로드 실패: {e}")
        print("src/config.py 파일을 확인하세요.")
        return
    
    # Start API server
    try:
        from fastapi import FastAPI, Response
        from fastapi.middleware.cors import CORSMiddleware
        import uvicorn
        
        # Create FastAPI app
        app = FastAPI(
            title="UGC Video Manager",
            version="1.0.0",
            description="영상 자동 처리 및 업로드 큐 관리 시스템"
        )
        
        # Add CORS
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Basic routes
        @app.get("/")
        async def root():
            html = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>UGC Video Manager</title>
                <style>
                    body { 
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                        max-width: 800px;
                        margin: 50px auto;
                        padding: 20px;
                        background: #f5f5f5;
                    }
                    .container {
                        background: white;
                        border-radius: 10px;
                        padding: 30px;
                        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                    }
                    h1 { 
                        color: #333;
                        border-bottom: 2px solid #4CAF50;
                        padding-bottom: 10px;
                    }
                    .status { 
                        background: #4CAF50;
                        color: white;
                        padding: 10px 20px;
                        border-radius: 5px;
                        display: inline-block;
                        margin: 20px 0;
                    }
                    .info {
                        background: #f0f0f0;
                        padding: 15px;
                        border-radius: 5px;
                        margin: 10px 0;
                    }
                    .link {
                        color: #4CAF50;
                        text-decoration: none;
                        font-weight: bold;
                    }
                    .link:hover {
                        text-decoration: underline;
                    }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>🎥 UGC Video Manager</h1>
                    <div class="status">✅ 서버 실행 중</div>
                    
                    <div class="info">
                        <h3>📊 시스템 상태</h3>
                        <p>버전: v1.0.0</p>
                        <p>상태: 정상 작동 중</p>
                        <p>감시 폴더: """ + str(settings.watch_folder_path) + """</p>
                    </div>
                    
                    <div class="info">
                        <h3>🔗 유용한 링크</h3>
                        <p>📚 <a href="/docs" class="link">API 문서</a></p>
                        <p>❤️ <a href="/health" class="link">헬스 체크</a></p>
                    </div>
                    
                    <div class="info">
                        <h3>🚀 기능</h3>
                        <ul>
                            <li>영상 자동 감지</li>
                            <li>AI 기반 영상 분석</li>
                            <li>채널 자동 매칭</li>
                            <li>SEO 최적화</li>
                            <li>업로드 큐 관리</li>
                        </ul>
                    </div>
                </div>
            </body>
            </html>
            """
            return Response(content=html, media_type="text/html")
        
        @app.get("/health")
        async def health():
            return {
                "status": "healthy",
                "version": "1.0.0",
                "message": "UGC Video Manager is running"
            }
        
        @app.get("/api/status")
        async def status():
            return {
                "server": "running",
                "watch_folder": settings.watch_folder_path,
                "api_docs": f"http://localhost:{settings.api_port}/docs"
            }
        
        # Configure server
        config = uvicorn.Config(
            app=app,
            host=settings.api_host,
            port=settings.api_port,
            log_level="info",
            access_log=True
        )
        
        server = uvicorn.Server(config)
        
        print(f"\n🚀 서버 시작 중...")
        print(f"🌐 웹 인터페이스: http://localhost:{settings.api_port}")
        print(f"📊 API 문서: http://localhost:{settings.api_port}/docs")
        print(f"\n종료하려면 Ctrl+C를 누르세요\n")
        print("-" * 60)
        
        # Start server
        await server.serve()
        
    except ImportError as e:
        print(f"\n❌ 필수 패키지 누락: {e}")
        print("\n다음 명령어로 설치하세요:")
        print("pip3 install fastapi uvicorn python-dotenv")
    except Exception as e:
        print(f"\n❌ 서버 오류: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n✅ 사용자에 의해 종료됨")
    except Exception as e:
        print(f"\n❌ 애플리케이션 오류: {e}")
        import traceback
        traceback.print_exc()