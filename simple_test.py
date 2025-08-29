#!/usr/bin/env python3
print("Python script is running!")
print("Working directory:", __file__)

import sys
print("Python version:", sys.version)

try:
    import asyncio
    print("asyncio imported successfully")
except Exception as e:
    print(f"Error importing asyncio: {e}")

print("Script completed!")