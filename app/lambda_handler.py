"""AWS Lambda entrypoints.

Mangum adapts Lambda's (event, context) calling convention to ASGI, so the
FastAPI app in app/main.py runs unmodified — nothing in the application code
knows it is on Lambda.
"""

from mangum import Mangum

from app.main import app

# lifespan="off": no startup/shutdown events to run, and Lambda freezes the
# execution environment the moment a response returns.
handler = Mangum(app, lifespan="off")


def seed_handler(event, context):  # noqa: ANN001, ARG001
    """One-off: create tables and load the seed CSVs.

    Invoked manually (`aws lambda invoke --function-name …-seed`) rather than on
    startup, so concurrent cold starts can't race each other creating schema.
    Runs inside the VPC, which is what lets the database stay private with no
    public endpoint and no bastion.
    """
    from scripts.seed import seed

    seed()
    return {"ok": True}
