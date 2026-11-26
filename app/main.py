"""DistriFlow application entry point.  Run with:  uvicorn app.main:app --reload"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.templating import Jinja2Templates 
from fastapi import Request 

import app.models  # noqa: F401  (makes sure all 6 tables are registered)
from app.database import Base, engine
from app.routers import auth, customers, dashboard, trucks, users, staging, plans, pages


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Runs once at start-up: create any missing tables."""
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="DistriFlow", description="Route optimization and truck loading planning",
              version="1.0.0", lifespan=lifespan)

app.include_router(pages.router)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(trucks.router)
app.include_router(customers.router)
app.include_router(staging.router)   
app.include_router(plans.router) 
app.include_router(dashboard.router)



app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:8000",
        "http://localhost:8000",
        "http://127.0.0.1:5500",   # VS Code Live Server
        "http://localhost:5500",
    ],
    allow_credentials=True,        # required for the HttpOnly auth cookie
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/health", tags=["System"])
def health_check():
    """Public endpoint to check that the server is running."""
    return {"status": "ok"}