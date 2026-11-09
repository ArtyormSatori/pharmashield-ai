#!/usr/bin/env python3
"""
PharmaShield AI - Local Web Application Server Runner
Launches the FastAPI application on http://127.0.0.1:8000 (or specified PORT)
"""

import os
import sys
import uvicorn
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))


def main():
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))
    print("\n" + "=" * 65)
    print(" 🛡️  PHARMASHIELD AI - WEB APPLICATION SERVER")
    print("=" * 65)
    print(f" Serving Clinical Safety Intelligence UI at: http://{host}:{port}")
    print(f" API Documentation (OpenAPI/Swagger):         http://{host}:{port}/docs")
    print(f" Empirical Clinical Benchmark endpoint:      http://{host}:{port}/api/benchmark")
    print("=" * 65 + "\n")

    uvicorn.run("app.main:app", host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
