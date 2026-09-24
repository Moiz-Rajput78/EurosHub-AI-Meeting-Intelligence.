from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_db


router = APIRouter(
    tags=["Health"],
)


@router.get("/health")
def health_check() -> dict:
    return {
        "success": True,
        "message": "Meeting Intelligence backend is running",
    }


@router.get("/test-db")
def test_database(
    db: Session = Depends(get_db),
) -> dict:
    db.execute(text("SELECT 1"))

    return {
        "success": True,
        "message": "Database connection successful",
    }