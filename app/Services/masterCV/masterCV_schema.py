from pydantic import BaseModel, Field
from typing import List, Optional, Any
from datetime import datetime
 
 
# ─────────────────────────────────────────────
# INPUT SCHEMA  (what frontend sends)
# ─────────────────────────────────────────────
 
class ChallengeInput(BaseModel):
    situation: Optional[str] = None
    task:      Optional[str] = None
    action:    Optional[str] = None
    result:    Optional[str] = None
 
 
class EducationInput(BaseModel):
    degree: Optional[str] = None
    certificateName: Optional[str] = None
    institution: Optional[str] = None
    organizationName: Optional[str] = None
    passingYear: Optional[str] = None
    issueDate: Optional[str] = None
 
 
class WorkExperienceInput(BaseModel):
    company:          Optional[str]       = None
    position:         Optional[str]       = None
    duration:         Optional[str]       = None
    responsibilities: Optional[str]       = None   # plain string
    projects:         Optional[List[str]] = None
 
 
class MasterCVData(BaseModel):
    id: Optional[str] = None
    userId: Optional[str] = None
    accomplishments: Optional[Any] = None
    appliedGigs: Optional[Any] = None
    bio: Optional[str] = None
    careerStage: Optional[str] = None
    carrierGoal: Optional[str] = None
    challenges: Optional[List[ChallengeInput]] = None
    currentRole: Optional[str] = None
    domain: Optional[str] = None
    educationsAndCertifications: Optional[List[EducationInput]] = None
    email: Optional[str] = None
    fullName: Optional[str] = None
    generatedCvJson: Optional[Any] = None
    industry: Optional[str] = None
    languages: Optional[List[str]] = None
    lastGeneratedAt: Optional[Any] = None
    linkedinUrl: Optional[str] = None
    location: Optional[str] = None
    mentorProfile: Optional[Any] = None
    phoneNumber: Optional[str] = None
    portfolioUrl: Optional[str] = None
    refletions: Optional[Any] = None
    resumeSections: Optional[Any] = None
    resumeSummary: Optional[str] = None
    resumeLink: Optional[str] = None
    savedGigs: Optional[Any] = None
    skills: Optional[List[str]] = None   # array of skill strings
    strength: Optional[List[str]] = None
    subDomain: Optional[List[str]] = None  # array from DB
    totalExperienceYear: Optional[Any] = None
    version: Optional[int] = None
    projects: Optional[List[Any]] = None
    workExperiences: Optional[List[WorkExperienceInput]] = None
    createdAt: Optional[Any] = None
    updatedAt: Optional[Any] = None
 
 
class MasterCVRequest(BaseModel):
    success: bool
    statusCode: int
    message: str
    data: MasterCVData
 
 
# ─────────────────────────────────────────────
# OUTPUT SCHEMA  (what we return to frontend)
# ─────────────────────────────────────────────
 
class ScoreBreakdown(BaseModel):
    roleAlignment: int = 0
    experienceWeight: int = 0
 
 
class SkillOut(BaseModel):
    skillName: str
    skillCategory: str
    proficiencyLevel: str
    yearOfExperience: int = 0
    source: str                  # MASTER_CV | CHALLENGE_EXTRACTED
    score: int                   # 0-100
    scoreBreakdown: Optional[ScoreBreakdown] = None
 
 
class GapScoreBreakdown(BaseModel):
    roleAlignment: int = 0
    demandWeight: int = 0
 
 
class SkillGapOut(BaseModel):
    skillName: str
    skillCategory: str
    proficiencyLevel: str
    demandLevel: str             # High | Medium | Low
    score: int
    scoreBreakdown: Optional[GapScoreBreakdown] = None
    gapReason: str
    suggestion: str
    sourceCollection: str        # ROLE_SKILLS | DOMAIN_INFERRED
 
 
class AIImpact(BaseModel):
    field: str
    original: str
    enhanced: str
 
 
class EnhancedChallenge(BaseModel):
    challengeName: str
    situation: str
    task: str
    action: str
    result: str
 
 
class AIScoreBreakdown(BaseModel):
    profileCompleteness: int
    skillRelevance: int
    experienceClarity: int
    careerNarrative: int
    skillGapSeverity: int
 
 
