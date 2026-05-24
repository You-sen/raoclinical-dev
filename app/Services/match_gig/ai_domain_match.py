import json
from openai import AsyncOpenAI
from app.config.settings import settings
from app.prompt.prompt import GIG_MATCH_DOMAIN_TAXONOMY

openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)


async def ai_match_gigs_for_user(
     resume_domain: str,
     resume_subdomain: str,
     resume_skills: list[str],
     gig_candidates: list[dict],   # [{"gig_id": "...", "domain": "...", "subdomain": "...", "score": 0.87}]
) -> list[str]:
     """
     Feed resume domain + gig domain/subdomain into AI.
     AI returns only the gig_ids that are a genuine domain match.
     """
     if not gig_candidates:
          return []

     prompt = f"""
     You are a professional domain-matching engine for a freelance gig platform.

     Use both signals together:
     - Resume profile: domain, subdomain, and skills
     - Gig profile: domain, subdomain, skills, and combined score

     Prefer gigs that match the candidate's skills directly or adjacently.
     Do not return a gig only because its domain looks similar if the skill overlap is weak.

     {GIG_MATCH_DOMAIN_TAXONOMY}

     Candidate's Profile:
     - Domain: {resume_domain}
     - Subdomain: {resume_subdomain}
     - Skills: {json.dumps(resume_skills, indent=2)}

     Below are gig candidates with their domains and subdomains.
     Return ONLY the gig_ids that are a genuine domain match for this candidate.

     Rules:
     - A match means the gig is genuinely relevant to the candidate's background.
     - Domain and subdomain are soft labels, not hard filters.
     - Allow related or adjacent work areas if the skill overlap is strong.
     - If domain/subdomain is weak or missing, use gig title, category, description, responsibilities, and skills to infer relevance.
     - Prefer useful matches over strict rejection.

     Gig candidates:
     {json.dumps(gig_candidates, indent=2)}

     Respond ONLY with valid JSON, no markdown:
     {{
     "matched_gig_ids": ["gig_id_1", "gig_id_2", ...]
     }}
     """
     try:
          response = await openai_client.chat.completions.create(
               model="gpt-4o-mini",
               messages=[{"role": "user", "content": prompt}],
               max_tokens=500,
               temperature=0.1,
               response_format={"type": "json_object"},
          )
          result = json.loads(response.choices[0].message.content)
          matched_gig_ids = result.get("matched_gig_ids", [])
          if matched_gig_ids:
               return matched_gig_ids

               ranked_candidates = sorted(
                    gig_candidates,
                    key=lambda item: (
                         item.get("combined_score", item.get("score", 0.0)),
                         item.get("skill_overlap", 0.0),
                    ),
                    reverse=True,
               )
               fallback_ids = [
                    candidate["gig_id"]
                    for candidate in ranked_candidates
                    if candidate.get("skill_overlap", 0.0) > 0 or candidate.get("combined_score", 0.0) >= 0.25
               ]
               return fallback_ids[:5]
     except Exception as e:
          print(f"[AI Domain Matcher] Failed: {e}")
          return []


async def ai_match_users_for_gig(
     gig_domain: str,
     gig_subdomain: str,
     gig_skills: list[str],
     user_candidates: list[dict],  # [{"user_id": "...", "domain": "...", "subdomain": "...", "score": 0.87}]
) -> list[str]:
     """
     When a new gig is uploaded — AI decides which user IDs are a genuine domain match.
     """
     if not user_candidates:
          return []

     prompt = f"""
          You are a professional domain-matching engine for a freelance gig platform.

          Use both signals together:
          - Gig profile: domain, subdomain, and skills
          - Resume profile: domain, subdomain, and skills

          Prefer users whose skills overlap with the gig directly or adjacently.
          Do not return a user only because their domain looks similar if the skill overlap is weak.

          {GIG_MATCH_DOMAIN_TAXONOMY}

          New Gig Profile:
          - Domain: {gig_domain}
          - Subdomain: {gig_subdomain}
          - Skills: {json.dumps(gig_skills, indent=2)}

          Below are candidate users with their resume domain and subdomain.
          Return ONLY the user_ids whose background genuinely matches this gig.

          Rules:
          - Match means the user's background is genuinely relevant to the gig.
          - Domain and subdomain are soft labels, not hard gates.
          - Allow adjacent or related work areas if the skill overlap is strong.
          - If domain/subdomain is weak or missing, use gig title, category, description, responsibilities, and skills to infer relevance.
          - Prefer useful matches over strict rejection.

          User candidates:
          {json.dumps(user_candidates, indent=2)}

          Respond ONLY with valid JSON, no markdown:
          {{
          "matched_user_ids": ["user_id_1", "user_id_2", ...]
          }}
          """
     try:
          response = await openai_client.chat.completions.create(
               model="gpt-4o-mini",
               messages=[{"role": "user", "content": prompt}],
               temperature=0.1,
               response_format={"type": "json_object"},
          )
          result = json.loads(response.choices[0].message.content)
          matched_user_ids = result.get("matched_user_ids", [])
          if matched_user_ids:
               return matched_user_ids

               ranked_candidates = sorted(
                    user_candidates,
                    key=lambda item: (
                         item.get("combined_score", item.get("score", 0.0)),
                         item.get("skill_overlap", 0.0),
                    ),
                    reverse=True,
               )
               fallback_ids = [
                    candidate["user_id"]
                    for candidate in ranked_candidates
                    if candidate.get("skill_overlap", 0.0) > 0 or candidate.get("combined_score", 0.0) >= 0.25
               ]
               return fallback_ids[:5]
     except Exception as e:
          print(f"[AI User Matcher] Failed: {e}")
          return []