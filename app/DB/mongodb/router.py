from fastapi import APIRouter
from app.DB.mongodb.mongodb import MongoDB


router = APIRouter()

@router.get("/get_match_score/{user_id}/{gig_id}")
async def get_match_score(user_id: str,gig_id:str):
     try:
          mongodb = MongoDB()
          return await mongodb.get_match_score(user_id,gig_id)
     except Exception as e:
          raise e