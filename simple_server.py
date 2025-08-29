#!/usr/bin/env python3
"""
Simple HTTP Server for UGC Video Manager
No external dependencies required
"""

import http.server
import socketserver
import json
from datetime import datetime

PORT = 8000

class MyHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            
            html = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>UGC Video Manager</title>
                <meta charset="utf-8">
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
                        <p>시간: """ + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + """</p>
                    </div>
                    
                    <div class="info">
                        <h3>🔗 API 엔드포인트</h3>
                        <p>📊 <a href="/api/status">상태 확인</a></p>
                        <p>❤️ <a href="/health">헬스 체크</a></p>
                    </div>
                    
                    <div class="info">
                        <h3>🚀 주요 기능</h3>
                        <ul>
                            <li>영상 자동 감지 및 분석</li>
                            <li>AI 기반 콘텐츠 분석</li>
                            <li>채널 자동 매칭</li>
                            <li>SEO 메타데이터 생성</li>
                            <li>업로드 큐 관리</li>
                        </ul>
                    </div>
                    
                    <div class="info">
                        <h3>📁 감시 폴더</h3>
                        <p>/Users/thecity17/Desktop/teamclingotondrive/상품쇼츠DB/</p>
                    </div>
                </div>
            </body>
            </html>
            """
            self.wfile.write(html.encode())
            
        elif self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = {
                "status": "healthy",
                "timestamp": datetime.now().isoformat()
            }
            self.wfile.write(json.dumps(response).encode())
            
        elif self.path == '/api/status':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = {
                "server": "running",
                "version": "1.0.0",
                "watch_folder": "/Users/thecity17/Desktop/teamclingotondrive/상품쇼츠DB/",
                "timestamp": datetime.now().isoformat()
            }
            self.wfile.write(json.dumps(response).encode())
        else:
            super().do_GET()

if __name__ == "__main__":
    print("\n" + "="*60)
    print("     UGC Video Manager v1.0.0")
    print("     영상 자동 처리 및 업로드 큐 관리 시스템")
    print("="*60)
    print(f"\n🚀 서버 시작 중...")
    print(f"🌐 웹 인터페이스: http://localhost:{PORT}")
    print(f"📊 API 상태: http://localhost:{PORT}/api/status")
    print(f"\n종료하려면 Ctrl+C를 누르세요\n")
    print("-" * 60)
    
    try:
        with socketserver.TCPServer(("", PORT), MyHandler) as httpd:
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n\n✅ 사용자에 의해 종료됨")
    except Exception as e:
        print(f"\n❌ 서버 오류: {e}")