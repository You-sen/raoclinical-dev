import json
from openai import AsyncOpenAI
from bson import ObjectId
from app.DB.mongodb.mongodb import MongoDB
from app.Services.tailorCV.tailorCV_schema import (
    TailorCVRequest,
    TailoredCVData,
    TailoredWorkExperience,
    TailoredSkill,
    TailoredEducation,
    TailoredUser,
)

client = AsyncOpenAI()
db     = MongoDB()


# ─────────────────────────────────────────────
# SYSTEM PROMPT
# ─────────────────────────────────────────────

TAILOR_SYSTEM = """
You are an expert CV tailoring engine.

Your job is to rewrite and filter a candidate's existing CV data to best match
a specific job description — without inventing, guessing, or hallucinating any
information that is not already present in the candidate's CV.

RULES (strictly enforced):
- Only use facts, skills, experiences, and achievements that exist in the provided CV data.
- If a field cannot be meaningfully tailored or has no relevant content, return null.
- Do NOT guess missing information. Do NOT fabricate metrics, tools, or responsibilities.
- Rewrite narrative fields (resumeSummary, responsibilities) to emphasise job-relevant aspects.
- For skills: only include skills from the CV relevant to the job, with a relevanceScore (0-100).
- For workExperiences: keep all positions, rewrite responsibilities for job relevance.
- Identity fields (fullName, email, phoneNumber, location, portfolioUrl, linkedinUrl)
  must always be passed through exactly as-is.

Return ONLY a valid JSON object matching this exact schema (no extra keys, no comments):
{
  "fullName": "string | null",
  "email": "string | null",
  "phoneNumber": "string | null",
  "location": "string | null",
  "portfolioUrl": "string | null",
  "linkedinUrl": "string | null",
  "currentRole": "string | null",
  "resumeSummary": "string | null",
  "totalExperienceYear": "number | null",
  "domain": "string | null",
  "subDomain": "string | null",
  "industry": "string | null",
  "languages": ["string"] or null,
  "skills": [
    {
      "skillName": "string",
      "skillCategory": "string | null",
      "proficiencyLevel": "string | null",
      "yearOfExperience": "number | null",
      "relevanceScore": "number 0-100"
    }
  ] or null,
  "workExperiences": [
    {
      "company": "string | null",
      "position": "string | null",
      "duration": "string | null",
      "responsibilities": "string | null",
      "projects": ["string"] or null
    }
  ] or null,
  "educationsAndCertifications": [
    {
      "degree": "string | null",
      "certificateName": "string | null",
      "institution": "string | null",
      "organizationName": "string | null",
      "passingYear": "string | null",
      "issueDate": "string | null"
    }
  ] or null
}
"""


# ─────────────────────────────────────────────
# USER PROMPT BUILDER
# ─────────────────────────────────────────────

def _build_user_prompt(job_description: str, enhanced_cv: dict) -> str:
    ecv        = enhanced_cv.get("enhanced_master_cv", enhanced_cv)
    skills     = enhanced_cv.get("skills", [])
    challenges = enhanced_cv.get("enhanced_challenges", [])

    return f"""
JOB DESCRIPTION:
{job_description}

─────────────────────────────────────────────
CANDIDATE CV DATA:
{json.dumps({
    "fullName":       ecv.get("fullName"),
    "email":          ecv.get("email"),
    "phoneNumber":    ecv.get("phoneNumber"),
    "location":       ecv.get("location"),
    "portfolioUrl":   ecv.get("portfolioUrl"),
    "linkedinUrl":     ecv.get("linkedinUrl"),
    "currentRole":    ecv.get("currentRole"),
    "resumeSummary":  ecv.get("resumeSummary"),
    "totalExperienceYear": ecv.get("totalExperienceYear"),
    "domain":         ecv.get("domain"),
    "subDomain":      ecv.get("subDomain"),
    "industry":       ecv.get("industry"),
    "languages":      ecv.get("languages", []),
    "skills":         skills,
    "workExperiences":             ecv.get("workExperiences", []),
    "educationsAndCertifications": ecv.get("educationsAndCertifications", []),
    "enhanced_challenges":         challenges,
}, indent=2)}
""".strip()


# ─────────────────────────────────────────────
# MAIN SERVICE
# ─────────────────────────────────────────────

