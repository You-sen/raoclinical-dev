import json
from openai import AsyncOpenAI
from bson import ObjectId
from app.DB.mongodb.mongodb import MongoDB
from app.Services.coverLetter.coverLetter_schema import (
    CoverLetterRequest,
    CoverLetterData,
)

client = AsyncOpenAI()
db     = MongoDB()


# ─────────────────────────────────────────────
# TEMPLATE INSTRUCTIONS
# ─────────────────────────────────────────────

TEMPLATE_GUIDE = {
    "Modern": (
        "Write in a warm, confident, story-led style. "
        "Open with a compelling personal hook or narrative moment. "
        "Use natural flowing paragraphs — avoid stiff corporate language. "
        "Around 300-400 words."
    ),
    "Classic": (
        "Write in a formal, structured style. "
        "Follow a clear 4-paragraph structure: introduction, relevant experience, "
        "skills alignment, and closing call to action. "
        "Professional and polished. Around 300-350 words."
    ),
    "Concise": (
        "Write a short, punchy cover letter of no more than 200 words. "
        "Every sentence must earn its place. Lead with your strongest point. "
        "No filler phrases. End with a direct CTA."
    ),
}

TONE_GUIDE = {
    "Confident":         "Assert your value directly. Use strong active verbs.",
    "Enthusiastic":      "Show genuine excitement about the company and role.",
    "Formal":            "Maintain professional distance. No contractions.",
    "Friendly":          "Be warm and personable without being casual.",
    "Story-led":         "Anchor key points in brief real stories or moments.",
    "Conversational":    "Write as you'd speak in a professional conversation.",
    "Bold & Confident":  "Make bold claims backed by evidence. Stand out.",
    "Results-Focused":   "Lead every point with outcomes and numbers where possible.",
    "Analytical":        "Emphasise logical reasoning, data, and structured thinking.",
    "Warm & Approachable":"Create a sense of genuine connection and openness.",
    "Concise & Direct":  "Cut to the point. Short sentences. No padding.",
    "Professional":      "Polished, measured, and credible throughout.",
}


# ─────────────────────────────────────────────
# SYSTEM PROMPT BUILDER
# ─────────────────────────────────────────────

def _build_system_prompt(template: str, tone: str) -> str:
    return f"""
You are an expert cover letter writer who crafts highly personalised,
compelling cover letters that get interviews.

TEMPLATE STYLE — {template}:
{TEMPLATE_GUIDE[template]}

TONE — {tone}:
{TONE_GUIDE[tone]}

RULES:
- Never fabricate facts, metrics, or experiences not present in the CV data.
- Directly connect the candidate's real experience to the target role.
- Do not use generic filler phrases like "I am writing to apply for..."
- Do not include placeholders like [Company Name] — use the actual details provided.
- Do not add a subject line or email headers — return the letter body only.
- Start directly with the opening paragraph (no "Dear Hiring Manager" unless
  the template is Classic, in which case include a formal salutation).
- End with a confident closing paragraph and sign-off using the candidate's name.

Return ONLY the cover letter text. No JSON, no commentary, no extra formatting.
""".strip()


# ─────────────────────────────────────────────
# USER PROMPT BUILDER
# ─────────────────────────────────────────────

def _build_user_prompt(req: CoverLetterRequest, enhanced_cv: dict) -> str:
    # Pull the most useful fields from enhancedMasterCV
    ecv = enhanced_cv.get("enhanced_master_cv", enhanced_cv)  # support both shapes

    full_name      = ecv.get("fullName", "")
    current_role   = ecv.get("currentRole", "")
    domain         = ecv.get("domain", "")
    sub_domain     = ecv.get("subDomain", "")
    bio            = ecv.get("bio", "")
    resume_summary = ecv.get("resumeSummary", "")
    career_goal    = ecv.get("carrierGoal", "")
    strengths      = ecv.get("strength", [])
    total_exp      = ecv.get("totalExperienceYear", "")

    # Work experiences — top 2
    work_exps = ecv.get("workExperiences", ecv.get("workExperiences", []))[:2]
    work_text = "\n".join(
        f"- {w.get('position','?')} at {w.get('company','?')} ({w.get('duration','?')}): "
        f"{w.get('responsibilities','')}"
        for w in work_exps
    )

    # Skills — top 8 by score
    skills_raw = enhanced_cv.get("skills", [])
    top_skills = sorted(skills_raw, key=lambda s: s.get("score", 0), reverse=True)[:8]
    skills_text = ", ".join(s.get("skillName", "") for s in top_skills) or "Not available"

    # Enhanced challenges (STAR) — top 2
    challenges = enhanced_cv.get("enhanced_challenges", [])[:2]
    challenge_text = "\n".join(
        f"- {c.get('challengeName','')}: {c.get('action','')} → {c.get('result','')}"
        for c in challenges
    ) or "Not available"

    return f"""
CANDIDATE PROFILE:
  Name              : {full_name}
  Current Role      : {current_role}
  Domain            : {domain} / {sub_domain}
  Total Experience  : {total_exp} years
  Bio               : {bio}
  Resume Summary    : {resume_summary}
  Career Goal       : {career_goal}
  Key Strengths     : {', '.join(strengths) if strengths else 'Not available'}
  Top Skills        : {skills_text}

WORK EXPERIENCE HIGHLIGHTS:
{work_text or 'Not available'}

KEY ACHIEVEMENTS (STAR format):
{challenge_text}

TARGET JOB:
  Role              : {req.role}
  Job Details       : {req.jobDetails}
  Job Description   : {req.jobDescription or 'Not provided'}

Now write the cover letter.
""".strip()


# ─────────────────────────────────────────────
# MAIN SERVICE
# ─────────────────────────────────────────────

async def generate_cover_letter(req: CoverLetterRequest) -> CoverLetterData:
    # 1. Fetch enhancedMasterCV from MongoDB by userId
    enhanced_cv = await db.db["enhancedMasterCv"].find_one(
        {"userId": ObjectId(req.userId)},
        {"_id": 0},
    )

    if not enhanced_cv:
        raise ValueError(f"No enhancedMasterCV found for userId: {req.userId}")

    # 2. Build prompts
    system_prompt = _build_system_prompt(req.template.value, req.tone.value)
    user_prompt   = _build_user_prompt(req, enhanced_cv)

    # 3. Call OpenAI
    response = await client.chat.completions.create(
        model="gpt-4o",
        temperature=0.7,           # slight creativity for natural language
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ],
    )

    cover_letter_text = response.choices[0].message.content.strip()

    # # 4. Save to CoverLetter collection
    # await db.cover_letter_collection.insert_one({
    #     "userId":         ObjectId(req.userId),
    #     "coverLetter":    cover_letter_text,
    #     "template":       req.template.value,
    #     "tone":           req.tone.value,
    #     "role":           req.role,
    #     "jobDetails":     req.jobDetails,
    #     "jobDescription": req.jobDescription,
    #     "wordCount":      len(cover_letter_text.split()),
    # })

    return CoverLetterData(
        coverLetter=cover_letter_text,
        template=req.template,
        tone=req.tone,
        role=req.role,
        jobDetails=req.jobDetails,
        wordCount=len(cover_letter_text.split()),
    )