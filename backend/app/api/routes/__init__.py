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


__all__ = [
    "health_router",
    "meetings_router",
    "speakers_router",
    "analysis_router",
    "management_router",
    "media_router",
    "exports_router",
]