async def tailor_cv(req: TailorCVRequest) -> TailoredCVData:
    # 1. Fetch enhancedMasterCV from MongoDB
    enhanced_cv = await db.db["enhancedMasterCv"].find_one(
        {"userId": ObjectId(req.userId)},
        {"_id": 0},
    )

    if not enhanced_cv:
        raise ValueError(f"No enhancedMasterCV found for userId: {req.userId}")

    # 2. Build prompt
    user_prompt = _build_user_prompt(req.jobDescription, enhanced_cv)

    # 3. Call OpenAI
    response = await client.chat.completions.create(
        model="gpt-4o",
        temperature=0.2,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": TAILOR_SYSTEM},
            {"role": "user",   "content": user_prompt},
        ],
    )

    raw = json.loads(response.choices[0].message.content)

    # 4. Build nested models safely
    work_exps = [
        TailoredWorkExperience(**w)
        for w in (raw.get("workExperiences") or [])
    ]

    skills = [
        TailoredSkill(**s)
        for s in (raw.get("skills") or [])
    ]

    educations = [
        TailoredEducation(**e)
        for e in (raw.get("educationsAndCertifications") or [])
    ]

    return TailoredCVData(
        fullName=raw.get("fullName"),
        email=raw.get("email"),
        phoneNumber=raw.get("phoneNumber"),
        location=raw.get("location"),
        portfolioUrl=raw.get("portfolioUrl"),
        linkedinUrl=raw.get("linkedinUrl"),
        currentRole=raw.get("currentRole"),
        resumeSummary=raw.get("resumeSummary"),
        totalExperienceYear=raw.get("totalExperienceYear"),
        # domain=raw.get("domain"),
        # subDomain=raw.get("subDomain"),
        # industry=raw.get("industry"),
        languages=raw.get("languages"),
        skills=skills or None,
        workExperiences=work_exps or None,
        educationsAndCertifications=educations or None,
        user=TailoredUser(profileImage=None),  # can't get from DB
    )
# import json
# from openai import AsyncOpenAI
# from bson import ObjectId
# from app.DB.mongodb.mongodb import MongoDB
# from app.Services.tailorCV.tailorCV_schema import (
#     TailorCVRequest,
#     TailoredCVData,
#     TailoredWorkExperience,
#     TailoredChallenge,
#     TailoredSkill,
#     TailoredEducation,
# )

# client = AsyncOpenAI()
# db     = MongoDB()


# # ─────────────────────────────────────────────
# # SYSTEM PROMPT
# # ─────────────────────────────────────────────

# TAILOR_SYSTEM = """
# You are an expert CV tailoring engine.

# Your job is to rewrite and filter a candidate's existing CV data to best match
# a specific job description — without inventing, guessing, or hallucinating any
# information that is not already present in the candidate's CV.

# RULES (strictly enforced):
# - Only use facts, skills, experiences, and achievements that exist in the provided CV data.
# - If a field cannot be meaningfully tailored or has no relevant content for this job, return null for that field.
# - Do NOT guess missing information. Do NOT fabricate metrics, tools, or responsibilities.
# - Rewrite narrative fields (bio, resumeSummary, carrierGoal, responsibilities) to
#   emphasise the aspects most relevant to the job description.
# - For skills: only include skills from the CV that are relevant to the job. Add a
#   relevanceScore (0-100) for each based on how well it matches the job requirements.
# - For workExperiences: keep all positions but rewrite responsibilities to highlight
#   the most job-relevant aspects. If a role has nothing relevant, set responsibilities to null.
# - For challenges: only include challenges relevant to the job. Omit irrelevant ones.
# - For strength: only include strengths that are directly relevant to the job. Omit the rest.
# - Identity fields (fullName, email, phoneNumber, location, linkedinUrl, portfolioUrl,
#   resumeLink) must always be passed through exactly as-is.

# Return ONLY a valid JSON object matching this exact schema (no extra keys, no comments):
# {
#   "fullName": "string | null",
#   "email": "string | null",
#   "phoneNumber": "string | null",
#   "location": "string | null",
#   "linkedinUrl": "string | null",
#   "portfolioUrl": "string | null",
#   "resumeLink": "string | null",
#   "currentRole": "string | null",
#   "careerStage": "string | null",
#   "experienceYear": "number | null",
#   "domain": "string | null",
#   "subDomain": "string | null",
#   "industry": "string | null",
#   "bio": "string | null",
#   "resumeSummary": "string | null",
#   "carrierGoal": "string | null",
#   "strength": ["string"] or null,
#   "workExperiences": [
#     {
#       "company": "string | null",
#       "position": "string | null",
#       "duration": "string | null",
#       "responsibilities": "string | null",
#       "projects": ["string"] or null
#     }
#   ] or null,
#   "educationsAndCertifications": [
#     {
#       "degree": "string | null",
#       "certificateName": "string | null",
#       "institution": "string | null",
#       "organizationName": "string | null",
#       "passingYear": "string | null",
#       "issueDate": "string | null"
#     }
#   ] or null,
#   "relevantSkills": [
#     {
#       "skillName": "string",
#       "skillCategory": "string | null",
#       "proficiencyLevel": "string | null",
#       "yearOfExperience": "number | null",
#       "relevanceScore": "number 0-100"
#     }
#   ] or null,
#   "relevantChallenges": [
#     {
#       "challengeName": "string | null",
#       "situation": "string | null",
#       "task": "string | null",
#       "action": "string | null",
#       "result": "string | null"
#     }
#   ] or null
# }
# """


