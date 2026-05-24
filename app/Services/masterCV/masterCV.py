import json
from datetime import datetime, timezone
from openai import AsyncOpenAI
from app.DB.mongodb.mongodb import MongoDB
from app.Services.masterCV.masterCV_schema import (
    MasterCVData,
    EnhancedMasterCVData,
    SkillOut,
    SkillGapOut,
    AIImpact,
    EnhancedChallenge,
    AIScore,
    AIScoreBreakdown,
    ScoreBreakdown,
    GapScoreBreakdown,
    EnhancedMasterCV,
    WorkExperienceOut,
    EnhanceChallengeRequest,
    EnhanceChallengeData,
)
 
client = AsyncOpenAI()
db = MongoDB()
 
 
# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────
 
def _grade(total: int) -> str:
    if total >= 90: return "S"
    if total >= 75: return "A"
    if total >= 60: return "B"
    if total >= 45: return "C"
    return "D"
 
 
async def _call_openai(system: str, user: str, model: str = "gpt-4o") -> dict:
    """Call OpenAI and parse JSON response."""
    response = await client.chat.completions.create(
        model=model,
        temperature=0.3,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": user},
        ],
    )
    return json.loads(response.choices[0].message.content)
 
 
# ─────────────────────────────────────────────
# STEP 0 — Infer domain & subDomain if missing
# ─────────────────────────────────────────────
 
DOMAIN_INFER_SYSTEM = """
You are an expert career domain classifier.
Given a candidate's profile data, infer the most accurate domain and subDomain
for their professional background.
 
Use ALL available signals in this priority order:
  1. currentRole  — strongest signal
  2. workExperiences (positions, responsibilities, projects)
  3. challenges (what problems they solved)
  4. skills / tech stack mentioned anywhere
  5. industry + bio as soft context
 
Rules:
- domain: broad professional area (e.g. "Software Engineering", "Data Science",
  "Product Management", "UX Design", "DevOps", "Cybersecurity", "Mobile Engineering")
- subDomain: specific focus within the domain (e.g. "Backend Development",
  "ML Engineering", "iOS Engineering", "Cloud Infrastructure")
- Be specific — prefer "Backend Development" over "Engineering"
- If the profile is genuinely multi-domain, pick the DOMINANT hiring identity
- Never return null — always make your best inference
 
Return ONLY valid JSON:
{
  "domain": "string",
  "subDomain": "string",
  "confidence": "High | Medium | Low",
  "reasoning": "string (1 sentence explaining the inference)"
}
"""
 
 
async def infer_domain(cv: MasterCVData) -> tuple[str, str]:
    """
    Returns (domain, subDomain).
    If both are already present in the CV, returns them as-is (no API call).
    If either is missing or empty, infers both from the full CV context.
    """
    # subDomain may be List[str] or str — normalise to plain string
    def _first(val):
        if isinstance(val, list): return val[0].strip() if val else ""
        return (val or "").strip()
 
    domain_present    = bool(cv.domain and _first(cv.domain))
    subdomain_present = bool(cv.subDomain and _first(cv.subDomain))
 
    if domain_present and subdomain_present:
        return _first(cv.domain), _first(cv.subDomain)
 
    # Build context from whatever fields are available
    work_summary = ""
    if cv.workExperiences:
        work_summary = "; ".join(
            f"{w.position} at {w.company}: {w.responsibilities or ''}"
            for w in cv.workExperiences[:3]
        )
 
    challenge_summary = ""
    if cv.challenges:
        challenge_summary = "; ".join(
            f"{c.situation or ''}: {c.action or ''}"
            for c in cv.challenges[:3]
        )
 
    user_prompt = f"""
currentRole      : {cv.currentRole or 'Not provided'}
industry         : {cv.industry or 'Not provided'}
bio              : {cv.bio or 'Not provided'}
resumeSummary    : {cv.resumeSummary or 'Not provided'}
domain (given)   : {cv.domain or 'MISSING'}
subDomain (given): {cv.subDomain or 'MISSING'}
workExperiences  : {work_summary or 'Not provided'}
challenges       : {challenge_summary or 'Not provided'}
strength         : {', '.join(cv.strength or []) or 'Not provided'}
"""
    result = await _call_openai(DOMAIN_INFER_SYSTEM, user_prompt)
 
    inferred_domain    = result.get("domain",    _first(cv.domain)    or "Software Engineering")
    inferred_subdomain = result.get("subDomain", _first(cv.subDomain) or "General")
 
    return str(inferred_domain).strip(), str(inferred_subdomain).strip()
 
 
# ─────────────────────────────────────────────
# STEP 1 — Enhance CV text fields
# ─────────────────────────────────────────────
 
ENHANCE_SYSTEM = """
You are a senior career coach and professional CV writer.
Enhance the given fields from a candidate's MasterCV to be more impactful,
specific, and achievement-oriented while staying 100% truthful to the
original content. Do not invent metrics or facts.
 
Return ONLY valid JSON matching this schema (no extra keys):
{
  "bio": "string",
  "resumeSummary": "string",
  "carrierGoal": "string",
  "strength": ["string"],
  "workExperiences": [
    {
      "company": "string",
      "position": "string",
      "duration": "string",
      "responsibilities": "string",
      "projects": ["string"]
    }
  ],
  "challenges": [
    {
      "challengeName": "string",
      "situation": "string",
      "task": "string",
      "action": "string",
      "result": "string"
    }
  ]
}
 
Rules:
- bio: 2-3 punchy sentences. Lead with seniority + years + domain impact.
- resumeSummary: 2-3 sentences. Highlight tech stack, scale, and key achievement.
- carrierGoal: 1-2 sentences. Connect current expertise to ambition concretely.
- strength: each item should be 1 sentence with a concrete example from the CV.
- workExperiences[].responsibilities: rewrite with active verbs, scale, and outcomes.
- challenges: input already has situation, task, action, result. Enhance each to be vivid and impactful (2-3 sentences each). Infer challengeName (3-6 words) from the full STAR story summarising what the challenge WAS (e.g. "Monolith to Microservices Migration").v
"""
 
 
async def enhance_cv_fields(cv: MasterCVData) -> dict:
    user_prompt = f"""
Role: {cv.currentRole}
Domain: {cv.domain} / {cv.subDomain}
Career stage: {cv.careerStage}
Total experience: {cv.experienceYear} years
 
bio: {cv.bio}
resumeSummary: {cv.resumeSummary}
carrierGoal: {cv.carrierGoal}
strength: {json.dumps(cv.strength)}
workExperiences: {json.dumps([w.model_dump() for w in (cv.workExperiences or [])])}
challenges: {json.dumps([c.model_dump() for c in (cv.challenges or [])])}
"""
    return await _call_openai(ENHANCE_SYSTEM, user_prompt)
 
 
# ─────────────────────────────────────────────
# STEP 2 — Extract & score skills from challenges
# ─────────────────────────────────────────────
 
SKILL_EXTRACT_SYSTEM = """
You are a technical skill extraction engine.
Given challenges from a candidate's CV and their role/domain context,
extract all implied or explicit technical and soft skills.
 
For each skill calculate:
- roleAlignment (0-100): how relevant is this skill to their currentRole and domain?
- experienceWeight (0-100): based on the context, how experienced do they seem?
- score (0-100): weighted average — (roleAlignment * 0.6) + (experienceWeight * 0.4)
 
Return ONLY valid JSON:
{
  "skills": [
    {
      "skillName": "string",
      "skillCategory": "string",
      "proficiencyLevel": "Beginner | Intermediate | Advanced | Expert",
      "yearOfExperience": 0,
      "source": "MASTER_CV",
      "score": 0,
      "scoreBreakdown": {
        "roleAlignment": 0,
        "experienceWeight": 0
      }
    }
  ]
}
 
Rules:
- Extract concrete technical skills only (no generic words like "communication").
- Avoid duplicating skills that would obviously already be in their base skill set.
- yearOfExperience: estimate from context clues; default to 1 if unclear.
- Max 10 skills per call.
"""
 
 
async def extract_skills_from_challenges(cv: MasterCVData) -> list[dict]:
    if not cv.challenges:
        return []
 
    user_prompt = f"""
currentRole: {cv.currentRole}
domain: {cv.domain}
subDomain: {cv.subDomain}
careerStage: {cv.careerStage}
carrierGoal: {cv.carrierGoal}
 
Challenges:
{json.dumps([c.model_dump() for c in cv.challenges])}
"""
    result = await _call_openai(SKILL_EXTRACT_SYSTEM, user_prompt)
    return result.get("skills", [])
 
 
# ─────────────────────────────────────────────
# STEP 3 — Score existing skills from MongoDB
# ─────────────────────────────────────────────
 
SKILL_SCORE_SYSTEM = """
You are a technical skill evaluator.
Given a list of skills the candidate already has and their role/domain context,
score each skill.
 
For each skill calculate:
- roleAlignment (0-100): relevance to currentRole and domain
- experienceWeight (0-100): inferred from yearsOfExperience vs expected for the role
- score (0-100): (roleAlignment * 0.6) + (experienceWeight * 0.4)
- proficiencyLevel: infer from score — <40 Beginner, 40-65 Intermediate, 66-80 Advanced, >80 Expert
 
Return ONLY valid JSON:
{
  "skills": [
    {
      "skillName": "string",
      "skillCategory": "string",
      "proficiencyLevel": "string",
      "yearOfExperience": 0,
      "source": "MASTER_CV",
      "score": 0,
      "scoreBreakdown": {
        "roleAlignment": 0,
        "experienceWeight": 0
      }
    }
  ]
}
"""
 
 
async def score_existing_skills(raw_skills: list, cv: MasterCVData) -> list[dict]:
    if not raw_skills:
        return []
 
    user_prompt = f"""
currentRole: {cv.currentRole}
domain: {cv.domain}
subDomain: {cv.subDomain}
experienceYear: {cv.experienceYear}
 
Skills to score:
{json.dumps(raw_skills)}
"""
    result = await _call_openai(SKILL_SCORE_SYSTEM, user_prompt)
    return result.get("skills", [])
 
 
# ─────────────────────────────────────────────
# STEP 4 — Identify skill gaps
# ─────────────────────────────────────────────
 
SKILL_GAP_SYSTEM = """
You are an expert technical career advisor.
Given a candidate's current skills, role, domain, and a reference skill collection
for that domain/role, identify skills the candidate is MISSING that are important
for their career progression.
 
For each gap:
- roleAlignment (0-100): how relevant is this skill to their role/domain
- demandWeight (0-100): how in-demand is this skill in the industry right now
- score (0-100): (roleAlignment * 0.5) + (demandWeight * 0.5)
- demandLevel: High (score >= 70), Medium (40-69), Low (<40)
- sourceCollection: "ROLE_SKILLS" if it comes from the provided skill list,
  "DOMAIN_INFERRED" if identified by you from domain knowledge
 
Return ONLY valid JSON:
{
  "skill_gaps": [
    {
      "skillName": "string",
      "skillCategory": "string",
      "proficiencyLevel": "Beginner | Intermediate | Advanced",
      "demandLevel": "High | Medium | Low",
      "score": 0,
      "scoreBreakdown": {
        "roleAlignment": 0,
        "demandWeight": 0
      },
      "gapReason": "string (2 sentences: why this is a gap for this role)",
      "suggestion": "string (actionable 1-2 sentence learning path)",
      "sourceCollection": "ROLE_SKILLS | DOMAIN_INFERRED"
    }
  ]
}
 
Rules:
- Only surface MISSING skills — do not list skills the candidate already has.
- Limit to the 6 most impactful gaps.
- Sort by score descending (highest impact gap first).
"""
 
 
async def identify_skill_gaps(
    current_skills: list[dict],
    role_skill_collection: list,
    cv: MasterCVData,
) -> list[dict]:
    user_prompt = f"""
currentRole: {cv.currentRole}
domain: {cv.domain}
subDomain: {cv.subDomain}
careerStage: {cv.careerStage}
experienceYear: {cv.experienceYear}
 
Candidate's current skills:
{json.dumps([s.get("skillName") for s in current_skills])}
 
Role/domain reference skill collection (from frontend):
{json.dumps(role_skill_collection)}
"""
    result = await _call_openai(SKILL_GAP_SYSTEM, user_prompt)
    return result.get("skill_gaps", [])
 
 
