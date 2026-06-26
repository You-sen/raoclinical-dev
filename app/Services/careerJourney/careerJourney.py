import json
import asyncio
from bson import ObjectId
from openai import AsyncOpenAI
from datetime import datetime
from app.DB.mongodb.mongodb import MongoDB
from app.Services.careerJourney.careerJourney_schema import (
    ProfileScoreRequest,
    ProfileScoreResponse,
    GrowthTimelineResponse,
    FutureGrowthPathResponse,
    RoadmapResponse,
    OpportunitiesResponse
)

client = AsyncOpenAI()
db = MongoDB()

async def update_profile_score(req: ProfileScoreRequest) -> ProfileScoreResponse:
    # 1. Fetch enhancedMasterCV
    user_id_obj = ObjectId(req.userId)
    enhanced_cv = await db.db["enhancedMasterCv"].find_one({"userId": user_id_obj}, {"_id": 0})
    if not enhanced_cv:
        enhanced_cv = {}
    
    ecv = enhanced_cv.get("enhanced_master_cv", enhanced_cv)

    # 2. Fetch existing profileScore
    profile_score = await db.profile_score_collection.find_one({"userId": user_id_obj})
    if not profile_score:
        profile_score = {
            "userId": user_id_obj,
            "AIScore": [],
            "ConfidenceScore": [],
            "TopTraits": [],
            "CareerMomentum": {},
            "ChallengesConsistency": {},
            "GrowthDirection": {},
            "JobReadiness": {},
            "OverallAssessment": ""
        }

    # Append new scores if provided
    if req.AIScore:
        profile_score["AIScore"].append(req.AIScore.dict())
    if req.ConfidenceScore:
        profile_score["ConfidenceScore"].append(req.ConfidenceScore.dict())

    # Ensure uniqueness or replace logic for Top Traits
    strengths = ecv.get("strength", [])
    challenges = enhanced_cv.get("challenges", ecv.get("challenges", enhanced_cv.get("enhanced_challenges", [])))
    career_goal = ecv.get("carrierGoal", "")
    current_role = ecv.get("currentRole", "")

    # Combine data for AI prompt
    profile_data_str = json.dumps({
        "strengths": strengths,
        "challenges": challenges,
        "career_goal": career_goal,
        "current_role": current_role,
        "existing_traits": profile_score.get("TopTraits", []),
        "recent_confidence": req.ConfidenceScore.model_dump(mode='json') if req.ConfidenceScore else None
    })

    system_prompt = """
    You are an AI Career Journey analyst. Given the candidate's profile data, compute the following metrics:
    - Top Traits: Maximum 3 traits (1 or 2 words each). If they already exist, replace with newer relevant ones.
    - Career Momentum: Score based on challenges and skills towards career goal. Format: {"percentage": int, "rank": string} (ranks: 90+ Excellent, 80+ Strong, 60+ Good).
    - Challenges Consistency: Based on challenges quality. Format: {"Percentage": int, "Rank": string}.
    - Growth Direction: Based on challenges vs career goal. Format: {"Rank": string} (Excellent, Strong, Moderate).
    - Job Readiness: Based on current confidence score and profile. Format: {"Percentage": int, "Rank": string}.
    - Overall Assessment: A 1-2 sentence overall assessment of the profile based on the numbers calculated.

    Output strictly in valid JSON format matching this structure:
    {
        "TopTraits": ["Trait1", "Trait2"],
        "CareerMomentum": {"percentage": 85, "rank": "Strong"},
        "ChallengesConsistency": {"Percentage": 80, "Rank": "Strong"},
        "GrowthDirection": {"Rank": "Excellent"},
        "JobReadiness": {"Percentage": 75, "Rank": "Good"},
        "OverallAssessment": "Your overall assessment here."
    }
    """

    response = await client.chat.completions.create(
        model="gpt-4o",
        temperature=0.3,
        response_format={ "type": "json_object" },
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Profile Data: {profile_data_str}"}
        ]
    )

    ai_result = json.loads(response.choices[0].message.content)
    
    # Update profile score document
    profile_score["TopTraits"] = ai_result.get("TopTraits", [])
    profile_score["CareerMomentum"] = ai_result.get("CareerMomentum", {})
    profile_score["ChallengesConsistency"] = ai_result.get("ChallengesConsistency", {})
    profile_score["GrowthDirection"] = ai_result.get("GrowthDirection", {})
    profile_score["JobReadiness"] = ai_result.get("JobReadiness", {})
    profile_score["OverallAssessment"] = ai_result.get("OverallAssessment", "")

    await db.profile_score_collection.update_one(
        {"userId": user_id_obj},
        {"$set": profile_score},
        upsert=True
    )

    profile_score["userId"] = str(user_id_obj)
    profile_score.pop("_id", None)
    return ProfileScoreResponse(**profile_score)

