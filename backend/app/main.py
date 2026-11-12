import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import select, func

from .database import engine, Base, SessionLocal
from .models import User
from .seed import seed_database
from .routes import (
    auth, users, courses, assignments, submissions, quizzes, grades, resources, admin, logs,
    discussions, modules, files, peer_reviews, attendance
)


from .migrate_db import run_migrations


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure all tables exist and columns are synced
    Base.metadata.create_all(bind=engine)
    try:
        run_migrations()
    except Exception as e:
        print(f"Migration note: {e}")

    # Check if database needs seeding
    db = SessionLocal()
    try:
        user_count = db.scalar(select(func.count(User.id))) or 0
        if user_count == 0:
            print("Empty database detected. Running initial seed...")
            seed_database()
        else:
            print(f"Database already contains {user_count} users. Seeding verified.")
    except Exception as e:
        print(f"Startup database check note: {e}")
    finally:
        db.close()

    yield


app = FastAPI(
    title="GuardSLM Research LMS",
    description="A controlled Moodle-like LMS environment for evaluating Small Language Models as browser-agent authorization guards.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS Configuration
cors_origins_env = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
origins = [o.strip() for o in cors_origins_env.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if origins else ["*"],
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1|0\.0\.0\.0)(:[0-9]+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["System"])
def health_check():
    """Healthcheck endpoint for system uptime and monitoring."""
    return {"status": "ok", "service": "GuardSLM Research LMS API", "version": "1.0.0"}


# Register API Routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(courses.router)
app.include_router(courses.announcements_router)
app.include_router(assignments.router)
app.include_router(submissions.router)
app.include_router(quizzes.router)
app.include_router(grades.router)
app.include_router(resources.router)
app.include_router(admin.router)
app.include_router(logs.router)
app.include_router(discussions.router)
app.include_router(modules.router)
app.include_router(files.router)
app.include_router(peer_reviews.router)
app.include_router(attendance.router)