# ─────────────────────────────────────────────
# STEP 5 — Calculate AI score
# ─────────────────────────────────────────────
 
AI_SCORE_SYSTEM = """
You are a CV quality evaluator.
Given a candidate's enhanced MasterCV data, score their profile on 5 dimensions.
Each dimension is 0-100. Return the total as a weighted average.
 
Weights:
  profileCompleteness : 15%  — % of important fields that are non-null and detailed
  skillRelevance      : 30%  — avg skill score relative to role/domain
  experienceClarity   : 25%  — specificity and impact of work experience descriptions
  careerNarrative     : 20%  — coherence of bio + resumeSummary + carrierGoal + challenges
  skillGapSeverity    : 10%  — INVERSE score: more/worse gaps = lower score
 
Grading: S=90+, A=75-89, B=60-74, C=45-59, D=<45
 
Return ONLY valid JSON:
{
  "breakdown": {
    "profileCompleteness": 0,
    "skillRelevance": 0,
    "experienceClarity": 0,
    "careerNarrative": 0,
    "skillGapSeverity": 0
  },
  "summary": "string (2-3 sentence plain-English summary of the profile strengths and main gaps)"
}
"""
 
 
async def calculate_ai_score(
    cv: MasterCVData,
    enhanced: dict,
    skills: list[dict],
    skill_gaps: list[dict],
) -> AIScore:
    user_prompt = f"""
currentRole: {cv.currentRole}
domain: {cv.domain}
subDomain: {cv.subDomain}
careerStage: {cv.careerStage}
 
Enhanced bio: {enhanced.get('bio', '')}
Enhanced resumeSummary: {enhanced.get('resumeSummary', '')}
Enhanced carrierGoal: {enhanced.get('carrierGoal', '')}
Strengths count: {len(enhanced.get('strength', []))}
Work experiences count: {len(enhanced.get('workExperiences', []))}
 
Skills (count {len(skills)}), avg score: {
    round(sum(s.get('score', 0) for s in skills) / len(skills)) if skills else 0
}
Skill gaps count: {len(skill_gaps)}
High-demand gaps: {sum(1 for g in skill_gaps if g.get('demandLevel') == 'High')}
"""
    result = await _call_openai(AI_SCORE_SYSTEM, user_prompt)
    breakdown = result.get("breakdown", {})
 
    total = round(
        breakdown.get("profileCompleteness", 0) * 0.15
        + breakdown.get("skillRelevance", 0) * 0.30
        + breakdown.get("experienceClarity", 0) * 0.25
        + breakdown.get("careerNarrative", 0) * 0.20
        + breakdown.get("skillGapSeverity", 0) * 0.10
    )
 
    return AIScore(
        total=total,
        grade=_grade(total),
        summary=result.get("summary", ""),
        breakdown=AIScoreBreakdown(**breakdown),
    )
 
 
# ─────────────────────────────────────────────
# STEP 6 — Build ai_impacts (original vs enhanced diff)
# ─────────────────────────────────────────────
 
def build_ai_impacts(cv: MasterCVData, enhanced: dict) -> list[AIImpact]:
    impacts: list[AIImpact] = []
 
    def _add(field: str, original: str, enhanced_val: str):
        if original and enhanced_val and original.strip() != enhanced_val.strip():
            impacts.append(AIImpact(
                field=field,
                original=original,
                enhanced=enhanced_val,
            ))
 
    _add("bio", cv.bio or "", enhanced.get("bio", ""))
    _add("resumeSummary", cv.resumeSummary or "", enhanced.get("resumeSummary", ""))
    _add("carrierGoal", cv.carrierGoal or "", enhanced.get("carrierGoal", ""))
 
    orig_strengths = cv.strength or []
    new_strengths  = enhanced.get("strength", [])
    for i, (orig, enh) in enumerate(zip(orig_strengths, new_strengths)):
        _add(f"strength[{i}]", orig, enh)
 
    orig_exps = cv.workExperiences or []
    new_exps  = enhanced.get("workExperiences", [])
    for i, (orig, enh) in enumerate(zip(orig_exps, new_exps)):
        _add(
            f"workExperiences[{i}].responsibilities",
            orig.responsibilities or '',
            enh.get("responsibilities", ""),
        )
 
    return impacts
 
 
# ─────────────────────────────────────────────
# MAIN SERVICE ENTRY POINT
# ─────────────────────────────────────────────
 
async def enhance_master_cv(
    cv: MasterCVData,
    role_skill_collection: list,
) -> EnhancedMasterCVData:
    """
    Orchestrates all enhancement steps and returns the full EnhancedMasterCVData.
 
    Args:
        cv                    : parsed MasterCVData from the frontend request
        role_skill_collection : skill list for the candidate's role/domain,
                                received from the frontend alongside the masterCV
    """
 
 
 
    # 0. Resolve domain & subDomain — infer if missing so all downstream
    #    steps (scoring, gap analysis, AI score) have consistent context.
    #    If both are already present in the CV this is a no-op (no API call made).
    resolved_domain, resolved_subdomain = await infer_domain(cv)
    cv.domain    = resolved_domain
    cv.subDomain = resolved_subdomain   # plain string from here on
 
    # 1. Enhance text fields + rewrite challenges as STAR
    enhanced = await enhance_cv_fields(cv)
 
    # 2. Fetch existing user skills from MongoDB (Skill collection)
    raw_mongo_skills: list = []
    try:
        if not cv.userId:
            raise StopIteration   # skip lookup cleanly
        skill_doc = await db.resume_skill_collection.find_one(
            {"userId": cv.userId},
            {"_id": 0, "userId": 0},
        )
        if skill_doc:
            raw_mongo_skills = skill_doc.get("skills", [])
    except Exception:
        pass  # non-fatal — proceed without DB skills
 
    # 3. Score existing skills from MongoDB
    scored_existing = await score_existing_skills(raw_mongo_skills, cv)
 
    # 4. Extract skills from challenges
    challenge_skills = await extract_skills_from_challenges(cv)
 
    # 5. Merge — deduplicate by skillName (challenge skills supplement, not replace)
    existing_names = {s.get("skillName", "").lower() for s in scored_existing}
    unique_challenge_skills = [
        s for s in challenge_skills
        if s.get("skillName", "").lower() not in existing_names
    ]
    all_skills = scored_existing + unique_challenge_skills
 
    # Normalise — ensure scoreBreakdown always exists so Pydantic never fails
    # even when the model omits it
    for s in all_skills:
        if "scoreBreakdown" not in s or not s["scoreBreakdown"]:
            role = s.get("roleAlignment") or 0
            exp  = s.get("experienceWeight") or 0
            s["scoreBreakdown"] = {"roleAlignment": role, "experienceWeight": exp}
 
    # 6. Identify skill gaps
    skill_gaps_raw = await identify_skill_gaps(all_skills, role_skill_collection, cv)
 
    # Normalise skill_gaps scoreBreakdown
    for g in skill_gaps_raw:
        if "scoreBreakdown" not in g or not g["scoreBreakdown"]:
            g["scoreBreakdown"] = {
                "roleAlignment": g.get("roleAlignment") or 0,
                "demandWeight":  g.get("demandWeight")  or 0,
            }
 
    # 7. AI score
    ai_score = await calculate_ai_score(cv, enhanced, all_skills, skill_gaps_raw)
 
    # 8. Build ai_impacts
    ai_impacts = build_ai_impacts(cv, enhanced)
 
    # 9. Build enhanced_challenges (STAR format)
    enhanced_challenges = [
        EnhancedChallenge(
            challengeName=ch.get("challengeName", ""),
            situation=ch.get("situation", ""),
            task=ch.get("task", ""),
            action=ch.get("action", ""),
            result=ch.get("result", ""),
        )
        for ch in enhanced.get("challenges", [])
    ]
 
    # 10. Build enhanced_master_cv — use resolved domain/subDomain (never null)
    enhanced_cv = EnhancedMasterCV(
        fullName=cv.fullName,
        email=cv.email,
        phoneNumber=cv.phoneNumber,
        location=cv.location,
        linkedinUrl=cv.linkedinUrl,
        portfolioUrl=cv.portfolioUrl,
        resumeLink=cv.resumeLink,
        currentRole=cv.currentRole,
        careerStage=cv.careerStage,
        languages=cv.languages,
        experienceYear=int(cv.experienceYear) if cv.experienceYear else None,
        domain=resolved_domain,
        subDomain=resolved_subdomain,
        industry=cv.industry,
        bio=enhanced.get("bio", cv.bio),
        resumeSummary=enhanced.get("resumeSummary", cv.resumeSummary),
        carrierGoal=enhanced.get("carrierGoal", cv.carrierGoal),
        strength=enhanced.get("strength", cv.strength),
        workExperiences=[
            WorkExperienceOut(**w) for w in enhanced.get("workExperiences", []) if w
        ] or None,
        educationsAndCertifications=cv.educationsAndCertifications,
        accomplishments=cv.accomplishments,
        appliedGigs=cv.appliedGigs,
        savedGigs=cv.savedGigs,
        mentorProfile=cv.mentorProfile,
        resumeSections=cv.resumeSections,
        generatedCvJson=cv.generatedCvJson,
        lastGeneratedAt=cv.lastGeneratedAt,
        refletions=cv.refletions,
    )
 
    # 11. Assemble final response data
    return EnhancedMasterCVData(
        userId=cv.userId or "unknown",
        generatedAt=datetime.now(timezone.utc).isoformat(),
        ai_score=ai_score,
        skills=[SkillOut(**s) for s in all_skills],
        skill_gaps=[SkillGapOut(**g) for g in skill_gaps_raw],
        ai_impacts=ai_impacts,
        enhanced_challenges=enhanced_challenges,
        enhanced_master_cv=enhanced_cv,
    )
 
# ─────────────────────────────────────────────
# ENHANCE SINGLE CHALLENGE ENDPOINT
# ─────────────────────────────────────────────
 