async def get_growth_timeline(user_id: str) -> GrowthTimelineResponse:
    user_id_obj = ObjectId(user_id)
    profile_score = await db.profile_score_collection.find_one({"userId": user_id_obj})
    enhanced_cv = await db.db["enhancedMasterCv"].find_one({"userId": user_id_obj}, {"_id": 0})
    
    if not profile_score:
        profile_score = {}
    if not enhanced_cv:
        enhanced_cv = {}

    confidence_scores = profile_score.get("ConfidenceScore", [])
    ecv = enhanced_cv.get("enhanced_master_cv", enhanced_cv)
    challenges = enhanced_cv.get("challenges", ecv.get("challenges", enhanced_cv.get("enhanced_challenges", [])))[:3]
    career_goal = ecv.get("carrierGoal", "")

    data_str = json.dumps({
        "confidence_scores": confidence_scores,
        "recent_challenges": challenges,
        "career_goal": career_goal
    })

    system_prompt = """
    You are an AI Career Journey analyst. Given the candidate's confidence scores over time and recent challenges, provide:
    - Confidence Trajectory: A short string (e.g., "+15% boost", "Steady", "-5% declined").
    - AI Insight: Analyze the last 3 challenges to identify which skills are getting a boost.
    - Next Best Action: Analyze challenges and skills to suggest the next best action towards their career goal.
    
    Output exactly in this JSON format:
    {
        "ConfidenceTrajectory": "string",
        "AIInsight": "string",
        "NextBestAction": {
            "action": "string",
            "new_skill": "string",
            "profile_score_increase": "string"
        }
    }
    """

    response = await client.chat.completions.create(
        model="gpt-4o",
        temperature=0.3,
        response_format={ "type": "json_object" },
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Data: {data_str}"}
        ]
    )

    return GrowthTimelineResponse(**json.loads(response.choices[0].message.content))

async def get_future_growth_path(user_id: str) -> FutureGrowthPathResponse:
    user_id_obj = ObjectId(user_id)
    enhanced_cv = await db.db["enhancedMasterCv"].find_one({"userId": user_id_obj}, {"_id": 0})
    if not enhanced_cv:
        enhanced_cv = {}

    ecv = enhanced_cv.get("enhanced_master_cv", enhanced_cv)
    career_goal = ecv.get("carrierGoal", "")
    current_role = ecv.get("currentRole", "")

    system_prompt = """
    You are an AI Career Path architect. Given the candidate's current role and career goal, map out a 4-step career ladder.
    The 4 steps are:
    1. now: Current situation
    2. next: The immediate next step
    3. growth phase: The intermediate step
    4. next level: The ultimate goal (or beyond)
    
    Output strictly in this JSON format:
    {
        "now": {"Title": "string", "Responsibility": "string", "ExperienceNeed": "string", "YearNeed": "string"},
        "next": {"Title": "string", "Responsibility": "string", "ExperienceNeed": "string", "YearNeed": "string"},
        "growth phase": {"Title": "string", "Responsibility": "string", "ExperienceNeed": "string", "YearNeed": "string"},
        "next level": {"Title": "string", "Responsibility": "string", "ExperienceNeed": "string", "YearNeed": "string"}
    }
    """

    response = await client.chat.completions.create(
        model="gpt-4o",
        temperature=0.3,
        response_format={ "type": "json_object" },
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Current Role: {current_role}, Career Goal: {career_goal}"}
        ]
    )

    return FutureGrowthPathResponse(**json.loads(response.choices[0].message.content))

