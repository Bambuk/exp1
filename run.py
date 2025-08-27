#!/usr/bin/env python3
"""Simple script to run the application."""

import uvicorn
from radiator.core.config import settings

if __name__ == "__main__":
    uvicorn.run(
        "radiator.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.RELOAD,
        log_level=settings.LOG_LEVEL.lower(),
    )