ENHANCE_CHALLENGE_SYSTEM = """
You are a senior career coach specialising in impactful storytelling.
You will receive a raw STAR story (Situation, Task, Action, Result) from a candidate.
 
Your job:
1. Enhance each field to be vivid, specific, and achievement-oriented.
   - Situation: 2-3 sentences setting clear context.
   - Task: 1-2 sentences defining the responsibility or problem to solve.
   - Action: 2-3 sentences describing concrete steps taken (use active verbs).
   - Result: 1-2 sentences with measurable outcomes where possible.
2. Infer a concise challengeName (3-6 words) from the full story.
   It must describe WHAT the challenge was, not who solved it.
   Example: "Monolith to Microservices Migration", "Production Outage Resolution",
   "Zero-Downtime Database Migration".
 
Rules:
- Do NOT invent metrics, tools, or facts not present in the input.
- Stay 100% truthful — only enrich language and clarity.
 
Return ONLY valid JSON:
{
  "challengeName": "string",
  "situation": "string",
  "task": "string",
  "action": "string",
  "result": "string"
}
"""
 
 
async def enhance_challenge(req: EnhanceChallengeRequest) -> EnhanceChallengeData:
    user_prompt = f"""
Situation : {req.situation}
Task      : {req.task}
Action    : {req.action}
Result    : {req.result}
""".strip()
 
    result = await _call_openai(ENHANCE_CHALLENGE_SYSTEM, user_prompt)
 
    return EnhanceChallengeData(
        userId=req.userId,
        challengeName=result.get("challengeName", ""),
        situation=result.get("situation", ""),
        task=result.get("task", ""),
        action=result.get("action", ""),
        result=result.get("result", ""),
    )
 

# import json
# from datetime import datetime, timezone
# from openai import AsyncOpenAI
# from app.DB.mongodb.mongodb import MongoDB
# from app.Services.masterCV.masterCV_schema import (
#     MasterCVData,
#     EnhancedMasterCVData,
#     SkillOut,
#     SkillGapOut,
#     AIImpact,
#     EnhancedChallenge,
#     AIScore,
#     AIScoreBreakdown,
#     ScoreBreakdown,
#     GapScoreBreakdown,
#     EnhancedMasterCV,
#     WorkExperienceOut,
#     EnhanceChallengeRequest,
#     EnhanceChallengeData,
# )
 
# client = AsyncOpenAI()
# db = MongoDB()
 
 
# # ─────────────────────────────────────────────
# # HELPERS
# # ─────────────────────────────────────────────
 
# def _grade(total: int) -> str:
#     if total >= 90: return "S"
#     if total >= 75: return "A"
#     if total >= 60: return "B"
#     if total >= 45: return "C"
#     return "D"
 
 
# async def _call_openai(system: str, user: str, model: str = "gpt-4o") -> dict:
#     """Call OpenAI and parse JSON response."""
#     response = await client.chat.completions.create(
#         model=model,
#         temperature=0.3,
#         response_format={"type": "json_object"},
#         messages=[
#             {"role": "system", "content": system},
#             {"role": "user",   "content": user},
#         ],
#     )
#     return json.loads(response.choices[0].message.content)
 
 
# # ─────────────────────────────────────────────
# # STEP 0 — Infer domain & subDomain if missing
# # ─────────────────────────────────────────────
 
# DOMAIN_INFER_SYSTEM = """
# You are an expert career domain classifier.
# Given a candidate's profile data, infer the most accurate domain and subDomain
# for their professional background.
 
# Use ALL available signals in this priority order:
#   1. currentRole  — strongest signal
#   2. workExperiences (positions, responsibilities, projects)
#   3. challenges (what problems they solved)
#   4. skills / tech stack mentioned anywhere
#   5. industry + bio as soft context
 
# Rules:
# - domain: broad professional area (e.g. "Software Engineering", "Data Science",
#   "Product Management", "UX Design", "DevOps", "Cybersecurity", "Mobile Engineering")
# - subDomain: specific focus within the domain (e.g. "Backend Development",
#   "ML Engineering", "iOS Engineering", "Cloud Infrastructure")
# - Be specific — prefer "Backend Development" over "Engineering"
# - If the profile is genuinely multi-domain, pick the DOMINANT hiring identity
# - Never return null — always make your best inference
 
# Return ONLY valid JSON:
# {
#   "domain": "string",
#   "subDomain": "string",
#   "confidence": "High | Medium | Low",
#   "reasoning": "string (1 sentence explaining the inference)"
# }
# """
 
 
# async def infer_domain(cv: MasterCVData) -> tuple[str, str]:
#     """
#     Returns (domain, subDomain).
#     If both are already present in the CV, returns them as-is (no API call).
#     If either is missing or empty, infers both from the full CV context.
#     """
#     # subDomain may be List[str] or str — normalise to plain string
#     def _first(val):
#         if isinstance(val, list): return val[0].strip() if val else ""
#         return (val or "").strip()
 
#     domain_present    = bool(cv.domain and _first(cv.domain))
#     subdomain_present = bool(cv.subDomain and _first(cv.subDomain))
 
#     if domain_present and subdomain_present:
#         return _first(cv.domain), _first(cv.subDomain)
 
#     # Build context from whatever fields are available
#     work_summary = ""
#     if cv.workExperiences:
#         work_summary = "; ".join(
#             f"{w.role} at {w.companyName}: {', '.join(w.responsibilities or [])}"
#             for w in cv.workExperiences[:3]
#         )
 
#     challenge_summary = ""
#     if cv.challenges:
#         challenge_summary = "; ".join(
#             f"{c.situation or ''}: {c.action or ''}"
#             for c in cv.challenges[:3]
#         )
 
#     user_prompt = f"""
# currentRole      : {cv.currentRole or 'Not provided'}
# industry         : {cv.industry or 'Not provided'}
# bio              : {cv.bio or 'Not provided'}
# resumeSummary    : {cv.resumeSummary or 'Not provided'}
# domain (given)   : {cv.domain or 'MISSING'}
# subDomain (given): {cv.subDomain or 'MISSING'}
# workExperiences  : {work_summary or 'Not provided'}
# challenges       : {challenge_summary or 'Not provided'}
# strength         : {', '.join(cv.strength or []) or 'Not provided'}
# """
#     result = await _call_openai(DOMAIN_INFER_SYSTEM, user_prompt)
 
#     inferred_domain    = result.get("domain",    _first(cv.domain)    or "Software Engineering")
#     inferred_subdomain = result.get("subDomain", _first(cv.subDomain) or "General")
 
#     return str(inferred_domain).strip(), str(inferred_subdomain).strip()
 
 
# # ─────────────────────────────────────────────
# # STEP 1 — Enhance CV text fields
# # ─────────────────────────────────────────────
 
# ENHANCE_SYSTEM = """
# You are a senior career coach and professional CV writer.
# Enhance the given fields from a candidate's MasterCV to be more impactful,
# specific, and achievement-oriented while staying 100% truthful to the
# original content. Do not invent metrics or facts.
 
# Return ONLY valid JSON matching this schema (no extra keys):
# {
#   "bio": "string",
#   "resumeSummary": "string",
#   "carrierGoal": "string",
#   "strength": ["string"],
#   "workExperiences": [
#     {
#       "company": "string",
#       "position": "string",
#       "duration": "string",
#       "responsibilities": "string",
#       "projects": ["string"]
#     }
#   ],
#   "challenges": [
#     {
#       "challengeName": "string",
#       "situation": "string",
#       "task": "string",
#       "action": "string",
#       "result": "string"
#     }
#   ]
# }
 
# Rules:
# - bio: 2-3 punchy sentences. Lead with seniority + years + domain impact.
# - resumeSummary: 2-3 sentences. Highlight tech stack, scale, and key achievement.
# - carrierGoal: 1-2 sentences. Connect current expertise to ambition concretely.
# - strength: each item should be 1 sentence with a concrete example from the CV.
# - workExperiences[].responsibilities: rewrite with active verbs, scale, and outcomes.
# - challenges: input already has situation, task, action, result. Enhance each to be vivid and impactful (2-3 sentences each). Infer challengeName (3-6 words) from the full STAR story summarising what the challenge WAS (e.g. "Monolith to Microservices Migration").v
# """
 
 
# async def enhance_cv_fields(cv: MasterCVData) -> dict:
#     user_prompt = f"""
# Role: {cv.currentRole}
# Domain: {cv.domain} / {cv.subDomain}
# Career stage: {cv.careerStage}
# Total experience: {cv.totalExperienceYear} years
 
# bio: {cv.bio}
# resumeSummary: {cv.resumeSummary}
# carrierGoal: {cv.carrierGoal}
# strength: {json.dumps(cv.strength)}
# workExperiences: {json.dumps([w.model_dump() for w in (cv.workExperiences or [])])}
# challenges: {json.dumps([c.model_dump() for c in (cv.challenges or [])])}
# """
#     return await _call_openai(ENHANCE_SYSTEM, user_prompt)
 
 
# # ─────────────────────────────────────────────
# # STEP 2 — Extract & score skills from challenges
# # ─────────────────────────────────────────────
 
# SKILL_EXTRACT_SYSTEM = """
# You are a technical skill extraction engine.
# Given challenges from a candidate's CV and their role/domain context,
# extract all implied or explicit technical and soft skills.
 
# For each skill calculate:
# - roleAlignment (0-100): how relevant is this skill to their currentRole and domain?
# - experienceWeight (0-100): based on the context, how experienced do they seem?
# - score (0-100): weighted average — (roleAlignment * 0.6) + (experienceWeight * 0.4)
 
# Return ONLY valid JSON:
# {
#   "skills": [
#     {
#       "skillName": "string",
#       "skillCategory": "string",
#       "proficiencyLevel": "Beginner | Intermediate | Advanced | Expert",
#       "yearOfExperience": 0,
#       "source": "MASTER_CV",
#       "score": 0,
#       "scoreBreakdown": {
#         "roleAlignment": 0,
#         "experienceWeight": 0
#       }
#     }
#   ]
# }
 
# Rules:
# - Extract concrete technical skills only (no generic words like "communication").
# - Avoid duplicating skills that would obviously already be in their base skill set.
# - yearOfExperience: estimate from context clues; default to 1 if unclear.
# - Max 10 skills per call.
# """
 
 
# async def extract_skills_from_challenges(cv: MasterCVData) -> list[dict]:
#     if not cv.challenges:
#         return []
 
#     user_prompt = f"""
# currentRole: {cv.currentRole}
# domain: {cv.domain}
# subDomain: {cv.subDomain}
# careerStage: {cv.careerStage}
 
# Challenges:
# {json.dumps([c.model_dump() for c in cv.challenges])}
# """
#     result = await _call_openai(SKILL_EXTRACT_SYSTEM, user_prompt)
#     return result.get("skills", [])
 
 
# # ─────────────────────────────────────────────
# # STEP 3 — Score existing skills from MongoDB
# # ─────────────────────────────────────────────
 
# SKILL_SCORE_SYSTEM = """
# You are a technical skill evaluator.
# Given a list of skills the candidate already has and their role/domain context,
# score each skill.
 
# For each skill calculate:
# - roleAlignment (0-100): relevance to currentRole and domain
# - experienceWeight (0-100): inferred from yearsOfExperience vs expected for the role
# - score (0-100): (roleAlignment * 0.6) + (experienceWeight * 0.4)
# - proficiencyLevel: infer from score — <40 Beginner, 40-65 Intermediate, 66-80 Advanced, >80 Expert
 
# Return ONLY valid JSON:
# {
#   "skills": [
#     {
#       "skillName": "string",
#       "skillCategory": "string",
#       "proficiencyLevel": "string",
#       "yearOfExperience": 0,
#       "source": "MASTER_CV",
#       "score": 0,
#       "scoreBreakdown": {
#         "roleAlignment": 0,
#         "experienceWeight": 0
#       }
#     }
#   ]
# }
# """
 
 
# async def score_existing_skills(raw_skills: list, cv: MasterCVData) -> list[dict]:
#     if not raw_skills:
#         return []
 
#     user_prompt = f"""
# currentRole: {cv.currentRole}
# domain: {cv.domain}
# subDomain: {cv.subDomain}
# totalExperienceYear: {cv.totalExperienceYear}
 
