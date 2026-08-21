"""AWS Lambda entrypoints.

Mangum adapts Lambda's (event, context) convention to ASGI, so the FastAPI app
in app/main.py runs unmodified — nothing in the application code knows it is
running on Lambda.
"""

from mangum import Mangum

from app.main import app

# lifespan="off": nothing to run at startup, and Lambda freezes the execution
# environment as soon as a response returns.
handler = Mangum(app, lifespan="off")


def seed_handler(event, context):  # noqa: ANN001, ARG001
    """One-off: create tables and load the seed CSVs.

    Invoked manually rather than on startup, so concurrent cold starts can't
    race each other creating schema. Runs inside the VPC, which is what lets the
    database stay private with no public endpoint and no bastion.

    Pass {"reset": true} to clear items and reload them from the CSVs.
    """
    from scripts.seed import seed

    reset = bool((event or {}).get("reset"))
    counts = seed(reset=reset)
    return {"ok": True, "reset": reset, **counts}
