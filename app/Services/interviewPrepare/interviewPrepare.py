import json
from openai import AsyncOpenAI
from bson import ObjectId
from app.DB.mongodb.mongodb import MongoDB
from app.Services.interviewPrepare.interviewPrepare_schema import (
    InterviewQuestionsRequest,
    InterviewQuestionsData,
    ScoreRequest,
    ScoreData,
    Question,
    QuestionType,
    ScoreBreakdown,
)

client = AsyncOpenAI()
db     = MongoDB()


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

async def _fetch_enhanced_cv(user_id: str) -> dict:
    doc = await db.db["enhancedMasterCv"].find_one(
        {"userId": ObjectId(user_id)},
        {"_id": 0},
    )
    if not doc:
        raise ValueError(f"No enhancedMasterCV found for userId: {user_id}")
    return doc


def _extract_cv_context(enhanced_cv: dict) -> dict:
    """Flatten the most useful fields into a single context dict."""
    ecv        = enhanced_cv.get("enhanced_master_cv", enhanced_cv)
    skills     = enhanced_cv.get("skills", [])
    challenges = enhanced_cv.get("enhanced_challenges", [])

    work_exps = ecv.get("workExperiences", ecv.get("workExperiences", []))

    return {
        "fullName":       ecv.get("fullName"),
        "currentRole":    ecv.get("currentRole"),
        "domain":         ecv.get("domain"),
        "subDomain":      ecv.get("subDomain"),
        "careerStage":    ecv.get("careerStage"),
        "industry":       ecv.get("industry"),
        "totalExp":       ecv.get("totalExperienceYear"),
        "bio":            ecv.get("bio"),
        "resumeSummary":  ecv.get("resumeSummary"),
        "carrierGoal":    ecv.get("carrierGoal"),
        "strength":       ecv.get("strength", []),
        "workExperiences": [
            {
                "company":          w.get("company"),
                "position":         w.get("position"),
                "duration":         w.get("duration"),
                "responsibilities": w.get("responsibilities"),
                "projects":         w.get("projects", []),
            }
            for w in (work_exps or [])[:3]   # top 3 jobs
        ],
        "topSkills": [
            s.get("skillName") for s in
            sorted(skills, key=lambda x: x.get("score", 0), reverse=True)[:10]
        ],
        "challenges": [
            {
                "challengeName": c.get("challengeName"),
                "situation":     c.get("situation"),
                "action":        c.get("action"),
                "result":        c.get("result"),
            }
            for c in (challenges or [])
        ],
    }


# ─────────────────────────────────────────────
# QUESTION GENERATION
# ─────────────────────────────────────────────

QUESTION_GEN_SYSTEM = """
You are an expert technical interviewer and career coach.
Your job is to generate 15 personalised, realistic interview questions
tailored to the candidate's actual CV data.

QUESTION BREAKDOWN (strictly follow this count):
  1  × Introduction          — based on name, bio, resumeSummary, careerGoal, strength
  2  × Behavioral            — based on challenges; hint must mention STAR format
  2  × Situational           — based on workExperiences; "what would you do if..."
  1  × Communication         — ask candidate to explain a complex thing they built
  1  × Leadership & Teamwork — based on workExperiences or challenges
  1  × Motivation & Career Goal — based on carrierGoal, domain, careerStage
  2  × Critical Thinking & Problem Solving — domain/role-aware edge cases
  5  × Domain Specific       — technical questions based on domain, subDomain, topSkills

RULES:
- Every question must reference something REAL from the CV — don't generate generic questions.
- expectedAnswerTraits: 3-5 bullet strings describing what a great answer includes.
- hint: 1-2 sentences guiding the candidate on how to approach the answer.
- Behavioral hints MUST mention the STAR format (Situation, Task, Action, Result).
- Domain Specific questions should progressively increase in depth (Q11 easy → Q15 hard).
- questionId: sequential 1-15.

Return ONLY valid JSON:
{
  "questions": [
    {
      "questionId": 1,
      "questionType": "Introduction | Behavioral | Situational | Communication | Leadership & Teamwork | Motivation & Career Goal | Critical Thinking & Problem Solving | Domain Specific",
      "question": "string",
      "expectedAnswerTraits": ["string"],
      "hint": "string"
    }
  ]
}
"""


async def generate_interview_questions(
    req: InterviewQuestionsRequest,
) -> InterviewQuestionsData:
    # 1. Fetch CV
    enhanced_cv = await _fetch_enhanced_cv(req.userId)
    ctx         = _extract_cv_context(enhanced_cv)

    # 2. Build user prompt
    user_prompt = f"""
Generate 15 interview questions for this candidate:

{json.dumps(ctx, indent=2)}
""".strip()

    # 3. Call OpenAI
    response = await client.chat.completions.create(
        model="gpt-4o",
        temperature=0.5,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": QUESTION_GEN_SYSTEM},
            {"role": "user",   "content": user_prompt},
        ],
    )

    raw       = json.loads(response.choices[0].message.content)
    questions = [Question(**q) for q in raw.get("questions", [])]

    return InterviewQuestionsData(
        userId=req.userId,
        candidateName=ctx.get("fullName"),
        role=ctx.get("currentRole"),
        domain=ctx.get("domain"),
        totalQuestions=len(questions),
        questions=questions,
    )


# ─────────────────────────────────────────────
# DYNAMIC SCORING CRITERIA PER QUESTION TYPE
# ─────────────────────────────────────────────

