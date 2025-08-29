#!/usr/bin/env python3
"""
Simple test server to verify installation
"""

print("Starting test server...")

try:
    from fastapi import FastAPI
    import uvicorn
    
    app = FastAPI()
    
    @app.get("/")
    def read_root():
        return {"Hello": "World"}
    
    print("FastAPI loaded successfully!")
    print("Starting server on http://localhost:8000")
    print("Press Ctrl+C to stop")
    
    # Run server
    uvicorn.run(app, host="0.0.0.0", port=8000)
    
except ImportError as e:
    print(f"Error: {e}")
    print("\nPlease install dependencies:")
    print("pip3 install fastapi uvicorn")
except Exception as e:
    print(f"Server error: {e}")