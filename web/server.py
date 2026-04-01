#!/usr/bin/env python3
"""
Aizen Dashboard Server - Start both backend and frontend

Usage:
    python -m web.server
    python -m web.server --port 8000
    python -m web.server --no-frontend
"""

import argparse
import subprocess
import sys
import os
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description="Start Aizen Dashboard")
    parser.add_argument("--port", type=int, default=8000, help="Port for backend")
    parser.add_argument("--no-frontend", action="store_true", help="Don't open frontend")
    parser.add_argument("--host", default="0.0.0.0", help="Host for backend")
    args = parser.parse_args()
    
    # Add parent to path
    parent = Path(__file__).parent.parent
    sys.path.insert(0, str(parent))
    
    # Start backend
    os.environ["PORT"] = str(args.port)
    
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║           Aizen Dashboard v3.0                               ║
╠══════════════════════════════════════════════════════════════╣
║  Backend:  http://localhost:{args.port:<5}                          ║
║  API Docs: http://localhost:{args.port:<5}/docs                      ║
║  Frontend: http://localhost:{args.port:<5}/static/index.html           ║
╚══════════════════════════════════════════════════════════════╝
""")
    
    # Import and run
    from web.backend.main import app
    import uvicorn
    
    # Mount static files for frontend
    frontend_path = Path(__file__).parent / "frontend"
    if frontend_path.exists():
        from fastapi.staticfiles import StaticFiles
        app.mount("/static", StaticFiles(directory=str(frontend_path), html=True), name="static")
    
    uvicorn.run(app, host=args.host, port=args.port)

if __name__ == "__main__":
    main()
