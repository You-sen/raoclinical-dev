from fastapi import APIRouter, HTTPException, Depends, Form ,BackgroundTasks
from .user_skillgap import skillgap_service
from .user_skillgap_schema import UserSkillGapRequest,UserSkillGapResponse
from app.Services.match_gig.match_gig import MatchGig
from app.DB.mongodb.mongodb import MongoDB
router = APIRouter()
skillgap =skillgap_service()
mongodb = MongoDB()
match_gig = MatchGig()

async def background_task(user_id: str, gig_id: str, result: UserSkillGapResponse):
     try:
          # ✅ Convert Pydantic model to dict first
          result_dict = result.model_dump()

          skillgap_list = result_dict.get("skill_gap_of_user_with_gig", [])
          if skillgap_list:
               # Convert list to string for embedding
               skillgap_text = ", ".join(skillgap_list)
               embedding = await match_gig.get_embedding(skillgap_text)
               result_dict["embedding"] = embedding

          await mongodb.insert_skill_gap(user_id, gig_id, result_dict)

     except Exception as e:
          print(f"[SkillGap Background] Error: {e}")

@router.get("/user_skillgap")
async def user_skillgap(
     user_id: str,
     gig_id :str,
     background_tasks: BackgroundTasks
):
     try:
          result = await mongodb.get_skill_gap(user_id, gig_id)
          if result:
               return result
          else:
               result = await skillgap.get_response(user_id, gig_id)
               background_tasks.add_task(background_task, user_id, gig_id, result)
               return result

     except Exception as e:
          raise HTTPException(status_code=500, detail=str(e))

@router.post("/get_resume_by_user_id")
async def get_resume_by_user_id(
     user_id: str
):
     try:
          return await skillgap.get_full_resume_by_user_id(user_id)
     except Exception as e:
          raise HTTPException(status_code=500, detail=str(e))

