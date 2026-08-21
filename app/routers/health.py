from fastapi import APIRouter

router = APIRouter(tags=["ops"])


@router.get("/health")
def health() -> dict[str, str]:
    """Load-balancer target. No auth, no database — it answers 'is the process up'."""
    return {"status": "ok"}
