"""
Dork Routes — Mark dorks as used.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from database import mark_dork_used
from services.dork_guard import generate_dork_hash

router = APIRouter()


class MarkDorkRequest(BaseModel):
    dork_text: str
    country: str = ""
    region: str = ""
    sector: str = ""


@router.post("/dorks/mark-used", summary="Mark a dork as used")
def mark_dork_as_used(req: MarkDorkRequest):
    """
    Mark a dork as used so it won't appear in future recommendations.
    Only call this when user clicks 'Use Dork' or 'Create Campaign'.
    """
    if not req.dork_text:
        raise HTTPException(status_code=400, detail="dork_text is required")

    dork_hash = generate_dork_hash(req.dork_text)
    mark_dork_used(
        dork_text=req.dork_text,
        dork_hash=dork_hash,
        country=req.country,
        region=req.region,
        sector=req.sector,
    )
    return {"status": "marked_used", "dork_hash": dork_hash}
