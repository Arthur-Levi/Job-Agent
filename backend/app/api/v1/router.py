from fastapi import APIRouter

from app.api.v1 import applications, auth, jobs, profile

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(profile.router)
api_router.include_router(jobs.router)
api_router.include_router(applications.router)
