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

# No CORSMiddleware on purpose: this is a machine-consumed API with no browser
# origin to relax same-origin for. Add it only when a browser app needs it.


# --- Docs behind auth, written but not enforced ------------------------------
# /docs, /redoc and /openapi.json are public above. That is a deliberate choice
# for this demo so the API is explorable. For an internet-facing deployment,
# replace the FastAPI(...) call with the version below and uncomment the two
# routes — the schema then requires X-API-Key, and the docs page with it.
#
# from fastapi import Depends
# from fastapi.openapi.docs import get_swagger_ui_html
# from fastapi.openapi.utils import get_openapi
# from fastapi.responses import HTMLResponse, JSONResponse
# from app.security import require_api_key
#
# app = FastAPI(
#     title=settings.app_name,
#     version="0.1.0",
#     docs_url=None,
#     redoc_url=None,
#     openapi_url=None,
# )
#
# @app.get("/openapi.json", include_in_schema=False,
#          dependencies=[Depends(require_api_key)])
# def openapi_schema() -> JSONResponse:
#     return JSONResponse(
#         get_openapi(title=app.title, version=app.version, routes=app.routes)
#     )
#
# @app.get("/docs", include_in_schema=False,
#          dependencies=[Depends(require_api_key)])
# def swagger_ui() -> HTMLResponse:
#     return get_swagger_ui_html(openapi_url="/openapi.json", title=app.title)
# -----------------------------------------------------------------------------