# Skills to score:
# {json.dumps(raw_skills)}
# """
#     result = await _call_openai(SKILL_SCORE_SYSTEM, user_prompt)
#     return result.get("skills", [])
 
 
# # ─────────────────────────────────────────────
# # STEP 4 — Identify skill gaps
# # ─────────────────────────────────────────────
 
# SKILL_GAP_SYSTEM = """
# You are an expert technical career advisor.
# Given a candidate's current skills, role, domain, and a reference skill collection
# for that domain/role, identify skills the candidate is MISSING that are important
# for their career progression.
 
# For each gap:
# - roleAlignment (0-100): how relevant is this skill to their role/domain
# - demandWeight (0-100): how in-demand is this skill in the industry right now
# - score (0-100): (roleAlignment * 0.5) + (demandWeight * 0.5)
# - demandLevel: High (score >= 70), Medium (40-69), Low (<40)
# - sourceCollection: "ROLE_SKILLS" if it comes from the provided skill list,
#   "DOMAIN_INFERRED" if identified by you from domain knowledge
 
# Return ONLY valid JSON:
# {
#   "skill_gaps": [
#     {
#       "skillName": "string",
#       "skillCategory": "string",
#       "proficiencyLevel": "Beginner | Intermediate | Advanced",
#       "demandLevel": "High | Medium | Low",
#       "score": 0,
#       "scoreBreakdown": {
#         "roleAlignment": 0,
#         "demandWeight": 0
#       },
#       "gapReason": "string (2 sentences: why this is a gap for this role)",
#       "suggestion": "string (actionable 1-2 sentence learning path)",
#       "sourceCollection": "ROLE_SKILLS | DOMAIN_INFERRED"
#     }
#   ]
# }
 
# Rules:
# - Only surface MISSING skills — do not list skills the candidate already has.
# - Limit to the 6 most impactful gaps.
# - Sort by score descending (highest impact gap first).
# """
 
 
# async def identify_skill_gaps(
#     current_skills: list[dict],
#     role_skill_collection: list,
#     cv: MasterCVData,
# ) -> list[dict]:
#     user_prompt = f"""
# currentRole: {cv.currentRole}
# domain: {cv.domain}
# subDomain: {cv.subDomain}
# careerStage: {cv.careerStage}
# totalExperienceYear: {cv.totalExperienceYear}
 
# Candidate's current skills:
# {json.dumps([s.get("skillName") for s in current_skills])}
 
# Role/domain reference skill collection (from frontend):
# {json.dumps(role_skill_collection)}
# """
#     result = await _call_openai(SKILL_GAP_SYSTEM, user_prompt)
#     return result.get("skill_gaps", [])
 
 
# # ─────────────────────────────────────────────
# # STEP 5 — Calculate AI score
# # ─────────────────────────────────────────────
 
# AI_SCORE_SYSTEM = """
# You are a CV quality evaluator.
# Given a candidate's enhanced MasterCV data, score their profile on 5 dimensions.
# Each dimension is 0-100. Return the total as a weighted average.
 
# Weights:
#   profileCompleteness : 15%  — % of important fields that are non-null and detailed
#   skillRelevance      : 30%  — avg skill score relative to role/domain
#   experienceClarity   : 25%  — specificity and impact of work experience descriptions
#   careerNarrative     : 20%  — coherence of bio + resumeSummary + carrierGoal + challenges
#   skillGapSeverity    : 10%  — INVERSE score: more/worse gaps = lower score
 
# Grading: S=90+, A=75-89, B=60-74, C=45-59, D=<45
 
# Return ONLY valid JSON:
# {
#   "breakdown": {
#     "profileCompleteness": 0,
#     "skillRelevance": 0,
#     "experienceClarity": 0,
#     "careerNarrative": 0,
#     "skillGapSeverity": 0
#   },
#   "summary": "string (2-3 sentence plain-English summary of the profile strengths and main gaps)"
# }
# """
 
 
# async def calculate_ai_score(
#     cv: MasterCVData,
#     enhanced: dict,
#     skills: list[dict],
#     skill_gaps: list[dict],
# ) -> AIScore:
#     user_prompt = f"""
# currentRole: {cv.currentRole}
# domain: {cv.domain}
# subDomain: {cv.subDomain}
# careerStage: {cv.careerStage}
 
# Enhanced bio: {enhanced.get('bio', '')}
# Enhanced resumeSummary: {enhanced.get('resumeSummary', '')}
# Enhanced carrierGoal: {enhanced.get('carrierGoal', '')}
# Strengths count: {len(enhanced.get('strength', []))}
# Work experiences count: {len(enhanced.get('workExperiences', []))}
 
# Skills (count {len(skills)}), avg score: {
#     round(sum(s.get('score', 0) for s in skills) / len(skills)) if skills else 0
# }
# Skill gaps count: {len(skill_gaps)}
# High-demand gaps: {sum(1 for g in skill_gaps if g.get('demandLevel') == 'High')}
# """
#     result = await _call_openai(AI_SCORE_SYSTEM, user_prompt)
#     breakdown = result.get("breakdown", {})
 
#     total = round(
#         breakdown.get("profileCompleteness", 0) * 0.15
#         + breakdown.get("skillRelevance", 0) * 0.30
#         + breakdown.get("experienceClarity", 0) * 0.25
#         + breakdown.get("careerNarrative", 0) * 0.20
#         + breakdown.get("skillGapSeverity", 0) * 0.10
#     )
 
#     return AIScore(
#         total=total,
#         grade=_grade(total),
#         summary=result.get("summary", ""),
#         breakdown=AIScoreBreakdown(**breakdown),
#     )
 
 
# # ─────────────────────────────────────────────
# # STEP 6 — Build ai_impacts (original vs enhanced diff)
# # ─────────────────────────────────────────────
 
# def build_ai_impacts(cv: MasterCVData, enhanced: dict) -> list[AIImpact]:
#     impacts: list[AIImpact] = []
 
#     def _add(field: str, original: str, enhanced_val: str):
#         if original and enhanced_val and original.strip() != enhanced_val.strip():
#             impacts.append(AIImpact(
#                 field=field,
#                 original=original,
#                 enhanced=enhanced_val,
#             ))
 
#     _add("bio", cv.bio or "", enhanced.get("bio", ""))
#     _add("resumeSummary", cv.resumeSummary or "", enhanced.get("resumeSummary", ""))
#     _add("carrierGoal", cv.carrierGoal or "", enhanced.get("carrierGoal", ""))
 
#     orig_strengths = cv.strength or []
#     new_strengths  = enhanced.get("strength", [])
#     for i, (orig, enh) in enumerate(zip(orig_strengths, new_strengths)):
#         _add(f"strength[{i}]", orig, enh)
 
#     orig_exps = cv.workExperiences or []
#     new_exps  = enhanced.get("workExperiences", [])
#     for i, (orig, enh) in enumerate(zip(orig_exps, new_exps)):
#         _add(
#             f"workExperiences[{i}].responsibilities",
#             ', '.join(orig.responsibilities or []) if isinstance(orig.responsibilities, list) else (orig.responsibilities or ''),
#             enh.get("responsibilities", ""),
#         )
 
#     return impacts
 
 
# # ─────────────────────────────────────────────
# # MAIN SERVICE ENTRY POINT
# # ─────────────────────────────────────────────
 
# async def enhance_master_cv(
#     cv: MasterCVData,
#     role_skill_collection: list,
# ) -> EnhancedMasterCVData:
#     """
#     Orchestrates all enhancement steps and returns the full EnhancedMasterCVData.
 
#     Args:
#         cv                    : parsed MasterCVData from the frontend request
#         role_skill_collection : skill list for the candidate's role/domain,
#                                 received from the frontend alongside the masterCV
#     """
 
#     # 0. Resolve domain & subDomain — infer if missing so all downstream
#     #    steps (scoring, gap analysis, AI score) have consistent context.
#     #    If both are already present in the CV this is a no-op (no API call made).
#     resolved_domain, resolved_subdomain = await infer_domain(cv)
#     cv.domain    = resolved_domain
#     cv.subDomain = resolved_subdomain   # plain string from here on
 
#     # 1. Enhance text fields + rewrite challenges as STAR
#     enhanced = await enhance_cv_fields(cv)
 
#     # 2. Fetch existing user skills from MongoDB (Skill collection)
#     raw_mongo_skills: list = []
#     try:
#         skill_doc = await db.resume_skill_collection.find_one(
#             {"userId": cv.userId},
#             {"_id": 0, "userId": 0},
#         )
#         if skill_doc:
#             raw_mongo_skills = skill_doc.get("skills", [])
#     except Exception:
#         pass  # non-fatal — proceed without DB skills
 
#     # 3. Score existing skills from MongoDB
#     scored_existing = await score_existing_skills(raw_mongo_skills, cv)
 
#     # 4. Extract skills from challenges
#     challenge_skills = await extract_skills_from_challenges(cv)
 
#     # 5. Merge — deduplicate by skillName (challenge skills supplement, not replace)
#     existing_names = {s.get("skillName", "").lower() for s in scored_existing}
#     unique_challenge_skills = [
#         s for s in challenge_skills
#         if s.get("skillName", "").lower() not in existing_names
#     ]
#     all_skills = scored_existing + unique_challenge_skills
 
#     # Normalise — ensure scoreBreakdown always exists so Pydantic never fails
#     # even when the model omits it
#     for s in all_skills:
#         if "scoreBreakdown" not in s or not s["scoreBreakdown"]:
#             role = s.get("roleAlignment") or 0
#             exp  = s.get("experienceWeight") or 0
#             s["scoreBreakdown"] = {"roleAlignment": role, "experienceWeight": exp}
 
#     # 6. Identify skill gaps
#     skill_gaps_raw = await identify_skill_gaps(all_skills, role_skill_collection, cv)
 
#     # Normalise skill_gaps scoreBreakdown
#     for g in skill_gaps_raw:
#         if "scoreBreakdown" not in g or not g["scoreBreakdown"]:
#             g["scoreBreakdown"] = {
#                 "roleAlignment": g.get("roleAlignment") or 0,
#                 "demandWeight":  g.get("demandWeight")  or 0,
#             }
 
#     # 7. AI score
#     ai_score = await calculate_ai_score(cv, enhanced, all_skills, skill_gaps_raw)
 
#     # 8. Build ai_impacts
#     ai_impacts = build_ai_impacts(cv, enhanced)
 
#     # 9. Build enhanced_challenges (STAR format)
#     enhanced_challenges = [
#         EnhancedChallenge(
#             challengeName=ch.get("challengeName", ""),
#             situation=ch.get("situation", ""),
#             task=ch.get("task", ""),
#             action=ch.get("action", ""),
#             result=ch.get("result", ""),
#         )
#         for ch in enhanced.get("challenges", [])
#     ]
 
#     # 10. Build enhanced_master_cv — use resolved domain/subDomain (never null)
#     enhanced_cv = EnhancedMasterCV(
#         fullName=cv.fullName,
#         email=cv.email,
#         phoneNumber=cv.phoneNumber,
#         location=cv.location,
#         linkedinUrl=cv.linkedinUrl,
#         portfolioUrl=cv.portfolioUrl,
#         resumeLink=cv.resumeLink,
#         currentRole=cv.currentRole,
#         careerStage=cv.careerStage,
#         languages=cv.languages,
#         totalExperienceYear=int(cv.totalExperienceYear) if cv.totalExperienceYear else None,
#         domain=resolved_domain,
#         subDomain=resolved_subdomain,
#         industry=cv.industry,
#         bio=enhanced.get("bio", cv.bio),
#         resumeSummary=enhanced.get("resumeSummary", cv.resumeSummary),
#         carrierGoal=enhanced.get("carrierGoal", cv.carrierGoal),
#         strength=enhanced.get("strength", cv.strength),
#         workExperiences=[
#             WorkExperienceOut(**w) for w in enhanced.get("workExperiences", [])
#         ],
#         educationsAndCertifications=cv.educationsAndCertifications,
#         accomplishments=cv.accomplishments,
#         appliedGigs=cv.appliedGigs,
#         savedGigs=cv.savedGigs,
#         mentorProfile=cv.mentorProfile,
#         resumeSections=cv.resumeSections,
#         generatedCvJson=cv.generatedCvJson,
#         lastGeneratedAt=cv.lastGeneratedAt,
#         refletions=cv.refletions,
#     )
 
