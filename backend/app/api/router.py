from fastapi import APIRouter

from app.api.routes.analysis import (
    router as analysis_router,
)
from app.api.routes.exports import (
    router as exports_router,
)
from app.api.routes.health import (
    router as health_router,
)
from app.api.routes.management import (
    router as management_router,
)
from app.api.routes.media import (
    router as media_router,
)
from app.api.routes.meetings import (
    router as meetings_router,
)
from app.api.routes.speakers import (
    router as speakers_router,
)


api_router = APIRouter()


api_router.include_router(
    health_router
)

api_router.include_router(
    meetings_router
)

api_router.include_router(
    speakers_router
)

api_router.include_router(
    analysis_router
)

api_router.include_router(
    management_router
)

api_router.include_router(
    media_router
)

api_router.include_router(
    exports_router
)