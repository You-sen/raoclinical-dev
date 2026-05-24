# mentor_match_service.py
import json
import asyncio
from bson import ObjectId
from datetime import datetime, timezone
from app.DB.vectorDB.vectordb import search_similar_mentors
from app.DB.mongodb.mongodb import MongoDB
from app.prompt.prompt import mentor_match_system_prompt, mentor_match_user_prompt
from openai import AsyncOpenAI
from app.config.settings import settings


class mentor_match_service:
     def __init__(self):
          self.mongodb      = MongoDB()
          self.openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

     async def get_ai_matched_mentors(
          self,
          user_skillgap: dict,
          user_domain: dict,
          mentor_profiles: list[dict],
     ) -> list[dict]:
          try:
               print(user_skillgap,user_domain,mentor_profiles)
               response = await self.openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                         {"role": "system", "content": mentor_match_system_prompt},
                         {
                         "role": "user",
                         "content": mentor_match_user_prompt.format(
                              user_skillgap=user_skillgap,
                              user_domain=user_domain,
                              mentor_profiles=mentor_profiles,
                         )
                         }
                    ],
                    temperature=0.1,
                    response_format={"type": "json_object"},
               )
               print("response",response)
               result = json.loads(response.choices[0].message.content)
               return result.get("matched_mentor_ids", [])
               # returns: [{"mentor_id": "...", "score": "...", "reason": "..."}]

          except Exception as e:
               print(f"[MentorMatch] AI error: {e}")
               return []

     async def get_similar_mentors(self, user_id: str, gig_id: str) -> dict:
          try:
               # ── STEP 1 ────────────────────────────────────────────────────────
               cached = await self.mongodb.get_match_mentor(user_id, gig_id)
               print(f"[DEBUG-1] cached: {cached is not None}")
               if cached:
                    return cached

               # ── STEP 2 ────────────────────────────────────────────────────────
               user_skillgap, user_domain = await asyncio.gather(
                    self.mongodb.get_skill_gap(user_id, gig_id),
                    self.mongodb.get_user_domain(user_id),
               )
               print(f"[DEBUG-2] user_skillgap keys: {list(user_skillgap.keys()) if user_skillgap else None}")
               print(f"[DEBUG-2] user_domain: {user_domain}")
               print(f"[DEBUG-2] has embedding: {bool(user_skillgap.get('embedding') if user_skillgap else False)}")

               if not user_skillgap:
                    return {"message": "Skill gap not found. Please analyze skill gap first."}

               embedding = user_skillgap.get("embedding")
               if not embedding:
                    return {"message": "Skill gap has no embedding yet."}

               print(f"[DEBUG-2] embedding dim: {len(embedding)}")

               # ── STEP 3 ────────────────────────────────────────────────────────
               candidate_mentor_results = await search_similar_mentors(embedding)
               print(f"[DEBUG-3] qdrant results count: {len(candidate_mentor_results)}")
               print(f"[DEBUG-3] qdrant results sample: {candidate_mentor_results[:2]}")

               if not candidate_mentor_results:
                    return {"message": "No similar mentors found in vector DB."}

               # ── STEP 4 ────────────────────────────────────────────────────────
               # Guard — handle both list[str] and list[dict]
               candidate_mentor_ids_list = []
               for item in candidate_mentor_results:
                    if isinstance(item, dict) and item.get("mentor_id") != user_id:
                         candidate_mentor_ids_list.append(item["mentor_id"])
                    elif isinstance(item, str) and item != user_id:
                         candidate_mentor_ids_list.append(item)

               print(f"[DEBUG-4] candidate_ids: {candidate_mentor_ids_list}")

               mentor_profiles = await self.mongodb.get_mentor_profile(candidate_mentor_ids_list)
               print(f"[DEBUG-4] mentor_profiles count: {len(mentor_profiles)}")
               print(f"[DEBUG-4] mentor_profiles: {mentor_profiles}")

               if not mentor_profiles:
                    return {"message": "No active mentor profiles found"}

               # ── STEP 5 ────────────────────────────────────────────────────────
               skillgap_for_ai = {k: v for k, v in user_skillgap.items() if k != "embedding"}

               ai_raw = await self.get_ai_matched_mentors(
                    skillgap_for_ai, user_domain, mentor_profiles
               )
               print(f"[DEBUG-5] ai_raw type: {type(ai_raw)}")
               print(f"[DEBUG-5] ai_raw: {ai_raw}")

               if not ai_raw:
                    return {"message": "AI returned no matches"}

               # ── STEP 6 — normalize AI output ──────────────────────────────────
               ai_matches = []
               for item in ai_raw:
                    if isinstance(item, dict):
                         ai_matches.append({
                              "mentor_id": str(item.get("mentor_id", "")),
                              "score":     str(item.get("score", "0")),
                              "reason":    item.get("reason", ""),
                         })
                    elif isinstance(item, str):
                         ai_matches.append({
                              "mentor_id": item,
                              "score":     "0",
                              "reason":    "",
                         })

               ai_matches = [m for m in ai_matches if m["mentor_id"]]
               print(f"[DEBUG-6] normalized ai_matches: {ai_matches}")

               if not ai_matches:
                    return {"message": "AI matches were empty "}

               # ── STEP 7 ────────────────────────────────────────────────────────
               mentor_id_list = [m["mentor_id"] for m in ai_matches]
               print(f"[DEBUG-7] mentor_id_list for enrichment: {mentor_id_list}")

               enriched = await self._enrich_mentor_data(mentor_id_list, ai_matches)
               print(f"[DEBUG-7] enriched count: {len(enriched)}")
               print(f"[DEBUG-7] enriched: {enriched}")

               # ── STEP 8 ────────────────────────────────────────────────────────
               await self.mongodb.save_match_mentor(user_id, gig_id, enriched)
               print(f"[DEBUG-8] saved to DB")

               return {
                    "user_id": user_id,
                    "gig_id":  gig_id,
                    "mentors": enriched,
                    "source":  "ai_match",
               }

          except Exception as e:
               import traceback
               print(f"[MentorMatch] FULL ERROR:\n{traceback.format_exc()}")
               raise

     async def _enrich_mentor_data(
          self, mentor_ids: list[str], ai_matches: list[dict]
     ) -> list[dict]:
          """
          Fetch mentor name, role, profileImage from User collection.
          Merge with AI score and reason.
          """
          score_map = {m["mentor_id"]: m for m in ai_matches}

          # Fetch User docs for name + profileImage
          user_docs = await self.mongodb.db["User"].find(
               {"_id": {"$in": [ObjectId(mid) for mid in mentor_ids]}},
               {"fullName": 1, "profileImage": 1, "profession": 1}
          ).to_list(length=20)

          user_map = {str(u["_id"]): u for u in user_docs}

          # Fetch MentorProfile for role + skills
          mentor_docs = await self.mongodb.mentor_collection.find(
               {"userId": {"$in": [ObjectId(mid) for mid in mentor_ids]}, "isActive": True},
               {"userId": 1, "role": 1, "skills": 1, "experienceYears": 1,
               "mentorName": 1, "company": 1, "availability": 1}
          ).to_list(length=20)

          mentor_map = {str(m["userId"]): m for m in mentor_docs}

          enriched = []
          for mentor_id in mentor_ids:
               ai_data     = score_map.get(mentor_id, {})
               user_data   = user_map.get(mentor_id, {})
               mentor_data = mentor_map.get(mentor_id, {})

               enriched.append({
                    "mentorId":      mentor_id,
                    "name":          mentor_data.get("mentorName") or user_data.get("fullName"),
                    "role":          mentor_data.get("role") or user_data.get("profession"),
                    "profileImage":  user_data.get("profileImage", ""),
                    "experienceYears": mentor_data.get("experienceYears"),
                    "matchScore":    ai_data.get("score"),
                    "matchReason":   ai_data.get("reason"),
               })

          return enriched