#     # 11. Assemble final response data
#     return EnhancedMasterCVData(
#         userId=cv.userId,
#         generatedAt=datetime.now(timezone.utc).isoformat(),
#         ai_score=ai_score,
#         skills=[SkillOut(**s) for s in all_skills],
#         skill_gaps=[SkillGapOut(**g) for g in skill_gaps_raw],
#         ai_impacts=ai_impacts,
#         enhanced_challenges=enhanced_challenges,
#         enhanced_master_cv=enhanced_cv,
#     )
 
# # ─────────────────────────────────────────────
# # ENHANCE SINGLE CHALLENGE ENDPOINT
# # ─────────────────────────────────────────────
 
# ENHANCE_CHALLENGE_SYSTEM = """
# You are a senior career coach specialising in impactful storytelling.
# You will receive a raw STAR story (Situation, Task, Action, Result) from a candidate.
 
# Your job:
# 1. Enhance each field to be vivid, specific, and achievement-oriented.
#    - Situation: 2-3 sentences setting clear context.
#    - Task: 1-2 sentences defining the responsibility or problem to solve.
#    - Action: 2-3 sentences describing concrete steps taken (use active verbs).
#    - Result: 1-2 sentences with measurable outcomes where possible.
# 2. Infer a concise challengeName (3-6 words) from the full story.
#    It must describe WHAT the challenge was, not who solved it.
#    Example: "Monolith to Microservices Migration", "Production Outage Resolution",
#    "Zero-Downtime Database Migration".
 
# Rules:
# - Do NOT invent metrics, tools, or facts not present in the input.
# - Stay 100% truthful — only enrich language and clarity.
 
# Return ONLY valid JSON:
# {
#   "challengeName": "string",
#   "situation": "string",
#   "task": "string",
#   "action": "string",
#   "result": "string"
# }
# """
 
 
# async def enhance_challenge(req: EnhanceChallengeRequest) -> EnhanceChallengeData:
#     user_prompt = f"""
# Situation : {req.situation}
# Task      : {req.task}
# Action    : {req.action}
# Result    : {req.result}
# """.strip()
 
#     result = await _call_openai(ENHANCE_CHALLENGE_SYSTEM, user_prompt)
 
#     return EnhanceChallengeData(
#         userId=req.userId,
#         challengeName=result.get("challengeName", ""),
#         situation=result.get("situation", ""),
#         task=result.get("task", ""),
#         action=result.get("action", ""),
#         result=result.get("result", ""),
#     )
# import json
# from datetime import datetime, timezone
# from openai import AsyncOpenAI
# from app.DB.mongodb.mongodb import MongoDB
# from app.Services.masterCV.masterCV_schema import (
#     MasterCVData,
#     EnhancedMasterCVData,
#     SkillOut,
#     SkillGapOut,
#     AIImpact,
#     EnhancedChallenge,
#     AIScore,
#     AIScoreBreakdown,
#     ScoreBreakdown,
#     GapScoreBreakdown,
#     EnhancedMasterCV,
#     WorkExperienceOut,
#     EnhanceChallengeRequest,
#     EnhanceChallengeData,
# )

# client = AsyncOpenAI()
# db = MongoDB()


# # ─────────────────────────────────────────────
# # HELPERS
# # ─────────────────────────────────────────────

# def _grade(total: int) -> str:
#     if total >= 90: return "S"
#     if total >= 75: return "A"
#     if total >= 60: return "B"
#     if total >= 45: return "C"
#     return "D"


# async def _call_openai(system: str, user: str, model: str = "gpt-4o") -> dict:
#     """Call OpenAI and parse JSON response."""
#     response = await client.chat.completions.create(
#         model=model,
#         temperature=0.3,
#         response_format={"type": "json_object"},
#         messages=[
#             {"role": "system", "content": system},
#             {"role": "user",   "content": user},
#         ],
#     )
#     return json.loads(response.choices[0].message.content)


# # ─────────────────────────────────────────────
# # STEP 0 — Infer domain & subDomain if missing
# # ─────────────────────────────────────────────

# DOMAIN_INFER_SYSTEM = """
# You are an expert career domain classifier.
# Given a candidate's profile data, infer the most accurate domain and subDomain
# for their professional background.

# Use ALL available signals in this priority order:
#   1. currentRole  — strongest signal
#   2. workExperiences (positions, responsibilities, projects)
#   3. challenges (what problems they solved)
#   4. skills / tech stack mentioned anywhere
#   5. industry + bio as soft context

# Rules:
# - domain: broad professional area (e.g. "Software Engineering", "Data Science",
#   "Product Management", "UX Design", "DevOps", "Cybersecurity", "Mobile Engineering")
# - subDomain: specific focus within the domain (e.g. "Backend Development",
#   "ML Engineering", "iOS Engineering", "Cloud Infrastructure")
# - Be specific — prefer "Backend Development" over "Engineering"
# - If the profile is genuinely multi-domain, pick the DOMINANT hiring identity
# - Never return null — always make your best inference

# Return ONLY valid JSON:
# {
#   "domain": "string",
#   "subDomain": "string",
#   "confidence": "High | Medium | Low",
#   "reasoning": "string (1 sentence explaining the inference)"
# }
# """


# async def infer_domain(cv: MasterCVData) -> tuple[str, str]:
#     """
#     Returns (domain, subDomain).
#     If both are already present in the CV, returns them as-is (no API call).
#     If either is missing or empty, infers both from the full CV context.
#     """
#     domain_present    = cv.domain    and cv.domain.strip()
#     subdomain_present = cv.subDomain and cv.subDomain.strip()

#     if domain_present and subdomain_present:
#         return cv.domain.strip(), cv.subDomain.strip()

#     # Build context from whatever fields are available
#     work_summary = ""
#     if cv.workExperiences:
#         work_summary = "; ".join(
#             f"{w.position} at {w.company}: {w.responsibilities or ''}"
#             for w in cv.workExperiences[:3]
#         )

#     challenge_summary = ""
#     if cv.challenges:
#         challenge_summary = "; ".join(
#             f"{c.challengeName}: {c.achievement or ''}"
#             for c in cv.challenges[:3]
#         )

#     user_prompt = f"""
# currentRole      : {cv.currentRole or 'Not provided'}
# industry         : {cv.industry or 'Not provided'}
# bio              : {cv.bio or 'Not provided'}
# resumeSummary    : {cv.resumeSummary or 'Not provided'}
# domain (given)   : {cv.domain or 'MISSING'}
# subDomain (given): {cv.subDomain or 'MISSING'}
# workExperiences  : {work_summary or 'Not provided'}
# challenges       : {challenge_summary or 'Not provided'}
# strength         : {', '.join(cv.strength or []) or 'Not provided'}
# """
#     result = await _call_openai(DOMAIN_INFER_SYSTEM, user_prompt)

#     inferred_domain    = result.get("domain",    cv.domain    or "Software Engineering")
#     inferred_subdomain = result.get("subDomain", cv.subDomain or "General")

#     return inferred_domain.strip(), inferred_subdomain.strip()


# # ─────────────────────────────────────────────
# # STEP 1 — Enhance CV text fields
# # ─────────────────────────────────────────────

# ENHANCE_SYSTEM = """
# You are a senior career coach and professional CV writer.
# Enhance the given fields from a candidate's MasterCV to be more impactful,
# specific, and achievement-oriented while staying 100% truthful to the
# original content. Do not invent metrics or facts.

# Return ONLY valid JSON matching this schema (no extra keys):
# {
#   "bio": "string",
#   "resumeSummary": "string",
#   "carrierGoal": "string",
#   "strength": ["string"],
#   "workExperiences": [
#     {
#       "company": "string",
#       "position": "string",
#       "duration": "string",
#       "responsibilities": "string",
#       "projects": ["string"]
#     }
#   ],
#   "challenges": [
#     {
#       "challengeName": "string",
#       "situation": "string",
#       "task": "string",
#       "action": "string",
#       "result": "string"
#     }
#   ]
# }

# Rules:
# - bio: 2-3 punchy sentences. Lead with seniority + years + domain impact.
# - resumeSummary: 2-3 sentences. Highlight tech stack, scale, and key achievement.
# - carrierGoal: 1-2 sentences. Connect current expertise to ambition concretely.
# - strength: each item should be 1 sentence with a concrete example from the CV.
# - workExperiences[].responsibilities: rewrite with active verbs, scale, and outcomes.
# - challenges: input already has situation, task, action, result. Enhance each to be vivid and impactful (2-3 sentences each). Infer challengeName (3-6 words) from the full STAR story summarising what the challenge WAS (e.g. "Monolith to Microservices Migration").v
# """


# async def enhance_cv_fields(cv: MasterCVData) -> dict:
#     user_prompt = f"""
# Role: {cv.currentRole}
# Domain: {cv.domain} / {cv.subDomain}
# Career stage: {cv.careerStage}
# Total experience: {cv.totalExperienceYear} years

# bio: {cv.bio}
# resumeSummary: {cv.resumeSummary}
# carrierGoal: {cv.carrierGoal}
# strength: {json.dumps(cv.strength)}
# workExperiences: {json.dumps([w.model_dump() for w in (cv.workExperiences or [])])}
# challenges: {json.dumps([c.model_dump() for c in (cv.challenges or [])])}
# """
#     return await _call_openai(ENHANCE_SYSTEM, user_prompt)


# # ─────────────────────────────────────────────
# # STEP 2 — Extract & score skills from challenges
# # ─────────────────────────────────────────────

# SKILL_EXTRACT_SYSTEM = """
# You are a technical skill extraction engine.
# Given challenges from a candidate's CV and their role/domain context,
# extract all implied or explicit technical and soft skills.

# For each skill calculate:
# - roleAlignment (0-100): how relevant is this skill to their currentRole and domain?
# - experienceWeight (0-100): based on the context, how experienced do they seem?
# - score (0-100): weighted average — (roleAlignment * 0.6) + (experienceWeight * 0.4)

# Return ONLY valid JSON:
# {
#   "skills": [
#     {
#       "skillName": "string",
#       "skillCategory": "string",
#       "proficiencyLevel": "Beginner | Intermediate | Advanced | Expert",
#       "yearOfExperience": 0,
#       "source": "MASTER_CV",
#       "score": 0,
#       "scoreBreakdown": {
#         "roleAlignment": 0,
#         "experienceWeight": 0
#       }
#     }
#   ]
# }

# Rules:
# - Extract concrete technical skills only (no generic words like "communication").
# - Avoid duplicating skills that would obviously already be in their base skill set.
# - yearOfExperience: estimate from context clues; default to 1 if unclear.
# - Max 10 skills per call.
# """


# async def extract_skills_from_challenges(cv: MasterCVData) -> list[dict]:
#     if not cv.challenges:
#         return []