class AIScore(BaseModel):
    total: int
    grade: str                   # S A B C D
    summary: str
    breakdown: AIScoreBreakdown
 
 
class WorkExperienceOut(BaseModel):
    company:          Optional[str]       = None
    position:         Optional[str]       = None
    duration:         Optional[str]       = None
    responsibilities: Optional[str]       = None   # AI returns plain string
    projects:         Optional[List[str]] = None
 
 
class EnhancedMasterCV(BaseModel):
    fullName: Optional[str] = None
    email: Optional[str] = None
    phoneNumber: Optional[str] = None
    location: Optional[str] = None
    linkedinUrl: Optional[str] = None
    portfolioUrl: Optional[str] = None
    resumeLink: Optional[str] = None
    currentRole: Optional[str] = None
    careerStage: Optional[str] = None
    totalExperienceYear: Optional[int] = None
    domain: Optional[str] = None
    subDomain: Optional[str] = None       # resolved plain string
    industry: Optional[str] = None
    bio: Optional[str] = None
    resumeSummary: Optional[str] = None
    carrierGoal: Optional[str] = None
    strength: Optional[List[str]] = None
    languages: Optional[List[str]] = None
    workExperiences: Optional[List[WorkExperienceOut]] = None
    educationsAndCertifications: Optional[List[EducationInput]] = None
    accomplishments: Optional[Any] = None
    appliedGigs: Optional[Any] = None
    savedGigs: Optional[Any] = None
    mentorProfile: Optional[Any] = None
    resumeSections: Optional[Any] = None
    generatedCvJson: Optional[Any] = None
    lastGeneratedAt: Optional[Any] = None
    refletions: Optional[Any] = None
 
 
class EnhancedMasterCVResponse(BaseModel):
    success: bool
    statusCode: int
    message: str
    data: "EnhancedMasterCVData"
 
 
class EnhancedMasterCVData(BaseModel):
    userId: str
    generatedAt: str
    ai_score: AIScore
    skills: List[SkillOut]
    skill_gaps: List[SkillGapOut]
    ai_impacts: List[AIImpact]
    enhanced_challenges: List[EnhancedChallenge]
    enhanced_master_cv: EnhancedMasterCV
 
 
EnhancedMasterCVResponse.model_rebuild()
 
# ─────────────────────────────────────────────
# ENHANCE CHALLENGE ENDPOINT
# ─────────────────────────────────────────────
 
class EnhanceChallengeRequest(BaseModel):
    userId:    str
    situation: str
    task:      str
    action:    str
    result:    str
 
 
class EnhanceChallengeData(BaseModel):
    userId:        str
    challengeName: str
    situation:     str
    task:          str
    action:        str
    result:        str
 
 
class EnhanceChallengeResponse(BaseModel):
    success:    bool
    statusCode: int
    message:    str
    data:       EnhanceChallengeData


# from pydantic import BaseModel, Field
# from typing import List, Optional, Any
# from datetime import datetime


# # ─────────────────────────────────────────────
# # INPUT SCHEMA  (what frontend sends)
# # ─────────────────────────────────────────────

# class ChallengeInput(BaseModel):
#     situation: Optional[str] = None
#     task:      Optional[str] = None
#     action:    Optional[str] = None
#     result:    Optional[str] = None


# class EducationInput(BaseModel):
#     degree: Optional[str] = None
#     certificateName: Optional[str] = None
#     institution: Optional[str] = None
#     organizationName: Optional[str] = None
#     passingYear: Optional[str] = None
#     issueDate: Optional[str] = None


# class WorkExperienceInput(BaseModel):
#     companyName: Optional[str] = None
#     role: Optional[str] = None
#     duration: Optional[str] = None
#     responsibilities: Optional[List[str]] = None   # array of strings
#     technologies: Optional[List[str]] = None


