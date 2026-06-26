from motor.motor_asyncio import AsyncIOMotorClient
from app.config.settings import settings
from bson import ObjectId
from datetime import datetime, timezone

class MongoDB:
     def __init__(self):
          self.client = AsyncIOMotorClient(settings.MONGODB_URL)
          self.db = self.client[settings.DB_NAME]
          self.user_collection = self.db['User']
          self.resume_collection = self.db['ResumeProfile']
          self.cover_letter_collection = self.db['CoverLetter']
          self.job_collection = self.db['Gig']
          self.recommended_skill_collection = self.db['RecommendedSkill']
          self.notify_gig_match = self.db["GigMatches"]
          self.skill_impact_collection = self.db['SkillImpact']
          self.matches_collection = self.db['Matches']
          self.clearityScore_collection = self.db['ClearityScore']
          self.activityLog_collection = self.db['ActivityLog']
          self.skillGap_collection = self.db['SkillGap']
          self.applied_gigs_collection = self.db['AppliedGigs']
          self.resume_profile_collection = self.db['ResumeProfile']
          self.resume_section_collection = self.db['ResumeSection']
          self.resume_section_item_collection = self.db['ResumeSectionItem']
          self.resume_skill_collection = self.db['Skill']
          self.mentor_collection = self.db['MentorProfile']
          self.mentorMatch_collection = self.db['MentorMatch']
          self.profile_score_collection = self.db['ProfileScore']



     def get_db(self):
          return self.db

     async def initial_index(self):
          await self.user_collection.create_index([('email', 1)], unique=True)
          await self.resume_collection.create_index([('userId', 1)])
          await self.cover_letter_collection.create_index([('userId', 1)])
          await self.job_collection.create_index([('userId', 1)])
          await self.recommended_skill_collection.create_index([('userId', 1)])
          await self.skill_impact_collection.create_index([('skill', 1)])
          await self.matches_collection.create_index([('userId', 1)])
          await self.clearityScore_collection.create_index([('userId', 1)])
          await self.activityLog_collection.create_index([('userId', 1),('createdAt', 1)])


     async def insert_resume_parse_info(self,user_id:str,user_resume:dict):
          try:
               user_id = ObjectId(user_id)
               user_resume['userId'] = user_id
               
               # comment: insert user resume
               result = await self.resume_collection.insert_one(user_resume)
               return {"message":"Resume parsed successfully","resume_id":str(result.inserted_id)}
               
          except Exception as e:
               raise e
          # end try
     async def get_resume_by_user_id(self,user_id:str):
          try:
               user_id = ObjectId(user_id)
               resume = await self.resume_collection.find_one({'userId':user_id},
               {
                    "_id":0,
                    "userId":0,
                    "embedding":0,
                    "createdAt":0,
                    "updatedAt":0,
               })

               return resume
          except Exception as e:
               raise e
          # end try
     
     
     async def update_resume_parse_info(self,user_id:str,user_resume:dict):
          try:
               user_id = ObjectId(user_id)
               
               # comment: update user resume
               result = await self.resume_collection.update_one({'userId':user_id},{"$set":user_resume})
               return {"message":"Resume parsed successfully","resume_id":str(result.upserted_id)}
               
          except Exception as e:
               raise e
          # end try

     from bson import ObjectId


     async def get_skill(self,user_id:str):
          try:
               user_id = ObjectId(user_id)
               skill = await self.resume_collection.find_one({'user_id':user_id},{"tech_stack":1})

               return skill
          except Exception as e:
               raise e
          # end try

     async def insert_cover_letter_info(self,user_id:str,cover_letter:dict):
          try:
               user_id = ObjectId(user_id)
               cover_letter['userId'] = user_id
               
               # comment: insert user cover letter
               result = await self.cover_letter_collection.insert_one(cover_letter)
               return {"message":"Cover letter inserted successfully","cover_letter_id":str(result.inserted_id)}
               
          except Exception as e:
               raise e
          # end try

     async def get_cover_letter_by_user_id(self,user_id:str):
          try:
               user_id = ObjectId(user_id)
               cover_letter = await self.cover_letter_collection.find_one({'userId':user_id})
               if cover_letter:
                    cover_letter['_id'] = str(cover_letter['_id'])
                    cover_letter['userId'] = str(cover_letter['userId'])
               return cover_letter
          except Exception as e:
               raise e
          # end try
     
     async def insert_recommended_skill(self,user_id:str,recommended_skill:dict):
          try:
               user_id = ObjectId(user_id)
               exist= await self.recommended_skill_collection.find_one({'userId':user_id})
               if exist:
                    await self.recommended_skill_collection.update_one({'userId':user_id},{"$push":{"recommended_skills":recommended_skill.recommended_skills}})
                    return {"message":"Recommended skill updated successfully","recommended_skill_id":str(exist['_id'])}  
               # comment: insert user recommended skill
               recommended_skill['userId'] = user_id
               result = await self.recommended_skill_collection.insert_one(recommended_skill)
               return {"message":"Recommended skill inserted successfully","recommended_skill_id":str(result.inserted_id)}
               
          except Exception as e:
               raise e
          # end try

     async def get_recommended_skill(self,user_id:str):
          try:
               user_id = ObjectId(user_id)
               recommended_skill = await self.recommended_skill_collection.find_one({'userId':user_id})
               if recommended_skill:
                    recommended_skill['_id'] = str(recommended_skill['_id'])
                    recommended_skill['userId'] = str(recommended_skill['userId'])
               return recommended_skill
          except Exception as e:
               raise e
          # end try
     
     async def insert_skill_impact(self,skill:str,skill_impact:dict):
          try:
               
               skill_impact['skill'] = skill
               
               result = await self.skill_impact_collection.insert_one(skill_impact)
               return {"message":"Skill impact inserted successfully","skill_impact_id":str(result.inserted_id)}
               
          except Exception as e:
               raise e
          
     async def get_skill_impact(self,skill:str):
          try:
               skill_impact = await self.skill_impact_collection.find_one({'skill':skill},{
                    "_id":0,
                    "skill":0,
               })
               return skill_impact
          except Exception as e:
               raise e

     async def get_user_resume(self, user_id: str):
          try:
               user_id = ObjectId(user_id)
               resume = await self.resume_collection.find_one({'user_id':user_id},{
                    "_id":0,
                    "user_id":0,
                    "createdAt":0,
                    "updatedAt":0,
                    
               })
               
               return resume
          except Exception as e:
               raise e
     async def get_user_skill(self,user_id:str):
          try:
               user_id = ObjectId(user_id)
               skill = await self.resume_collection.find_one({'user_id':user_id},{
                    "tech_stack":1,
                    "_id":0,
                    "user_id":0,
                    "createdAt":0,
                    "updatedAt":0,
                    
               })
               return skill
          except Exception as e:
               raise e
     

     async def insert_skill_gap(self, user_id: str, gig_id: str, skill_gap: dict):
          try:
               skill_gap["userId"]   = ObjectId(user_id)
               skill_gap["gigId"]    = ObjectId(gig_id)
               skill_gap["createdAt"] = datetime.now(timezone.utc)
               skill_gap["updatedAt"] = datetime.now(timezone.utc)

               result = await self.skillGap_collection.insert_one(skill_gap)
               return {
                    "message":       "Skill gap inserted successfully",
                    "skill_gap_id":  str(result.inserted_id)
               }
          except Exception as e:
               raise e

     async def save_match_mentor(self, user_id: str, gig_id: str, mentors: list[dict]):
          try:
               await self.mentorMatch_collection.update_one(
                    {
                         "userId": ObjectId(user_id),
                         "gigId":  ObjectId(gig_id),
                    },
                    {
                         "$set": {
                              "mentors":   mentors,
                              "updatedAt": datetime.now(timezone.utc),
                         },
                         "$setOnInsert": {
                              "userId":    ObjectId(user_id),
                              "gigId":     ObjectId(gig_id),
                              "createdAt": datetime.now(timezone.utc),
                         },
                    },
                    upsert=True,
               )
          except Exception as e:
               raise e


    # mongodb.py — fix all projection issues

     async def get_mentor_profile(self, mentor_ids: list[str]) -> list[dict]:
          try:
               object_ids = [ObjectId(mid) for mid in mentor_ids]
               mentors = await self.mentor_collection.find(
                    {"_id": {"$in": object_ids}, "isActive": True},
                    {
                         # ✅ inclusion only — no 0s except _id
                         "userId":            1,
                         "mentorName":        1,
                         "role":              1,
                         "company":           1,
                         "skills":            1,
                         "experienceYears":   1,
                         "mentorshipDetails": 1,
                         "availability":      1,
                         "_id":               0,   # ← only _id allowed as exclusion
                    }
               ).to_list(length=None)

               return [
                    {
                         "mentor_id":         str(m["userId"]),
                         "role":              m.get("role"),
                         "company":           m.get("company"),
                         "skills":            m.get("skills", []),
                         "experienceYears":   m.get("experienceYears"),
                         "mentorshipDetails": m.get("mentorshipDetails"),
                         "availability":      m.get("availability"),
                    }
                    for m in mentors
               ]
          except Exception as e:
               raise e


     async def get_user_domain(self, user_id: str) -> dict | None:
          try:
               user = await self.resume_profile_collection.find_one(
               {"userId": ObjectId(user_id)},
               {
                    # ✅ inclusion only
                    "domain":    1,
                    "subDomain": 1,
                    "_id":       0,
               }
          )
               return user
          except Exception as e:
               raise e


     async def get_skill_gap(self, user_id: str, gig_id: str) -> dict | None:
          try:
               skill_gap = await self.skillGap_collection.find_one(
               {
                    "userId": ObjectId(user_id),
                    "gigId":  ObjectId(gig_id),
               },
               {
                    # ✅ inclusion only
                    "skill_gap_of_user_with_gig":    1,
                    "match_skills_of_user_with_gig": 1,
                    "skil_gap_importance":           1,
                    "embedding":                     1,
                    "_id":                           0,
               }
          )
               return skill_gap
          except Exception as e:
               raise e


     async def get_match_mentor(self, user_id: str, gig_id: str) -> dict | None:
          try:
               result = await self.mentorMatch_collection.find_one(
               {
                    "userId": ObjectId(user_id),
                    "gigId":  ObjectId(gig_id),
               },
               {
                    # ✅ inclusion only
                    "mentors":   1,
                    "userId":    1,
                    "gigId":     1,
                    "_id":       0,
               }
          )    #skillquix-1  | [MentorMatch] Error: 'NoneType' object is not subscriptable
               if result:
                    if result["userId"]:
                         result["userId"] = str(result["userId"])
                    if result["gigId"]:
                         result["gigId"] = str(result["gigId"])
               return result
          except Exception as e:
               raise e


     async def get_gig_description(self, gig_id: str) -> dict | None:
          try:
               gig = await self.job_collection.find_one(
               {"_id": ObjectId(gig_id)},
               {
                    # ✅ inclusion only
                    "gigTitle":        1,
                    "description":     1,
                    "jobDescription":  1,
                    "responsibilities": 1,
                    "category":        1,
                    "experienceLevel": 1,
                    "gigType":         1,
                    "_id":             0,
               }
          )
               return gig
          except Exception as e:
               raise e
          
     async def delete_previous_match_gig(self, user_id: str):
          try:
               await self.matches_collection.delete_one(
                    {"userId": ObjectId(user_id)}
               )
               await self.skillGap_collection.delete_many(
                    {"userId": ObjectId(user_id)}
               )
               await self.mentorMatch_collection.delete_many(
                    {"userId": ObjectId(user_id)}
               )
               return {"message": "Previous match gigs deleted successfully"}
          except Exception as e:
               raise e


     async def get_match_score(self, user_id: str, gig_id: str) -> dict | None:
          try:
               result = await self.matches_collection.find_one(
                    {
                         "userId": ObjectId(user_id),
                         f"scoreMap.{gig_id}": {"$exists": True}
                    },
                    {
                         f"scoreMap.{gig_id}": 1,
                         "userId": 1,
                         "_id": 0
                    }
               )

               if result:
                    # Convert ObjectId to string for JSON serialization
                    result["userId"] = str(result["userId"])
                    
                    # Extract the specific score from the map
                    # This flattens the response so it's easier to use
                    score = result.get("scoreMap", {}).get(gig_id)
                    
                    return {
                         "userId": result["userId"],
                         "gigId": gig_id,
                         "score": score
                    }
                    
               return None

          except Exception as e:
               # Log the error here if needed
               raise e