#     user_prompt = f"""
# currentRole: {cv.currentRole}
# domain: {cv.domain}
# subDomain: {cv.subDomain}
# careerStage: {cv.careerStage}

# Challenges:
# {json.dumps([c.model_dump() for c in cv.challenges])}
# """
#     result = await _call_openai(SKILL_EXTRACT_SYSTEM, user_prompt)
#     return result.get("skills", [])


# # ─────────────────────────────────────────────
# # STEP 3 — Score existing skills from MongoDB
# # ─────────────────────────────────────────────

# SKILL_SCORE_SYSTEM = """
# You are a technical skill evaluator.
# Given a list of skills the candidate already has and their role/domain context,
# score each skill.

# For each skill calculate:
# - roleAlignment (0-100): relevance to currentRole and domain
# - experienceWeight (0-100): inferred from yearsOfExperience vs expected for the role
# - score (0-100): (roleAlignment * 0.6) + (experienceWeight * 0.4)
# - proficiencyLevel: infer from score — <40 Beginner, 40-65 Intermediate, 66-80 Advanced, >80 Expert

# Return ONLY valid JSON:
# {
#   "skills": [
#     {
#       "skillName": "string",
#       "skillCategory": "string",
#       "proficiencyLevel": "string",
#       "yearOfExperience": 0,
#       "source": "MASTER_CV",
#       "score": 0,
#       "scoreBreakdown": {
#         "roleAlignment": 0,
#         "experienceWeight": 0
#       }
#     }
#   ]
# }
# """


# async def score_existing_skills(raw_skills: list, cv: MasterCVData) -> list[dict]:
#     if not raw_skills:
#         return []

#     user_prompt = f"""
# currentRole: {cv.currentRole}
# domain: {cv.domain}
# subDomain: {cv.subDomain}
# totalExperienceYear: {cv.totalExperienceYear}

# Skills to score:
# {json.dumps(raw_skills)}
# """
#     result = await _call_openai(SKILL_SCORE_SYSTEM, user_prompt)
#     return result.get("skills", [])


# # ─────────────────────────────────────────────
# # STEP 4 — Identify skill gaps
# # ─────────────────────────────────────────────

# SKILL_GAP_SYSTEM = """
# You are an expert technical career advisor.
# Given a candidate's current skills, role, domain, and a reference skill collection
# for that domain/role, identify skills the candidate is MISSING that are important
# for their career progression.

# For each gap:
# - roleAlignment (0-100): how relevant is this skill to their role/domain
# - demandWeight (0-100): how in-demand is this skill in the industry right now
# - score (0-100): (roleAlignment * 0.5) + (demandWeight * 0.5)
# - demandLevel: High (score >= 70), Medium (40-69), Low (<40)
# - sourceCollection: "ROLE_SKILLS" if it comes from the provided skill list,
#   "DOMAIN_INFERRED" if identified by you from domain knowledge

# Return ONLY valid JSON:
# {
#   "skill_gaps": [
#     {
#       "skillName": "string",
#       "skillCategory": "string",
#       "proficiencyLevel": "Beginner | Intermediate | Advanced",
#       "demandLevel": "High | Medium | Low",
#       "score": 0,
#       "scoreBreakdown": {
#         "roleAlignment": 0,
#         "demandWeight": 0
#       },
#       "gapReason": "string (2 sentences: why this is a gap for this role)",
#       "suggestion": "string (actionable 1-2 sentence learning path)",
#       "sourceCollection": "ROLE_SKILLS | DOMAIN_INFERRED"
#     }
#   ]
# }

# Rules:
# - Only surface MISSING skills — do not list skills the candidate already has.
# - Limit to the 6 most impactful gaps.
# - Sort by score descending (highest impact gap first).
# """


# async def identify_skill_gaps(
#     current_skills: list[dict],
#     role_skill_collection: list,
#     cv: MasterCVData,
# ) -> list[dict]:
#     user_prompt = f"""
# currentRole: {cv.currentRole}
# domain: {cv.domain}
# subDomain: {cv.subDomain}
# careerStage: {cv.careerStage}
# totalExperienceYear: {cv.totalExperienceYear}

# Candidate's current skills:
# {json.dumps([s.get("skillName") for s in current_skills])}

# Role/domain reference skill collection (from frontend):
# {json.dumps(role_skill_collection)}
# """
#     result = await _call_openai(SKILL_GAP_SYSTEM, user_prompt)
#     return result.get("skill_gaps", [])


# # ─────────────────────────────────────────────
# # STEP 5 — Calculate AI score
# # ─────────────────────────────────────────────

# AI_SCORE_SYSTEM = """
# You are a CV quality evaluator.
# Given a candidate's enhanced MasterCV data, score their profile on 5 dimensions.
# Each dimension is 0-100. Return the total as a weighted average.

# Weights:
#   profileCompleteness : 15%  — % of important fields that are non-null and detailed
#   skillRelevance      : 30%  — avg skill score relative to role/domain
#   experienceClarity   : 25%  — specificity and impact of work experience descriptions
#   careerNarrative     : 20%  — coherence of bio + resumeSummary + carrierGoal + challenges
#   skillGapSeverity    : 10%  — INVERSE score: more/worse gaps = lower score

# Grading: S=90+, A=75-89, B=60-74, C=45-59, D=<45

# Return ONLY valid JSON:
# {
#   "breakdown": {
#     "profileCompleteness": 0,
#     "skillRelevance": 0,
#     "experienceClarity": 0,
#     "careerNarrative": 0,
#     "skillGapSeverity": 0
#   },
#   "summary": "string (2-3 sentence plain-English summary of the profile strengths and main gaps)"
# }
# """


# async def calculate_ai_score(
#     cv: MasterCVData,
#     enhanced: dict,
#     skills: list[dict],
#     skill_gaps: list[dict],
# ) -> AIScore:
#     user_prompt = f"""
# currentRole: {cv.currentRole}
# domain: {cv.domain}
# subDomain: {cv.subDomain}
# careerStage: {cv.careerStage}

# Enhanced bio: {enhanced.get('bio', '')}
# Enhanced resumeSummary: {enhanced.get('resumeSummary', '')}
# Enhanced carrierGoal: {enhanced.get('carrierGoal', '')}
# Strengths count: {len(enhanced.get('strength', []))}
# Work experiences count: {len(enhanced.get('workExperiences', []))}

# Skills (count {len(skills)}), avg score: {
#     round(sum(s.get('score', 0) for s in skills) / len(skills)) if skills else 0
# }
# Skill gaps count: {len(skill_gaps)}
# High-demand gaps: {sum(1 for g in skill_gaps if g.get('demandLevel') == 'High')}
# """
#     result = await _call_openai(AI_SCORE_SYSTEM, user_prompt)
#     breakdown = result.get("breakdown", {})

#     total = round(
#         breakdown.get("profileCompleteness", 0) * 0.15
#         + breakdown.get("skillRelevance", 0) * 0.30
#         + breakdown.get("experienceClarity", 0) * 0.25
#         + breakdown.get("careerNarrative", 0) * 0.20
#         + breakdown.get("skillGapSeverity", 0) * 0.10
#     )

#     return AIScore(
#         total=total,
#         grade=_grade(total),
#         summary=result.get("summary", ""),
#         breakdown=AIScoreBreakdown(**breakdown),
#     )


# # ─────────────────────────────────────────────
# # STEP 6 — Build ai_impacts (original vs enhanced diff)
# # ─────────────────────────────────────────────

# def build_ai_impacts(cv: MasterCVData, enhanced: dict) -> list[AIImpact]:
#     impacts: list[AIImpact] = []

#     def _add(field: str, original: str, enhanced_val: str):
#         if original and enhanced_val and original.strip() != enhanced_val.strip():
#             impacts.append(AIImpact(
#                 field=field,
#                 original=original,
#                 enhanced=enhanced_val,
#             ))

#     _add("bio", cv.bio or "", enhanced.get("bio", ""))
#     _add("resumeSummary", cv.resumeSummary or "", enhanced.get("resumeSummary", ""))
#     _add("carrierGoal", cv.carrierGoal or "", enhanced.get("carrierGoal", ""))

#     orig_strengths = cv.strength or []
#     new_strengths  = enhanced.get("strength", [])
#     for i, (orig, enh) in enumerate(zip(orig_strengths, new_strengths)):
#         _add(f"strength[{i}]", orig, enh)

#     orig_exps = cv.workExperiences or []
#     new_exps  = enhanced.get("workExperiences", [])
#     for i, (orig, enh) in enumerate(zip(orig_exps, new_exps)):
#         _add(
#             f"workExperiences[{i}].responsibilities",
#             orig.responsibilities or "",
#             enh.get("responsibilities", ""),
#         )

#     return impacts


# # ─────────────────────────────────────────────
# # MAIN SERVICE ENTRY POINT
# # ─────────────────────────────────────────────

# async def enhance_master_cv(
#     cv: MasterCVData,
#     role_skill_collection: list,
# ) -> EnhancedMasterCVData:
#     """
#     Orchestrates all enhancement steps and returns the full EnhancedMasterCVData.

#     Args:
#         cv                    : parsed MasterCVData from the frontend request
#         role_skill_collection : skill list for the candidate's role/domain,
#                                 received from the frontend alongside the masterCV
#     """

#     # 0. Resolve domain & subDomain — infer if missing so all downstream
#     #    steps (scoring, gap analysis, AI score) have consistent context.
#     #    If both are already present in the CV this is a no-op (no API call made).
#     resolved_domain, resolved_subdomain = await infer_domain(cv)
#     cv.domain    = resolved_domain
#     cv.subDomain = resolved_subdomain

#     # 1. Enhance text fields + rewrite challenges as STAR
#     enhanced = await enhance_cv_fields(cv)

#     # 2. Fetch existing user skills from MongoDB (Skill collection)
#     raw_mongo_skills: list = []
#     try:
#         skill_doc = await db.resume_skill_collection.find_one(
#             {"userId": cv.userId},
#             {"_id": 0, "userId": 0},
#         )
#         if skill_doc:
#             raw_mongo_skills = skill_doc.get("skills", [])
#     except Exception:
#         pass  # non-fatal — proceed without DB skills

#     # 3. Score existing skills from MongoDB
#     scored_existing = await score_existing_skills(raw_mongo_skills, cv)

#     # 4. Extract skills from challenges
#     challenge_skills = await extract_skills_from_challenges(cv)

#     # 5. Merge — deduplicate by skillName (challenge skills supplement, not replace)
#     existing_names = {s.get("skillName", "").lower() for s in scored_existing}
#     unique_challenge_skills = [
#         s for s in challenge_skills
#         if s.get("skillName", "").lower() not in existing_names
#     ]
#     all_skills = scored_existing + unique_challenge_skills

#     # Normalise — ensure scoreBreakdown always exists so Pydantic never fails
#     # even when the model omits it
#     for s in all_skills:
#         if "scoreBreakdown" not in s or not s["scoreBreakdown"]:
#             role = s.get("roleAlignment") or 0
#             exp  = s.get("experienceWeight") or 0
#             s["scoreBreakdown"] = {"roleAlignment": role, "experienceWeight": exp}

#     # 6. Identify skill gaps
#     skill_gaps_raw = await identify_skill_gaps(all_skills, role_skill_collection, cv)

#     # Normalise skill_gaps scoreBreakdown
#     for g in skill_gaps_raw:
#         if "scoreBreakdown" not in g or not g["scoreBreakdown"]:
#             g["scoreBreakdown"] = {
#                 "roleAlignment": g.get("roleAlignment") or 0,
#                 "demandWeight":  g.get("demandWeight")  or 0,
#             }

