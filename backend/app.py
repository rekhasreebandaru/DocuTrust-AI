from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from database import close_mongo_connection, connect_to_mongo
from routes import router
from utils import client_ip, ensure_runtime_dirs, rate_limiter, settings

@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_runtime_dirs()
    await connect_to_mongo()
    yield
    await close_mongo_connection()

app = FastAPI(title=settings.app_name, version='1.1.0', lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=[settings.frontend_origin], allow_credentials=True, allow_methods=['*'], allow_headers=['*'])

@app.middleware('http')
async def rate_limit_middleware(request: Request, call_next):
    if request.url.path.startswith('/api'):
        key = client_ip(request)
        if not rate_limiter.is_allowed(key):
            return JSONResponse(status_code=429, content={'detail': f'Rate limit exceeded: max {rate_limiter.max_requests} requests per {rate_limiter.window_seconds}s'})
    return await call_next(request)

app.include_router(router)

if __name__ == '__main__':
    import uvicorn
    uvicorn.run('app:app', host=settings.api_host, port=settings.api_port, reload=True)