SCORING_CRITERIA = {
    QuestionType.BEHAVIORAL: """
Evaluate using STAR format:
- clarity (0-10):    Is the answer clear and easy to follow?
- relevance (0-10):  Does it directly answer the question using a real experience?
- structure (0-10):  Does it follow Situation → Task → Action → Result structure?
- confidence (0-10): Does the candidate show ownership, decisiveness, and self-awareness?
Key signals: ownership language ("I led", "I decided"), measurable impact, emotional intelligence.
""",

    QuestionType.DOMAIN_SPECIFIC: """
Evaluate as a technical interviewer:
- clarity (0-10):    Is the explanation clear and well-articulated?
- relevance (0-10):  Is the answer technically correct and on-topic?
- structure (0-10):  Is it logically organised (concept → reasoning → example)?
- confidence (0-10): Does the candidate show depth, correct terminology, and practical understanding?
Key signals: correct technical terms, trade-off awareness, real-world application of concepts.
""",

    QuestionType.COMMUNICATION: """
Evaluate explanation ability:
- clarity (0-10):    Could a non-technical person understand this?
- relevance (0-10):  Does it explain the specific thing asked, not something tangential?
- structure (0-10):  Is there a logical flow (problem → approach → outcome)?
- confidence (0-10): Is the tone assured and the explanation confident?
Key signals: use of analogy, avoidance of unnecessary jargon, concise delivery.
""",

    QuestionType.SITUATIONAL: """
Evaluate situational judgment:
- clarity (0-10):    Is the response concrete and actionable?
- relevance (0-10):  Is the approach relevant to the scenario described?
- structure (0-10):  Does it walk through a logical decision-making process?
- confidence (0-10): Does the candidate show decisiveness and role-appropriate thinking?
Key signals: identification of risks, stakeholder awareness, fallback plans.
""",

    QuestionType.LEADERSHIP_TEAMWORK: """
Evaluate leadership and collaboration:
- clarity (0-10):    Is the example clearly described?
- relevance (0-10):  Does it demonstrate actual leadership or teamwork, not just participation?
- structure (0-10):  Is there a clear context, role, action, and outcome?
- confidence (0-10): Does the candidate show initiative and accountability?
Key signals: evidence of influence without authority, conflict resolution, team outcomes.
""",

    # Default criteria for all other types
    "_default": """
Evaluate the response holistically:
- clarity (0-10):    Is the answer clear, focused, and easy to understand?
- relevance (0-10):  Does it directly address the question asked?
- structure (0-10):  Is it logically organised with a clear flow?
- confidence (0-10): Is the tone assured and the content well-grounded?
""",
}


def _get_scoring_criteria(question_type: QuestionType) -> str:
    return SCORING_CRITERIA.get(question_type, SCORING_CRITERIA["_default"])


# ─────────────────────────────────────────────
# ANSWER SCORING
# ─────────────────────────────────────────────

SCORE_SYSTEM_TEMPLATE = """
You are an expert interview evaluator.
Score the candidate's answer to an interview question.

QUESTION TYPE: {question_type}

SCORING CRITERIA:
{criteria}

SCORING RULES:
- Score each dimension from 0 to 10 (integer only).
- overallScore = round((clarity + relevance + structure + confidence) / 40 * 100)
- feedback: 2-3 sentences of honest, specific qualitative feedback.
- improvementTip: 1 short, actionable tip the candidate can apply immediately.
- If you need CV context to judge relevance, it is provided below.
- Be strict but fair — reserve 9-10 for exceptional answers.

Return ONLY valid JSON:
{{
  "scoreBreakdown": {{
    "clarity":    0,
    "relevance":  0,
    "structure":  0,
    "confidence": 0
  }},
  "overallScore":   0,
  "feedback":       "string",
  "improvementTip": "string"
}}
"""

# Question types that benefit from CV context when scoring
CV_DEPENDENT_TYPES = {
    QuestionType.BEHAVIORAL,
    QuestionType.SITUATIONAL,
    QuestionType.DOMAIN_SPECIFIC,
    QuestionType.LEADERSHIP_TEAMWORK,
    QuestionType.COMMUNICATION,
}


async def score_answer(req: ScoreRequest) -> ScoreData:
    # 1. Conditionally fetch CV based on question type
    cv_context_text = ""
    if req.questionType in CV_DEPENDENT_TYPES:
        try:
            enhanced_cv     = await _fetch_enhanced_cv(req.userId)
            ctx             = _extract_cv_context(enhanced_cv)
            cv_context_text = f"\nCANDIDATE CV CONTEXT (use to judge relevance):\n{json.dumps(ctx, indent=2)}"
        except ValueError:
            pass   # CV not found — score without context, non-fatal

    # 2. Build system prompt with dynamic criteria
    system_prompt = SCORE_SYSTEM_TEMPLATE.format(
        question_type=req.questionType.value,
        criteria=_get_scoring_criteria(req.questionType),
    )

    # 3. Build user prompt
    user_prompt = f"""
QUESTION: {req.question}

CANDIDATE'S ANSWER: {req.answer}
{cv_context_text}
""".strip()

    # 4. Call OpenAI
    response = await client.chat.completions.create(
        model="gpt-4o",
        temperature=0.2,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ],
    )

    raw = json.loads(response.choices[0].message.content)
    bd  = raw.get("scoreBreakdown", {})

    # Recompute overallScore server-side so it's always consistent
    clarity    = int(bd.get("clarity",    0))
    relevance  = int(bd.get("relevance",  0))
    structure  = int(bd.get("structure",  0))
    confidence = int(bd.get("confidence", 0))
    overall    = round((clarity + relevance + structure + confidence) / 40 * 100)

    return ScoreData(
        questionType=req.questionType,
        question=req.question,
        scoreBreakdown=ScoreBreakdown(
            clarity=clarity,
            relevance=relevance,
            structure=structure,
            confidence=confidence,
        ),
        overallScore=overall,
        feedback=raw.get("feedback", ""),
        improvementTip=raw.get("improvementTip", ""),
    )