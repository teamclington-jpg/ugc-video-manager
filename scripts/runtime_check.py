#!/usr/bin/env python3
"""
Runtime self-check: import core modules and create FastAPI app, writing results to a log file.
"""

import sys
import os
import importlib
import traceback
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
os.chdir(PROJECT_ROOT)
sys.path.insert(0, str(PROJECT_ROOT))

log_path = PROJECT_ROOT / "runtime_check.log"


def write(line: str):
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(line.rstrip("\n") + "\n")


def main():
    # reset log
    if log_path.exists():
        log_path.unlink()

    write("=== Runtime Check ===")
    write(f"Python: {sys.version}")
    write(f"CWD: {os.getcwd()}")

    modules = [
        "src.config.settings",
        "src.utils.logger",
        "src.utils.encryption",
        "src.utils.database",
        "src.api.main",
        "src.watchers.video_watcher",
        "src.watchers.enhanced_video_watcher",
        "src.analyzers.video_analyzer",
        "src.generators.seo_generator",
        "src.matchers.channel_matcher",
        "src.matchers.product_matcher",
        "src.queue.queue_manager",
        "src.processors.video_processor",
    ]

    write("\n[Import Check]")
    for m in modules:
        try:
            importlib.import_module(m)
            write(f"OK {m}")
        except Exception as e:
            write(f"ERR {m} :: {e}")
            tb = traceback.format_exc()
            write(tb)

    # App creation check
    try:
        write("\n[App Creation]")
        from src.api.main import create_app

        app = create_app()
        write(f"App title: {app.title}")
        routes = sorted([r.path for r in app.routes])
        write(f"Routes: {routes[:12]}")
    except Exception as e:
        write(f"App creation error: {e}")
        write(traceback.format_exc())

    write("\n=== Done ===")


if __name__ == "__main__":
    main()