# class MasterCVData(BaseModel):
#     id: Optional[str] = None
#     userId: str
#     accomplishments: Optional[Any] = None
#     appliedGigs: Optional[Any] = None
#     bio: Optional[str] = None
#     careerStage: Optional[str] = None
#     carrierGoal: Optional[str] = None
#     challenges: Optional[List[ChallengeInput]] = None
#     currentRole: Optional[str] = None
#     domain: Optional[str] = None
#     educationsAndCertifications: Optional[List[EducationInput]] = None
#     email: Optional[str] = None
#     fullName: Optional[str] = None
#     generatedCvJson: Optional[Any] = None
#     industry: Optional[str] = None
#     languages: Optional[List[str]] = None
#     lastGeneratedAt: Optional[Any] = None
#     linkedinUrl: Optional[str] = None
#     location: Optional[str] = None
#     mentorProfile: Optional[Any] = None
#     phoneNumber: Optional[str] = None
#     portfolioUrl: Optional[str] = None
#     refletions: Optional[Any] = None
#     resumeSections: Optional[Any] = None
#     resumeSummary: Optional[str] = None
#     resumeLink: Optional[str] = None
#     savedGigs: Optional[Any] = None
#     skills: Optional[List[str]] = None   # array of skill strings
#     strength: Optional[List[str]] = None
#     subDomain: Optional[List[str]] = None  # array from DB
#     totalExperienceYear: Optional[Any] = None
#     version: Optional[int] = None
#     projects: Optional[List[Any]] = None
#     workExperiences: Optional[List[WorkExperienceInput]] = None
#     createdAt: Optional[Any] = None
#     updatedAt: Optional[Any] = None


# class MasterCVRequest(BaseModel):
#     success: bool
#     statusCode: int
#     message: str
#     data: MasterCVData


# # ─────────────────────────────────────────────
# # OUTPUT SCHEMA  (what we return to frontend)
# # ─────────────────────────────────────────────

# class ScoreBreakdown(BaseModel):
#     roleAlignment: int = 0
#     experienceWeight: int = 0


# class SkillOut(BaseModel):
#     skillName: str
#     skillCategory: str
#     proficiencyLevel: str
#     yearOfExperience: int = 0
#     source: str                  # MASTER_CV | CHALLENGE_EXTRACTED
#     score: int                   # 0-100
#     scoreBreakdown: Optional[ScoreBreakdown] = None


# class GapScoreBreakdown(BaseModel):
#     roleAlignment: int = 0
#     demandWeight: int = 0


# class SkillGapOut(BaseModel):
#     skillName: str
#     skillCategory: str
#     proficiencyLevel: str
#     demandLevel: str             # High | Medium | Low
#     score: int
#     scoreBreakdown: Optional[GapScoreBreakdown] = None
#     gapReason: str
#     suggestion: str
#     sourceCollection: str        # ROLE_SKILLS | DOMAIN_INFERRED


# class AIImpact(BaseModel):
#     field: str
#     original: str
#     enhanced: str


# class EnhancedChallenge(BaseModel):
#     challengeName: str
#     situation: str
#     task: str
#     action: str
#     result: str


# class AIScoreBreakdown(BaseModel):
#     profileCompleteness: int
#     skillRelevance: int
#     experienceClarity: int
#     careerNarrative: int
#     skillGapSeverity: int


# class AIScore(BaseModel):
#     total: int
#     grade: str                   # S A B C D
#     summary: str
#     breakdown: AIScoreBreakdown


# class WorkExperienceOut(BaseModel):
#     companyName: Optional[str] = None
#     role: Optional[str] = None
#     duration: Optional[str] = None
#     responsibilities: Optional[List[str]] = None
#     technologies: Optional[List[str]] = None


# class EnhancedMasterCV(BaseModel):
#     fullName: Optional[str] = None
#     email: Optional[str] = None
#     phoneNumber: Optional[str] = None
#     location: Optional[str] = None
#     linkedinUrl: Optional[str] = None
#     portfolioUrl: Optional[str] = None
#     resumeLink: Optional[str] = None
#     currentRole: Optional[str] = None
#     careerStage: Optional[str] = None
#     totalExperienceYear: Optional[int] = None
#     domain: Optional[str] = None
#     subDomain: Optional[str] = None       # resolved plain string
#     industry: Optional[str] = None
#     bio: Optional[str] = None
#     resumeSummary: Optional[str] = None
#     carrierGoal: Optional[str] = None
#     strength: Optional[List[str]] = None
#     languages: Optional[List[str]] = None
#     workExperiences: Optional[List[WorkExperienceOut]] = None
#     educationsAndCertifications: Optional[List[EducationInput]] = None
#     accomplishments: Optional[Any] = None
#     appliedGigs: Optional[Any] = None
#     savedGigs: Optional[Any] = None
#     mentorProfile: Optional[Any] = None
#     resumeSections: Optional[Any] = None
#     generatedCvJson: Optional[Any] = None
#     lastGeneratedAt: Optional[Any] = None
#     refletions: Optional[Any] = None


