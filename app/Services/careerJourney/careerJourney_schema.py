from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime, timezone

class ScoreEntry(BaseModel):
    score: float
    date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ProfileScoreRequest(BaseModel):
    userId: str
    AIScore: Optional[ScoreEntry] = None
    ConfidenceScore: Optional[ScoreEntry] = None

class ProfileScoreResponse(BaseModel):
    userId: str
    AIScore: List[ScoreEntry] = []
    ConfidenceScore: List[ScoreEntry] = []
    TopTraits: List[str] = []
    CareerMomentum: dict = {}
    ChallengesConsistency: dict = {}
    GrowthDirection: dict = {}
    JobReadiness: dict = {}
    OverallAssessment: str = ""

class NextBestAction(BaseModel):
    action: str
    new_skill: str
    profile_score_increase: str

class GrowthTimelineResponse(BaseModel):
    ConfidenceTrajectory: str
    AIInsight: str
    NextBestAction: NextBestAction

class CareerPhase(BaseModel):
    Title: str
    Responsibility: str
    ExperienceNeed: str
    YearNeed: str

class FutureGrowthPathResponse(BaseModel):
    now: CareerPhase
    next: CareerPhase
    growth_phase: CareerPhase = Field(alias="growth phase")
    next_level: CareerPhase = Field(alias="next level")

    class Config:
        populate_by_name = True

class RoadmapSkillDonthave(BaseModel):
    Title: str
    Subtitle: str

class RoadmapSkillHas(BaseModel):
    Title: str
    score: int
    next_action: str = Field(alias="next action/hints to increase the point")

class RoadmapHasDontHave(BaseModel):
    has: List[RoadmapSkillHas]
    dont_have: List[RoadmapSkillDonthave] = Field(alias="dont have")

class AIInsightRoadmap(BaseModel):
    Title: str
    Description: str
    Recommendation: str
    TopTheme: List[str] = Field(alias="Top Theme")
    emerging_strength: str = Field(alias="emerging strength")
    why_this_matters: str = Field(alias="why this matters")

class RoadmapResponse(BaseModel):
    roadmapPreview: dict = {"Now": {}}
    roadmap: RoadmapHasDontHave
    ai_insight: AIInsightRoadmap = Field(alias="ai insight")
    Achievement: str
    EstimatedTimeline: str = Field(alias="Estimated Timeline")

    class Config:
        populate_by_name = True

class SkillTrait(BaseModel):
    name: str
    score: int

class RoleOpportunity(BaseModel):
    Title: str
    Comment: str
    skilTraits: List[SkillTrait]
    roleFitComment: str
    roleFitScore: int

class OpportunitiesResponse(BaseModel):
    role: List[RoleOpportunity]
