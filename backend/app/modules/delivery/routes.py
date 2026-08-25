"""
Routes stub — to be implemented in Phase 1+.
"""
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def module_health():
    return {"module": "delivery", "status": "ok"}