# class EnhancedMasterCVResponse(BaseModel):
#     success: bool
#     statusCode: int
#     message: str
#     data: "EnhancedMasterCVData"


# class EnhancedMasterCVData(BaseModel):
#     userId: str
#     generatedAt: str
#     ai_score: AIScore
#     skills: List[SkillOut]
#     skill_gaps: List[SkillGapOut]
#     ai_impacts: List[AIImpact]
#     enhanced_challenges: List[EnhancedChallenge]
#     enhanced_master_cv: EnhancedMasterCV


# EnhancedMasterCVResponse.model_rebuild()

# # ─────────────────────────────────────────────
# # ENHANCE CHALLENGE ENDPOINT
# # ─────────────────────────────────────────────
 
# class EnhanceChallengeRequest(BaseModel):
#     userId:    str
#     situation: str
#     task:      str
#     action:    str
#     result:    str
 
 
# class EnhanceChallengeData(BaseModel):
#     userId:        str
#     challengeName: str
#     situation:     str
#     task:          str
#     action:        str
#     result:        str
 
 
# class EnhanceChallengeResponse(BaseModel):
#     success:    bool
#     statusCode: int
#     message:    str
#     data:       EnhanceChallengeData
# from pydantic import BaseModel, Field
# from typing import List, Optional, Any
# from datetime import datetime


# # ─────────────────────────────────────────────
# # INPUT SCHEMA  (what frontend sends)
# # ─────────────────────────────────────────────

# class ChallengeInput(BaseModel):
#     situation: Optional[str] = None
#     task:      Optional[str] = None
#     action:    Optional[str] = None
#     result:    Optional[str] = None


# class EducationInput(BaseModel):
#     degree: Optional[str] = None
#     certificateName: Optional[str] = None
#     institution: Optional[str] = None
#     organizationName: Optional[str] = None
#     passingYear: Optional[str] = None
#     issueDate: Optional[str] = None


# class WorkExperienceInput(BaseModel):
#     company: Optional[str] = None
#     position: Optional[str] = None
#     duration: Optional[str] = None
#     responsibilities: Optional[str] = None
#     projects: Optional[List[str]] = None


# class MasterCVData(BaseModel):
#     id: Optional[str] = None
#     userId: str
#     accomplishments: Optional[Any] = None
#     appliedGigs: Optional[Any] = None
#     bio: Optional[str] = None
#     careerStage: Optional[str] = None
#     carrierGoal: Optional[str] = None
#     challenges: Optional[List[ChallengeInput]] = None
#     currentRole: Optional[str] = None
#     domain: Optional[str] = None
#     educationsAndCertifications: Optional[List[EducationInput]] = None
#     email: Optional[str] = None
#     fullName: Optional[str] = None
#     generatedCvJson: Optional[Any] = None
#     industry: Optional[str] = None
#     languages: Optional[List[str]] = None
#     lastGeneratedAt: Optional[Any] = None
#     linkedinUrl: Optional[str] = None
#     location: Optional[str] = None
#     mentorProfile: Optional[Any] = None
#     phoneNumber: Optional[str] = None
#     portfolioUrl: Optional[str] = None
#     refletions: Optional[Any] = None
#     resumeSections: Optional[Any] = None
#     resumeSummary: Optional[str] = None
#     resumeLink: Optional[str] = None
#     savedGigs: Optional[Any] = None
#     skills: Optional[Any] = None
#     strength: Optional[List[str]] = None
#     subDomain: Optional[str] = None
#     totalExperienceYear: Optional[Any] = None
#     version: Optional[int] = None
#     workExperiences: Optional[List[WorkExperienceInput]] = None
#     createdAt: Optional[Any] = None
#     updatedAt: Optional[Any] = None


# class MasterCVRequest(BaseModel):
#     success: bool
#     statusCode: int
#     message: str
#     data: MasterCVData


# # ─────────────────────────────────────────────
# # OUTPUT SCHEMA  (what we return to frontend)
# # ─────────────────────────────────────────────

