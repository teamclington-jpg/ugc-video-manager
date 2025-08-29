#!/usr/bin/env python3
"""
Run FastAPI app with uvicorn, with robust logging for debugging.
"""

import os
import sys
import traceback


def main():
    os.environ.setdefault("DEBUG_MODE", "1")
    os.environ.setdefault("DEVELOPMENT", "1")

    print("[runner] DEBUG_MODE=", os.environ.get("DEBUG_MODE"))
    print("[runner] DEVELOPMENT=", os.environ.get("DEVELOPMENT"))

    try:
        from src.config import settings  # noqa: F401
        print("[runner] settings imported")
    except Exception as e:
        print("[runner] settings import error:", e)
        print(traceback.format_exc())
        sys.exit(1)

    try:
        from src.api.main import app
        print("[runner] app imported; starting uvicorn...")
        import uvicorn
        uvicorn.run(
            app,
            host="127.0.0.1",
            port=8000,
            log_level="debug",
        )
    except Exception as e:
        print("[runner] uvicorn run error:", e)
        print(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()