async def get_roadmap(user_id: str) -> RoadmapResponse:
    user_id_obj = ObjectId(user_id)
    enhanced_cv = await db.db["enhancedMasterCv"].find_one({"userId": user_id_obj}, {"_id": 0})
    if not enhanced_cv:
        enhanced_cv = {}

    ecv = enhanced_cv.get("enhanced_master_cv", enhanced_cv)
    career_goal = ecv.get("carrierGoal", "")
    current_role = ecv.get("currentRole", "")
    skills = enhanced_cv.get("skills", [])
    challenges = enhanced_cv.get("challenges", ecv.get("challenges", enhanced_cv.get("enhanced_challenges", [])))

    data_str = json.dumps({
        "current_role": current_role,
        "career_goal": career_goal,
        "skills": skills,
        "challenges": challenges
    })

    system_prompt = """
    You are an AI Career Roadmap planner. Based on the user's current role, career goal, skills, and challenges, generate a comprehensive roadmap.
    Identify skills they have and skills they lack. Provide actionable hints and progress percentages.

    Output strictly in this JSON format:
    {
        "roadmapPreview": {
            "Now": {"Title": "string", "Small job responsibility": "string", "experience year needed": "string"}
        },
        "roadmap": {
            "has": [
                {"Title": "string", "score": 80, "next action/hints to increase the point": "string"}
            ],
            "dont have": [
                {"Title": "string", "Subtitle": "string"}
            ]
        },
        "ai insight": {
            "Title": "You're building strong expertise in X and Y",
            "Description": "string",
            "Recommendation": "string",
            "Top Theme": ["Theme1", "Theme2"],
            "emerging strength": "string",
            "why this matters": "string"
        },
        "Achievement": "75%",
        "Estimated Timeline": "10-12 Months"
    }
    """

    response = await client.chat.completions.create(
        model="gpt-4o",
        temperature=0.3,
        response_format={ "type": "json_object" },
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Data: {data_str}"}
        ]
    )

    return RoadmapResponse(**json.loads(response.choices[0].message.content))

async def get_opportunities(user_id: str) -> OpportunitiesResponse:
    user_id_obj = ObjectId(user_id)
    enhanced_cv = await db.db["enhancedMasterCv"].find_one({"userId": user_id_obj}, {"_id": 0})
    if not enhanced_cv:
        enhanced_cv = {}

    # Send relevant parts to save tokens
    ecv = enhanced_cv.get("enhanced_master_cv", enhanced_cv)
    data_to_analyze = {
        "skills": enhanced_cv.get("skills", []),
        "challenges": enhanced_cv.get("challenges", ecv.get("challenges", enhanced_cv.get("enhanced_challenges", []))),
        "current_role": ecv.get("currentRole", ""),
        "strengths": ecv.get("strength", []),
        "domain": ecv.get("domain", "")
    }

    system_prompt = """
    You are an AI Career Opportunities identifier. Based on the entire profile, suggest 2 to 5 alternative roles that fit the user.
    For each role, provide a comment, a fit score, and a breakdown of matching skill traits with their scores.
    Important: Write all comments addressing the user directly in the second person (e.g., use "Your skills...", "You have...", instead of "The user's...").

    Output strictly in this JSON format:
    {
        "role": [
            {
                "Title": "Role Title",
                "Comment": "Why this role fits",
                "skilTraits": [
                    {"name": "Skill1", "score": 85},
                    {"name": "Skill2", "score": 90}
                ],
                "roleFitComment": "Overall fit comment",
                "roleFitScore": 88
            }
        ]
    }
    """

    response = await client.chat.completions.create(
        model="gpt-4o",
        temperature=0.3,
        response_format={ "type": "json_object" },
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Profile: {json.dumps(data_to_analyze)}"}
        ]
    )

    return OpportunitiesResponse(**json.loads(response.choices[0].message.content))
