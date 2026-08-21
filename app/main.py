from fastapi import FastAPI

from app.config import settings
from app.routers import health, items, reports, sites

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    summary="Asset reporting over sites and items.",
)

app.include_router(health.router)
app.include_router(sites.router)
app.include_router(items.router)
app.include_router(reports.router)

# No CORSMiddleware: this is a machine-consumed API with no browser origin to
# relax same-origin for. Add it only when a browser client actually appears.
