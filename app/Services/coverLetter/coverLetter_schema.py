from pydantic import BaseModel
from typing import Optional
from enum import Enum


# ─────────────────────────────────────────────
# ENUMS
# ─────────────────────────────────────────────

class CoverLetterTemplate(str, Enum):
    MODERN  = "Modern"
    CLASSIC = "Classic"
    CONCISE = "Concise"


class CoverLetterTone(str, Enum):
    CONFIDENT         = "Confident"
    ENTHUSIASTIC      = "Enthusiastic"
    FORMAL            = "Formal"
    FRIENDLY          = "Friendly"
    STORY_LED         = "Story-led"
    CONVERSATIONAL    = "Conversational"
    BOLD_CONFIDENT    = "Bold & Confident"
    RESULTS_FOCUSED   = "Results-Focused"
    ANALYTICAL        = "Analytical"
    WARM_APPROACHABLE = "Warm & Approachable"
    CONCISE_DIRECT    = "Concise & Direct"
    PROFESSIONAL      = "Professional"


# ─────────────────────────────────────────────
# REQUEST
# ─────────────────────────────────────────────

class CoverLetterRequest(BaseModel):
    userId:         str
    jobDetails:     str
    role:           str
    jobDescription: Optional[str] = None
    template:       CoverLetterTemplate
    tone:           CoverLetterTone


# ─────────────────────────────────────────────
# RESPONSE
# ─────────────────────────────────────────────

class CoverLetterData(BaseModel):
    coverLetter:  str                    # the generated cover letter text
    template:     CoverLetterTemplate
    tone:         CoverLetterTone
    role:         str
    jobDetails:   str
    wordCount:    int


class CoverLetterResponse(BaseModel):
    success:    bool
    statusCode: int
    message:    str
    data:       CoverLetterData