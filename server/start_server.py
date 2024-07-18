from fastapi import FastAPI
import uvicorn, asyncio
from cyberchat_plugin import router as cyberchat_router

async def main():
    app = FastAPI(title="Remote API Routers", description="For Inference easily")
    app.include_router(cyberchat_router)
    config = uvicorn.Config(app, host="0.0.0.0", port=5010, log_level="error")
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Server has been shut down.")