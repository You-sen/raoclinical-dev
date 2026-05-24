

from fastapi import APIRouter, HTTPException, Depends, Form
from .mentor_match import mentor_match_service
import asyncio
router = APIRouter()
mentor_match = mentor_match_service()

@router.get("/mentor_match")
async def mentor_match(
     user_id: str,
     gig_id :str
):
     try:
          result = await mentor_match_service().get_similar_mentors(user_id,gig_id)
          return result
     except Exception as e:
          raise HTTPException(status_code=500, detail=str(e))