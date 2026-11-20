from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.config import settings
from backend.app.database import engine, Base, SessionLocal
from backend.app.seeder import seed_database
from backend.app.clock import get_app_now
from backend.app.models import Company
from backend.app.routers import (
    auth, teams, measurables, issues, todos, rocks, meetings, report
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure tables exist
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # Only seed if empty
        if not db.query(Company).first():
            seed_database(db=db)
    except Exception as e:
        print(f"Startup notice: {e}")
    finally:
        db.close()
    yield

app = FastAPI(
    title=settings.APP_NAME,
    description="Level 10 Meeting Platform for EOS",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(teams.router)
app.include_router(measurables.router)
app.include_router(issues.router)
app.include_router(todos.router)
app.include_router(rocks.router)
app.include_router(meetings.router)
app.include_router(report.router)

@app.get("/health")
def health_check():
    return {"status": "ok", "app_now": get_app_now().strftime("%Y-%m-%dT%H:%M:%SZ")}