# class ScoreBreakdown(BaseModel):
#     roleAlignment: int
#     experienceWeight: int


# class SkillOut(BaseModel):
#     skillName: str
#     skillCategory: str
#     proficiencyLevel: str
#     yearOfExperience: int
#     source: str                  # MASTER_CV | CHALLENGE_EXTRACTED
#     score: int                   # 0-100
#     scoreBreakdown: ScoreBreakdown


# class GapScoreBreakdown(BaseModel):
#     roleAlignment: int
#     demandWeight: int


# class SkillGapOut(BaseModel):
#     skillName: str
#     skillCategory: str
#     proficiencyLevel: str
#     demandLevel: str             # High | Medium | Low
#     score: int
#     scoreBreakdown: GapScoreBreakdown
#     gapReason: str
#     suggestion: str
#     sourceCollection: str        # ROLE_SKILLS | DOMAIN_INFERRED


# class AIImpact(BaseModel):
#     field: str
#     original: str
#     enhanced: str


# class EnhancedChallenge(BaseModel):
#     challengeName: str
#     situation: str
#     task: str
#     action: str
#     result: str


# class AIScoreBreakdown(BaseModel):
#     profileCompleteness: int
#     skillRelevance: int
#     experienceClarity: int
#     careerNarrative: int
#     skillGapSeverity: int


# class AIScore(BaseModel):
#     total: int
#     grade: str                   # S A B C D
#     summary: str
#     breakdown: AIScoreBreakdown


# class WorkExperienceOut(BaseModel):
#     company: Optional[str] = None
#     position: Optional[str] = None
#     duration: Optional[str] = None
#     responsibilities: Optional[str] = None
#     projects: Optional[List[str]] = None


# class EnhancedMasterCV(BaseModel):
#     fullName: Optional[str] = None
#     email: Optional[str] = None
#     phoneNumber: Optional[str] = None
#     location: Optional[str] = None
#     linkedinUrl: Optional[str] = None
#     portfolioUrl: Optional[str] = None
#     resumeLink: Optional[str] = None
#     currentRole: Optional[str] = None
#     careerStage: Optional[str] = None
#     totalExperienceYear: Optional[int] = None
#     domain: Optional[str] = None
#     subDomain: Optional[str] = None
#     industry: Optional[str] = None
#     bio: Optional[str] = None
#     resumeSummary: Optional[str] = None
#     carrierGoal: Optional[str] = None
#     strength: Optional[List[str]] = None
#     languages: Optional[List[str]] = None
#     workExperiences: Optional[List[WorkExperienceOut]] = None
#     educationsAndCertifications: Optional[List[EducationInput]] = None
#     accomplishments: Optional[Any] = None
#     appliedGigs: Optional[Any] = None
#     savedGigs: Optional[Any] = None
#     mentorProfile: Optional[Any] = None
#     resumeSections: Optional[Any] = None
#     generatedCvJson: Optional[Any] = None
#     lastGeneratedAt: Optional[Any] = None
#     refletions: Optional[Any] = None


# class EnhancedMasterCVResponse(BaseModel):
#     success: bool
#     statusCode: int
#     message: str
#     data: "EnhancedMasterCVData"


# class EnhancedMasterCVData(BaseModel):
#     userId: str
#     generatedAt: str
#     ai_score: AIScore
#     skills: List[SkillOut]
#     skill_gaps: List[SkillGapOut]
#     ai_impacts: List[AIImpact]
#     enhanced_challenges: List[EnhancedChallenge]
#     enhanced_master_cv: EnhancedMasterCV


# EnhancedMasterCVResponse.model_rebuild()

# # ─────────────────────────────────────────────
# # ENHANCE CHALLENGE ENDPOINT
# # ─────────────────────────────────────────────
 
# class EnhanceChallengeRequest(BaseModel):
#     userId:    str
#     situation: str
#     task:      str
#     action:    str
#     result:    str
 
 
# class EnhanceChallengeData(BaseModel):
#     userId:        str
#     challengeName: str
#     situation:     str
#     task:          str
#     action:        str
#     result:        str
 
 
# class EnhanceChallengeResponse(BaseModel):
#     success:    bool
#     statusCode: int
#     message:    str
#     data:       EnhanceChallengeData