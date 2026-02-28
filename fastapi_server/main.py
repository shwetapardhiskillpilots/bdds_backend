from fastapi import FastAPI
from routers import master, form, auth, media, dashboard, admin, sp_authority
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

app = FastAPI(title="BDDS FastAPI Mirror")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve media files (mirroring Django media)
if not os.path.exists("media"):
    os.makedirs("media")
app.mount("/media", StaticFiles(directory="media"), name="media")

# Include routers - mirroring exact Django paths
app.include_router(auth.router)
app.include_router(master.router)
app.include_router(form.router)
app.include_router(media.router)
app.include_router(dashboard.router)
app.include_router(admin.router)
app.include_router(sp_authority.router)

@app.get("/")
async def root():
    return {"message": "BDDS FastAPI Mirror is running"}

@app.on_event("startup")
async def warm_pool():
    """Pre-warm the DB connection pool on startup to avoid cold-start latency."""
    from database import engine
    from sqlalchemy import text
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    print("✅ DB connection pool warmed up")