# # ─────────────────────────────────────────────
# # USER PROMPT BUILDER
# # ─────────────────────────────────────────────

# def _build_user_prompt(job_description: str, enhanced_cv: dict) -> str:
#     ecv      = enhanced_cv.get("enhanced_master_cv", enhanced_cv)
#     skills   = enhanced_cv.get("skills", [])
#     gaps     = enhanced_cv.get("skill_gaps", [])
#     challenges = enhanced_cv.get("enhanced_challenges", [])

#     return f"""
# JOB DESCRIPTION:
# {job_description}

# ─────────────────────────────────────────────
# CANDIDATE CV DATA:
# {json.dumps({
#     "identity": {
#         "fullName":       ecv.get("fullName"),
#         "email":          ecv.get("email"),
#         "phoneNumber":    ecv.get("phoneNumber"),
#         "languages":      ecv.get("languages", []),
#         "location":       ecv.get("location"),
#         "linkedinUrl":    ecv.get("linkedinUrl"),
#         "portfolioUrl":   ecv.get("portfolioUrl"),
#         "resumeLink":     ecv.get("resumeLink"),
#     },
#     "profile": {
#         "currentRole":         ecv.get("currentRole"),
#         "careerStage":         ecv.get("careerStage"),
#         "experienceYear": ecv.get("experienceYear"),
#         "domain":              ecv.get("domain"),
#         "subDomain":           ecv.get("subDomain"),
#         "industry":            ecv.get("industry"),
#     },
#     "narrative": {
#         "bio":           ecv.get("bio"),
#         "resumeSummary": ecv.get("resumeSummary"),
#         "carrierGoal":   ecv.get("carrierGoal"),
#         "strength":      ecv.get("strength"),
#     },
#     "workExperiences":             ecv.get("workExperiences", ecv.get("workExperiences", [])),
#     "educationsAndCertifications": ecv.get("educationsAndCertifications", []),
#     "skills":                      skills,
#     "enhanced_challenges":         challenges,
# }, indent=2)}
# """.strip()


# # ─────────────────────────────────────────────
# # MAIN SERVICE
# # ─────────────────────────────────────────────

# async def tailor_cv(req: TailorCVRequest) -> TailoredCVData:
#     # 1. Fetch enhancedMasterCV from MongoDB
#     enhanced_cv = await db.db["enhancedMasterCv"].find_one(
#         {"userId": ObjectId(req.userId)},
#         {"_id": 0},
#     )

#     if not enhanced_cv:
#         raise ValueError(f"No enhancedMasterCV found for userId: {req.userId}")

#     # 2. Build prompts
#     user_prompt = _build_user_prompt(req.jobDescription, enhanced_cv)

#     # 3. Call OpenAI
#     response = await client.chat.completions.create(
#         model="gpt-4o",
#         temperature=0.2,           # low — we want faithful rewriting, not creativity
#         response_format={"type": "json_object"},
#         messages=[
#             {"role": "system", "content": TAILOR_SYSTEM},
#             {"role": "user",   "content": user_prompt},
#         ],
#     )

#     raw = json.loads(response.choices[0].message.content)

#     # 4. Map to Pydantic — nested lists built explicitly so missing keys don't crash
#     work_exps = [
#         TailoredWorkExperience(**w)
#         for w in (raw.get("workExperiences") or [])
#     ]

#     challenges = [
#         TailoredChallenge(**c)
#         for c in (raw.get("relevantChallenges") or [])
#     ]

#     skills = [
#         TailoredSkill(**s)
#         for s in (raw.get("relevantSkills") or [])
#     ]

#     educations = [
#         TailoredEducation(**e)
#         for e in (raw.get("educationsAndCertifications") or [])
#     ]

#     return TailoredCVData(
#         fullName=raw.get("fullName"),
#         email=raw.get("email"),
#         phoneNumber=raw.get("phoneNumber"),
#         location=raw.get("location"),
#         linkedinUrl=raw.get("linkedinUrl"),
#         portfolioUrl=raw.get("portfolioUrl"),
#         resumeLink=raw.get("resumeLink"),
#         currentRole=raw.get("currentRole"),
#         careerStage=raw.get("careerStage"),
#         experienceYear=raw.get("experienceYear"),
#         domain=raw.get("domain"),
#         subDomain=raw.get("subDomain"),
#         industry=raw.get("industry"),
#         bio=raw.get("bio"),
#         resumeSummary=raw.get("resumeSummary"),
#         carrierGoal=raw.get("carrierGoal"),
#         strength=raw.get("strength"),
#         workExperiences=work_exps or None,
#         educationsAndCertifications=educations or None,
#         relevantSkills=skills or None,
#         relevantChallenges=challenges or None,
#     )