#     # 7. AI score
#     ai_score = await calculate_ai_score(cv, enhanced, all_skills, skill_gaps_raw)

#     # 8. Build ai_impacts
#     ai_impacts = build_ai_impacts(cv, enhanced)

#     # 9. Build enhanced_challenges (STAR format)
#     enhanced_challenges = [
#         EnhancedChallenge(
#             challengeName=ch.get("challengeName", ""),
#             situation=ch.get("situation", ""),
#             task=ch.get("task", ""),
#             action=ch.get("action", ""),
#             result=ch.get("result", ""),
#         )
#         for ch in enhanced.get("challenges", [])
#     ]

#     # 10. Build enhanced_master_cv — use resolved domain/subDomain (never null)
#     enhanced_cv = EnhancedMasterCV(
#         fullName=cv.fullName,
#         email=cv.email,
#         phoneNumber=cv.phoneNumber,
#         location=cv.location,
#         linkedinUrl=cv.linkedinUrl,
#         portfolioUrl=cv.portfolioUrl,
#         resumeLink=cv.resumeLink,
#         currentRole=cv.currentRole,
#         careerStage=cv.careerStage,
#         languages=cv.languages,
#         totalExperienceYear=int(cv.totalExperienceYear) if cv.totalExperienceYear else None,
#         domain=resolved_domain,
#         subDomain=resolved_subdomain,
#         industry=cv.industry,
#         bio=enhanced.get("bio", cv.bio),
#         resumeSummary=enhanced.get("resumeSummary", cv.resumeSummary),
#         carrierGoal=enhanced.get("carrierGoal", cv.carrierGoal),
#         strength=enhanced.get("strength", cv.strength),
#         workExperiences=[
#             WorkExperienceOut(**w) for w in enhanced.get("workExperiences", [])
#         ],
#         educationsAndCertifications=cv.educationsAndCertifications,
#         accomplishments=cv.accomplishments,
#         appliedGigs=cv.appliedGigs,
#         savedGigs=cv.savedGigs,
#         mentorProfile=cv.mentorProfile,
#         resumeSections=cv.resumeSections,
#         generatedCvJson=cv.generatedCvJson,
#         lastGeneratedAt=cv.lastGeneratedAt,
#         refletions=cv.refletions,
#     )

#     # 11. Assemble final response data
#     return EnhancedMasterCVData(
#         userId=cv.userId,
#         generatedAt=datetime.now(timezone.utc).isoformat(),
#         ai_score=ai_score,
#         skills=[SkillOut(**s) for s in all_skills],
#         skill_gaps=[SkillGapOut(**g) for g in skill_gaps_raw],
#         ai_impacts=ai_impacts,
#         enhanced_challenges=enhanced_challenges,
#         enhanced_master_cv=enhanced_cv,
#     )

# # ─────────────────────────────────────────────
# # ENHANCE SINGLE CHALLENGE ENDPOINT
# # ─────────────────────────────────────────────
 
# ENHANCE_CHALLENGE_SYSTEM = """
# You are a senior career coach specialising in impactful storytelling.
# You will receive a raw STAR story (Situation, Task, Action, Result) from a candidate.
 
# Your job:
# 1. Enhance each field to be vivid, specific, and achievement-oriented.
#    - Situation: 2-3 sentences setting clear context.
#    - Task: 1-2 sentences defining the responsibility or problem to solve.
#    - Action: 2-3 sentences describing concrete steps taken (use active verbs).
#    - Result: 1-2 sentences with measurable outcomes where possible.
# 2. Infer a concise challengeName (3-6 words) from the full story.
#    It must describe WHAT the challenge was, not who solved it.
#    Example: "Monolith to Microservices Migration", "Production Outage Resolution",
#    "Zero-Downtime Database Migration".
 
# Rules:
# - Do NOT invent metrics, tools, or facts not present in the input.
# - Stay 100% truthful — only enrich language and clarity.
 
# Return ONLY valid JSON:
# {
#   "challengeName": "string",
#   "situation": "string",
#   "task": "string",
#   "action": "string",
#   "result": "string"
# }
# """
 
 
# async def enhance_challenge(req: EnhanceChallengeRequest) -> EnhanceChallengeData:
#     user_prompt = f"""
# Situation : {req.situation}
# Task      : {req.task}
# Action    : {req.action}
# Result    : {req.result}
# """.strip()
 
#     result = await _call_openai(ENHANCE_CHALLENGE_SYSTEM, user_prompt)
 
#     return EnhanceChallengeData(
#         userId=req.userId,
#         challengeName=result.get("challengeName", ""),
#         situation=result.get("situation", ""),
#         task=result.get("task", ""),
#         action=result.get("action", ""),
#         result=result.get("result", ""),
#     )
 

# working start
# import json
# from datetime import datetime, timezone
# from openai import AsyncOpenAI
# from app.DB.mongodb.mongodb import MongoDB
# from app.Services.masterCV.masterCV_schema import (
#     MasterCVData,
#     EnhancedMasterCVData,
#     SkillOut,
#     SkillGapOut,
#     AIImpact,
#     EnhancedChallenge,
#     AIScore,
#     AIScoreBreakdown,
#     ScoreBreakdown,
#     GapScoreBreakdown,
#     EnhancedMasterCV,
#     WorkExperienceOut,
# )

# client = AsyncOpenAI()
# db = MongoDB()


# # ─────────────────────────────────────────────
# # HELPERS
# # ─────────────────────────────────────────────

# def _grade(total: int) -> str:
#     if total >= 90: return "S"
#     if total >= 75: return "A"
#     if total >= 60: return "B"
#     if total >= 45: return "C"
#     return "D"


# async def _call_openai(system: str, user: str, model: str = "gpt-4o") -> dict:
#     """Call OpenAI and parse JSON response."""
#     response = await client.chat.completions.create(
#         model=model,
#         temperature=0.3,
#         response_format={"type": "json_object"},
#         messages=[
#             {"role": "system", "content": system},
#             {"role": "user",   "content": user},
#         ],
#     )
#     return json.loads(response.choices[0].message.content)


# # ─────────────────────────────────────────────
# # STEP 1 — Enhance CV text fields
# # ─────────────────────────────────────────────

# ENHANCE_SYSTEM = """
# You are a senior career coach and professional CV writer.
# Enhance the given fields from a candidate's MasterCV to be more impactful,
# specific, and achievement-oriented while staying 100% truthful to the
# original content. Do not invent metrics or facts.

# Return ONLY valid JSON matching this schema (no extra keys):
# {
#   "bio": "string",
#   "resumeSummary": "string",
#   "carrierGoal": "string",
#   "strength": ["string"],
#   "workExperiences": [
#     {
#       "company": "string",
#       "position": "string",
#       "duration": "string",
#       "responsibilities": "string",
#       "projects": ["string"]
#     }
#   ],
#   "challenges": [
#     {
#       "challengeName": "string",
#       "situation": "string",
#       "task": "string",
#       "action": "string",
#       "result": "string"
#     }
#   ]
# }

# Rules:
# - bio: 2-3 punchy sentences. Lead with seniority + years + domain impact.
# - resumeSummary: 2-3 sentences. Highlight tech stack, scale, and key achievement.
# - carrierGoal: 1-2 sentences. Connect current expertise to ambition concretely.
# - strength: each item should be 1 sentence with a concrete example from the CV.
# - workExperiences[].responsibilities: rewrite with active verbs, scale, and outcomes.
# - challenges: map challangeName→challengeName, impact→task, achievement→action,
#   leadershipMoment→result. Expand each to a full STAR sentence (2-3 sentences each).
# """


# async def enhance_cv_fields(cv: MasterCVData) -> dict:
#     user_prompt = f"""
# Role: {cv.currentRole}
# Domain: {cv.domain} / {cv.subDomain}
# Career stage: {cv.careerStage}
# Total experience: {cv.totalExperienceYear} years

# bio: {cv.bio}
# resumeSummary: {cv.resumeSummary}
# carrierGoal: {cv.carrierGoal}
# strength: {json.dumps(cv.strength)}
# workExperiences: {json.dumps([w.model_dump() for w in (cv.workExperiences or [])])}
# challenges: {json.dumps([c.model_dump() for c in (cv.challenges or [])])}
# """
#     return await _call_openai(ENHANCE_SYSTEM, user_prompt)


# # ─────────────────────────────────────────────
# # STEP 2 — Extract & score skills from challenges
# # ─────────────────────────────────────────────

# SKILL_EXTRACT_SYSTEM = """
# You are a technical skill extraction engine.
# Given challenges from a candidate's CV and their role/domain context,
# extract all implied or explicit technical and soft skills.

# For each skill calculate:
# - roleAlignment (0-100): how relevant is this skill to their currentRole and domain?
# - experienceWeight (0-100): based on the context, how experienced do they seem?
# - score (0-100): weighted average — (roleAlignment * 0.6) + (experienceWeight * 0.4)

# Return ONLY valid JSON:
# {
#   "skills": [
#     {
#       "skillName": "string",
#       "skillCategory": "string",
#       "proficiencyLevel": "Beginner | Intermediate | Advanced | Expert",
#       "yearOfExperience": 0,
#       "source": "CHALLENGE_EXTRACTED",
#       "score": 0,
#       "scoreBreakdown": {
#         "roleAlignment": 0,
#         "experienceWeight": 0
#       }
#     }
#   ]
# }

# Rules:
# - Extract concrete technical skills only (no generic words like "communication").
# - Avoid duplicating skills that would obviously already be in their base skill set.
# - yearOfExperience: estimate from context clues; default to 1 if unclear.
# - Max 10 skills per call.
# """


# async def extract_skills_from_challenges(cv: MasterCVData) -> list[dict]:
#     if not cv.challenges:
#         return []

#     user_prompt = f"""
# currentRole: {cv.currentRole}
# domain: {cv.domain}
# subDomain: {cv.subDomain}
# careerStage: {cv.careerStage}

# Challenges:
# {json.dumps([c.model_dump() for c in cv.challenges])}
# """
#     result = await _call_openai(SKILL_EXTRACT_SYSTEM, user_prompt)
#     return result.get("skills", [])


# # ─────────────────────────────────────────────
# # STEP 3 — Score existing skills from MongoDB
# # ─────────────────────────────────────────────

# SKILL_SCORE_SYSTEM = """
# You are a technical skill evaluator.
# Given a list of skills the candidate already has and their role/domain context,
# score each skill.

# For each skill calculate:
# - roleAlignment (0-100): relevance to currentRole and domain
# - experienceWeight (0-100): inferred from yearsOfExperience vs expected for the role
# - score (0-100): (roleAlignment * 0.6) + (experienceWeight * 0.4)
# - proficiencyLevel: infer from score — <40 Beginner, 40-65 Intermediate, 66-80 Advanced, >80 Expert

# Return ONLY valid JSON:
# {
#   "skills": [
#     {
#       "skillName": "string",
#       "skillCategory": "string",
#       "proficiencyLevel": "string",
#       "yearOfExperience": 0,
#       "source": "MASTER_CV",
#       "score": 0,
#       "scoreBreakdown": {
#         "roleAlignment": 0,
#         "experienceWeight": 0
#       }
#     }
#   ]
# }
# """


# async def score_existing_skills(
#     raw_skills: list,
#     cv: MasterCVData,
# ) -> list[dict]:
#     if not raw_skills:
#         return []

