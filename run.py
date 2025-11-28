#!/usr/bin/env python3
"""
Simple startup script for JustData.
"""

import uvicorn
from core.config.settings import get_settings

if __name__ == "__main__":
    settings = get_settings()
    
    print(f"🚀 Starting JustData v{settings.app_version}")
    print(f"🌐 Server will be available at http://{settings.api_host}:{settings.api_port}")
    print(f"📚 API documentation: http://{settings.api_host}:{settings.api_port}/docs")
    
    uvicorn.run(
        "api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )
