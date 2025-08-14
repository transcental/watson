import asyncio
import logging
import uvicorn

from watson.config import config


try:
    import uvloop
    
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
except ImportError:
    pass

logging.basicConfig(level=logging.DEBUG if config.environment == "development" else logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")


def start():
    uvicorn.run(
        "watson.fastapi:app",
        host="0.0.0.0",
        port=config.port,
        log_level="info" if config.environment == "development" else "warning",
        reload=config.environment == "development"
    )
    

if __name__ == "__main__":
    start()
