from pydantic import BaseModel
from typing import Optional, List


# ─────────────────────────────────────────────
# REQUEST
# ─────────────────────────────────────────────

class TailorCVRequest(BaseModel):
    userId:         str
    jobDescription: str


# ─────────────────────────────────────────────
# RESPONSE — mirrors enhanced_master_cv shape
# but every field is Optional (leave empty if
# no evidence found in the CV for that job)
# ─────────────────────────────────────────────

class TailoredWorkExperience(BaseModel):
    company:          Optional[str] = None
    position:         Optional[str] = None
    duration:         Optional[str] = None
    responsibilities: Optional[str] = None   # rewritten for job fit
    projects:         Optional[List[str]] = None

class TailoredChallenge(BaseModel):
    challengeName: Optional[str] = None
    situation:     Optional[str] = None
    task:          Optional[str] = None
    action:        Optional[str] = None
    result:        Optional[str] = None

class TailoredSkill(BaseModel):
    skillName:        Optional[str] = None
    skillCategory:    Optional[str] = None
    proficiencyLevel: Optional[str] = None
    yearOfExperience: Optional[int] = None
    relevanceScore:   Optional[int] = None   # 0-100: how relevant to THIS job

class TailoredEducation(BaseModel):
    degree:           Optional[str] = None
    certificateName:  Optional[str] = None
    institution:      Optional[str] = None
    organizationName: Optional[str] = None
    passingYear:      Optional[str] = None
    issueDate:        Optional[str] = None

class TailoredCVData(BaseModel):
    # Identity — passed through unchanged
    fullName:        Optional[str] = None
    email:           Optional[str] = None
    phoneNumber:     Optional[str] = None
    location:        Optional[str] = None
    linkedinUrl:     Optional[str] = None
    portfolioUrl:    Optional[str] = None
    resumeLink:      Optional[str] = None

    # Role context — tailored
    currentRole:          Optional[str] = None
    careerStage:          Optional[str] = None
    totalExperienceYear:  Optional[int] = None
    domain:               Optional[str] = None
    subDomain:            Optional[str] = None
    industry:             Optional[str] = None

    # Narrative — rewritten for job fit
    bio:           Optional[str] = None
    resumeSummary: Optional[str] = None
    carrierGoal:   Optional[str] = None

    # Content — filtered and rewritten for job fit
    strength:                    Optional[List[str]] = None
    workExperiences:             Optional[List[TailoredWorkExperience]] = None
    educationsAndCertifications: Optional[List[TailoredEducation]] = None
    relevantSkills:              Optional[List[TailoredSkill]] = None
    relevantChallenges:          Optional[List[TailoredChallenge]] = None


class TailorCVResponse(BaseModel):
    success:    bool
    statusCode: int
    message:    str
    data:       TailoredCVData