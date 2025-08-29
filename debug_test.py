#!/usr/bin/env python3
"""
Debug test to identify the issue
"""

import sys
import traceback

print("=" * 60)
print("DEBUG TEST - Finding the issue")
print("=" * 60)

# Test 1: Python version
print(f"\n1. Python version: {sys.version}")

# Test 2: Import test
print("\n2. Testing imports...")
try:
    import fastapi
    print("   ✅ FastAPI imported")
except ImportError as e:
    print(f"   ❌ FastAPI not found: {e}")
    
try:
    import uvicorn
    print("   ✅ Uvicorn imported")
except ImportError as e:
    print(f"   ❌ Uvicorn not found: {e}")

try:
    from dotenv import load_dotenv
    print("   ✅ python-dotenv imported")
except ImportError as e:
    print(f"   ❌ python-dotenv not found: {e}")

# Test 3: Config loading
print("\n3. Testing config loading...")
try:
    from src.config import settings
    print(f"   ✅ Config loaded")
    print(f"   API Port: {settings.api_port}")
except Exception as e:
    print(f"   ❌ Config error: {e}")
    traceback.print_exc()

# Test 4: Simple server test
print("\n4. Testing simple server...")
try:
    from fastapi import FastAPI
    import uvicorn
    import asyncio
    
    app = FastAPI()
    
    @app.get("/test")
    def test():
        return {"status": "ok"}
    
    print("   ✅ FastAPI app created")
    
    # Try to create server config
    config = uvicorn.Config(app, host="0.0.0.0", port=8000, log_level="debug")
    print("   ✅ Uvicorn config created")
    
    print("\n✅ All tests passed! Server should work.")
    print("\nNow trying to run the actual app.py...")
    
except Exception as e:
    print(f"   ❌ Server test failed: {e}")
    traceback.print_exc()

# Test 5: Run app.py
print("\n5. Testing app.py execution...")
try:
    with open("app.py", "r") as f:
        app_content = f.read()
    print("   ✅ app.py file found and readable")
    
    # Check if it's a syntax issue
    compile(app_content, "app.py", "exec")
    print("   ✅ app.py has valid Python syntax")
    
    print("\nTrying to execute app.py...")
    exec(app_content)
    
except SyntaxError as e:
    print(f"   ❌ Syntax error in app.py: {e}")
except FileNotFoundError:
    print("   ❌ app.py not found")
except Exception as e:
    print(f"   ❌ Error executing app.py: {e}")
    traceback.print_exc()

print("\n" + "=" * 60)
print("Debug test complete")
print("=" * 60)