#     user_prompt = f"""
# currentRole: {cv.currentRole}
# domain: {cv.domain}
# subDomain: {cv.subDomain}
# totalExperienceYear: {cv.totalExperienceYear}

# Skills to score:
# {json.dumps(raw_skills)}
# """
#     result = await _call_openai(SKILL_SCORE_SYSTEM, user_prompt)
#     return result.get("skills", [])


# # ─────────────────────────────────────────────
# # STEP 4 — Identify skill gaps
# # ─────────────────────────────────────────────

# SKILL_GAP_SYSTEM = """
# You are an expert technical career advisor.
# Given a candidate's current skills, role, domain, and a reference skill collection
# for that domain/role, identify skills the candidate is MISSING that are important
# for their career progression.

# For each gap:
# - roleAlignment (0-100): how relevant is this skill to their role/domain
# - demandWeight (0-100): how in-demand is this skill in the industry right now
# - score (0-100): (roleAlignment * 0.5) + (demandWeight * 0.5)
# - demandLevel: High (score >= 70), Medium (40-69), Low (<40)
# - sourceCollection: "ROLE_SKILLS" if it comes from the provided skill list,
#   "DOMAIN_INFERRED" if identified by you from domain knowledge

# Return ONLY valid JSON:
# {
#   "skill_gaps": [
#     {
#       "skillName": "string",
#       "skillCategory": "string",
#       "proficiencyLevel": "Beginner | Intermediate | Advanced",
#       "demandLevel": "High | Medium | Low",
#       "score": 0,
#       "scoreBreakdown": {
#         "roleAlignment": 0,
#         "demandWeight": 0
#       },
#       "gapReason": "string (2 sentences: why this is a gap for this role)",
#       "suggestion": "string (actionable 1-2 sentence learning path)",
#       "sourceCollection": "ROLE_SKILLS | DOMAIN_INFERRED"
#     }
#   ]
# }

# Rules:
# - Only surface MISSING skills — do not list skills the candidate already has.
# - Limit to the 6 most impactful gaps.
# - Sort by score descending (highest impact gap first).
# """


# async def identify_skill_gaps(
#     current_skills: list[dict],
#     role_skill_collection: list,
#     cv: MasterCVData,
# ) -> list[dict]:
#     user_prompt = f"""
# currentRole: {cv.currentRole}
# domain: {cv.domain}
# subDomain: {cv.subDomain}
# careerStage: {cv.careerStage}
# totalExperienceYear: {cv.totalExperienceYear}

# Candidate's current skills:
# {json.dumps([s.get("skillName") for s in current_skills])}

# Role/domain reference skill collection (from frontend):
# {json.dumps(role_skill_collection)}
# """
#     result = await _call_openai(SKILL_GAP_SYSTEM, user_prompt)
#     return result.get("skill_gaps", [])


# # ─────────────────────────────────────────────
# # STEP 5 — Calculate AI score
# # ─────────────────────────────────────────────

# AI_SCORE_SYSTEM = """
# You are a CV quality evaluator.
# Given a candidate's enhanced MasterCV data, score their profile on 5 dimensions.
# Each dimension is 0-100. Return the total as a weighted average.

# Weights:
#   profileCompleteness : 15%  — % of important fields that are non-null and detailed
#   skillRelevance      : 30%  — avg skill score relative to role/domain
#   experienceClarity   : 25%  — specificity and impact of work experience descriptions
#   careerNarrative     : 20%  — coherence of bio + resumeSummary + carrierGoal + challenges
#   skillGapSeverity    : 10%  — INVERSE score: more/worse gaps = lower score

# Grading: S=90+, A=75-89, B=60-74, C=45-59, D=<45

# Return ONLY valid JSON:
# {
#   "breakdown": {
#     "profileCompleteness": 0,
#     "skillRelevance": 0,
#     "experienceClarity": 0,
#     "careerNarrative": 0,
#     "skillGapSeverity": 0
#   },
#   "summary": "string (2-3 sentence plain-English summary of the profile's strengths and main gaps)"
# }
# """


# async def calculate_ai_score(
#     cv: MasterCVData,
#     enhanced: dict,
#     skills: list[dict],
#     skill_gaps: list[dict],
# ) -> AIScore:
#     user_prompt = f"""
# currentRole: {cv.currentRole}
# domain: {cv.domain}
# subDomain: {cv.subDomain}
# careerStage: {cv.careerStage}

# Enhanced bio: {enhanced.get('bio', '')}
# Enhanced resumeSummary: {enhanced.get('resumeSummary', '')}
# Enhanced carrierGoal: {enhanced.get('carrierGoal', '')}
# Strengths count: {len(enhanced.get('strength', []))}
# Work experiences count: {len(enhanced.get('workExperiences', []))}

# Skills (count {len(skills)}), avg score: {
#     round(sum(s.get('score', 0) for s in skills) / len(skills)) if skills else 0
# }
# Skill gaps count: {len(skill_gaps)}
# High-demand gaps: {sum(1 for g in skill_gaps if g.get('demandLevel') == 'High')}
# """
#     result = await _call_openai(AI_SCORE_SYSTEM, user_prompt)
#     breakdown = result.get("breakdown", {})

#     total = round(
#         breakdown.get("profileCompleteness", 0) * 0.15
#         + breakdown.get("skillRelevance", 0) * 0.30
#         + breakdown.get("experienceClarity", 0) * 0.25
#         + breakdown.get("careerNarrative", 0) * 0.20
#         + breakdown.get("skillGapSeverity", 0) * 0.10
#     )

#     return AIScore(
#         total=total,
#         grade=_grade(total),
#         summary=result.get("summary", ""),
#         breakdown=AIScoreBreakdown(**breakdown),
#     )


# # ─────────────────────────────────────────────
# # STEP 6 — Build ai_impacts (original vs enhanced diff)
# # ─────────────────────────────────────────────

# def build_ai_impacts(cv: MasterCVData, enhanced: dict) -> list[AIImpact]:
#     impacts: list[AIImpact] = []

#     def _add(field: str, original: str, enhanced_val: str):
#         if original and enhanced_val and original.strip() != enhanced_val.strip():
#             impacts.append(AIImpact(
#                 field=field,
#                 original=original,
#                 enhanced=enhanced_val,
#             ))

#     _add("bio", cv.bio or "", enhanced.get("bio", ""))
#     _add("resumeSummary", cv.resumeSummary or "", enhanced.get("resumeSummary", ""))
#     _add("carrierGoal", cv.carrierGoal or "", enhanced.get("carrierGoal", ""))

#     orig_strengths = cv.strength or []
#     new_strengths  = enhanced.get("strength", [])
#     for i, (orig, enh) in enumerate(zip(orig_strengths, new_strengths)):
#         _add(f"strength[{i}]", orig, enh)

#     orig_exps = cv.workExperiences or []
#     new_exps  = enhanced.get("workExperiences", [])
#     for i, (orig, enh) in enumerate(zip(orig_exps, new_exps)):
#         _add(
#             f"workExperiences[{i}].responsibilities",
#             orig.responsibilities or "",
#             enh.get("responsibilities", ""),
#         )

#     return impacts


# # ─────────────────────────────────────────────
# # MAIN SERVICE ENTRY POINT
# # ─────────────────────────────────────────────

# async def enhance_master_cv(
#     cv: MasterCVData,
#     role_skill_collection: list,
# ) -> EnhancedMasterCVData:
#     """
#     Orchestrates all enhancement steps and returns the full EnhancedMasterCVData.

#     Args:
#         cv                    : parsed MasterCVData from the frontend request
#         role_skill_collection : skill list for the candidate's role/domain,
#                                 received from the frontend alongside the masterCV
#     """

#     # 1. Enhance text fields + rewrite challenges as STAR
#     enhanced = await enhance_cv_fields(cv)

#     # 2. Fetch existing user skills from MongoDB (Skill collection)
#     raw_mongo_skills: list = []
#     try:
#         skill_doc = await db.resume_skill_collection.find_one(
#             {"userId": cv.userId},
#             {"_id": 0, "userId": 0},
#         )
#         if skill_doc:
#             raw_mongo_skills = skill_doc.get("skills", [])
#     except Exception:
#         pass  # non-fatal — proceed without DB skills

#     # 3. Score existing skills from MongoDB
#     scored_existing = await score_existing_skills(raw_mongo_skills, cv)

#     # 4. Extract skills from challenges
#     challenge_skills = await extract_skills_from_challenges(cv)

#     # 5. Merge — deduplicate by skillName (challenge skills supplement, not replace)
#     existing_names = {s.get("skillName", "").lower() for s in scored_existing}
#     unique_challenge_skills = [
#         s for s in challenge_skills
#         if s.get("skillName", "").lower() not in existing_names
#     ]
#     all_skills = scored_existing + unique_challenge_skills

#     # 6. Identify skill gaps
#     skill_gaps_raw = await identify_skill_gaps(all_skills, role_skill_collection, cv)

#     # 7. AI score
#     ai_score = await calculate_ai_score(cv, enhanced, all_skills, skill_gaps_raw)

#     # 8. Build ai_impacts
#     ai_impacts = build_ai_impacts(cv, enhanced)

#     # 9. Build enhanced_challenges (STAR format)
#     enhanced_challenges = [
#         EnhancedChallenge(
#             challengeName=ch.get("challengeName", ""),
#             situation=ch.get("situation", ""),
#             task=ch.get("task", ""),
#             action=ch.get("action", ""),
#             result=ch.get("result", ""),
#         )
#         for ch in enhanced.get("challenges", [])
#     ]

#     # 10. Build enhanced_master_cv (merge original passthrough + enhanced fields)
#     enhanced_cv = EnhancedMasterCV(
#         fullName=cv.fullName,
#         email=cv.email,
#         phoneNumber=cv.phoneNumber,
#         location=cv.location,
#         linkedinUrl=cv.linkedinUrl,
#         portfolioUrl=cv.portfolioUrl,
#         resumeLink=cv.resumeLink,
#         currentRole=cv.currentRole,
#         careerStage=cv.careerStage,
#         totalExperienceYear=int(cv.totalExperienceYear) if cv.totalExperienceYear else None,
#         domain=cv.domain,
#         subDomain=cv.subDomain,
#         industry=cv.industry,
#         bio=enhanced.get("bio", cv.bio),
#         resumeSummary=enhanced.get("resumeSummary", cv.resumeSummary),
#         carrierGoal=enhanced.get("carrierGoal", cv.carrierGoal),
#         strength=enhanced.get("strength", cv.strength),
#         workExperiences=[
#             WorkExperienceOut(**w) for w in enhanced.get("workExperiences", [])
#         ],
#         educationsAndCertifications=cv.educationsAndCertifications,
#         accomplishments=cv.accomplishments,
#         appliedGigs=cv.appliedGigs,
#         savedGigs=cv.savedGigs,
#         mentorProfile=cv.mentorProfile,
#         resumeSections=cv.resumeSections,
#         generatedCvJson=cv.generatedCvJson,
#         lastGeneratedAt=cv.lastGeneratedAt,
#         refletions=cv.refletions,
#     )

#     # 11. Assemble final response data
#     return EnhancedMasterCVData(
#         userId=cv.userId,
#         generatedAt=datetime.now(timezone.utc).isoformat(),
#         ai_score=ai_score,
#         skills=[SkillOut(**s) for s in all_skills],
#         skill_gaps=[SkillGapOut(**g) for g in skill_gaps_raw],
#         ai_impacts=ai_impacts,
#         enhanced_challenges=enhanced_challenges,
#         enhanced_master_cv=enhanced_cv,
#     )
# working end