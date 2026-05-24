from openai import AsyncOpenAI
from app.config.settings import settings
from .user_skillgap_schema import UserSkillGapResponse
from app.DB.mongodb.mongodb import MongoDB
from app.prompt.prompt import USER_SKILLGAP_USER_PROMPT , USER_SKILLGAP_SYSTEM_PROMPT
from bson.objectid import ObjectId
import asyncio
from datetime import datetime
from fastapi import HTTPException
import json


class skillgap_service:
     def __init__(self):
          self.openai_client = AsyncOpenAI(
               api_key=settings.OPENAI_API_KEY
          )
          self.mongodb = MongoDB()
          self.user_skillgap_system_prompt = USER_SKILLGAP_SYSTEM_PROMPT
          self.user_skillgap_user_prompt = USER_SKILLGAP_USER_PROMPT

     async def get_full_resume_by_user_id(self, user_id: str) -> dict | None:
          """
          ResumeProfile → ResumeSection → ResumeSectionItem → Skill
          Based on Prisma schema — ResumeProfile is the AI-parsed domain-aware resume.
          """

          # ── 1. ResumeProfile (domain, embedding, summary) ─────────────────
          profile = await self.mongodb.resume_profile_collection.find_one(
               {"userId": ObjectId(user_id)},
               {"embedding": 0}    # exclude heavy embedding
          )
          if not profile:
               return None

          profile_id = profile["_id"]

          # ── 2. Fetch sections + skills concurrently ───────────────────────
          sections_list, skills_list = await asyncio.gather(
               self.mongodb.resume_section_collection.find(
                    {"resumeProfileId": profile_id}
               ).sort("orderIndex", 1).to_list(length=100),

               self.mongodb.resume_skill_collection.find(
                    {"resumeProfileId": profile_id}
               ).to_list(length=200),
          )

          # ── 3. Fetch all items for all sections in ONE query ──────────────
          section_ids = [s["_id"] for s in sections_list]

          all_items = await self.mongodb.resume_section_item_collection.find(
               {"resumeSectionId": {"$in": section_ids}}
          ).sort("orderIndex", 1).to_list(length=500)

          # ── 4. Group items by sectionId ───────────────────────────────────
          items_by_section: dict = {}
          for item in all_items:
               sid = str(item["resumeSectionId"])
               items_by_section.setdefault(sid, []).append(self._serialize(item))

          # ── 5. Attach items to sections ───────────────────────────────────
          sections_formatted = [
               {

                    "title":         s.get("title"),
                    "orderIndex":    s.get("orderIndex", 0),
                    "items":         items_by_section.get(str(s["_id"]), []),
               }
               for s in sections_list
          ]

          # ── 6. Format skills ──────────────────────────────────────────────
          skills_formatted = [
               {
                    "skillName":        s.get("skillName"),
                    "skillCategory":    s.get("skillCategory"),
                    "proficiencyLevel": s.get("proficiencyLevel"),
                    "yearOfExperience": s.get("yearOfExperience", 0),
                    "source":           s.get("source"),
               }
               for s in skills_list
          ]

          return {
               # ResumeProfile fields
               "domain":             profile.get("domain"),
               "subDomain":          profile.get("subDomain"),
               "name":               profile.get("name"),
               "summary":            profile.get("summary"),
               "totalExperienceYear": profile.get("totalExperienceYear"),

               # Nested
               "sections": sections_formatted,
               "skills":   skills_formatted,
          }
     def _serialize(self,doc: dict) -> dict:
          result = {}    
          for k, v in doc.items():
               if isinstance(v, ObjectId):
                    result[k] = str(v)
               elif isinstance(v, datetime):
                    result[k] = v.isoformat()
               elif isinstance(v, dict):
                    result[k] = self._serialize(v)
               elif isinstance(v, list):
                    result[k] = [
                         self._serialize(i) if isinstance(i, dict)
                         else str(i) if isinstance(i, ObjectId)
                         else i
                         for i in v
                    ]
               else:
                    result[k] = v
          return result

     

     async def get_response(self, user_id: str, gig_id: str) -> UserSkillGapResponse:
          try:
               gig_description, user_resume = await asyncio.gather(
                    self.mongodb.get_gig_description(gig_id),
                    self.get_full_resume_by_user_id(user_id)
               )

               prompt = self.user_skillgap_user_prompt.format(
                    gig_description=gig_description,
                    user_resume=user_resume
               )

               completion = await self.openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                         {
                              "role": "system",
                              "content": self.user_skillgap_system_prompt.format(
                              schema=UserSkillGapResponse.model_json_schema()
                              )
                         },
                         {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,
                    response_format={"type": "json_object"}
               )

               response = completion.choices[0].message.content

               if not response:
                    raise ValueError("No response from OpenAI")

               # ✅ Fix 2 — strip fences then parse JSON
               response = response.strip()
               if response.startswith("```json"):
                    response = response[7:]
               if response.startswith("```"):
                    response = response[3:]
               if response.endswith("```"):
                    response = response[:-3]
               response = response.strip()

               response = json.loads(response)   # ← parse to dict before returning

               return UserSkillGapResponse(**response)

          except Exception as e:
               raise HTTPException(status_code=500, detail=str(e))
                    
          