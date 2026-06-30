from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import close_mongo_connection, connect_to_mongo
from routes import router
from utils import ensure_runtime_dirs, settings

@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_runtime_dirs()
    await connect_to_mongo()
    yield
    await close_mongo_connection()

app = FastAPI(title=settings.app_name, version='1.0.0', lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=[settings.frontend_origin], allow_credentials=True, allow_methods=['*'], allow_headers=['*'])
app.include_router(router)

if __name__ == '__main__':
    import uvicorn
    uvicorn.run('app:app', host=settings.api_host, port=settings.api_port, reload=True)
