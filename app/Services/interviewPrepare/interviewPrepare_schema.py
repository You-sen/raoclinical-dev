from pydantic import BaseModel
from typing import Optional, List
from enum import Enum


# ─────────────────────────────────────────────
# ENUMS
# ─────────────────────────────────────────────

class QuestionType(str, Enum):
    INTRODUCTION        = "Introduction"
    BEHAVIORAL          = "Behavioral"
    SITUATIONAL         = "Situational"
    COMMUNICATION       = "Communication"
    LEADERSHIP_TEAMWORK = "Leadership & Teamwork"
    MOTIVATION_CAREER   = "Motivation & Career Goal"
    CRITICAL_THINKING   = "Critical Thinking & Problem Solving"
    DOMAIN_SPECIFIC     = "Domain Specific"


# ─────────────────────────────────────────────
# QUESTION GENERATION
# ─────────────────────────────────────────────

class Question(BaseModel):
    questionId:           int
    questionType:         QuestionType
    question:             str
    expectedAnswerTraits: List[str]
    hint:                 str


class InterviewQuestionsRequest(BaseModel):
    userId: str


class InterviewQuestionsData(BaseModel):
    userId:         str
    candidateName:  Optional[str] = None
    role:           Optional[str] = None
    domain:         Optional[str] = None
    totalQuestions: int
    questions:      List[Question]


class InterviewQuestionsResponse(BaseModel):
    success:    bool
    statusCode: int
    message:    str
    data:       InterviewQuestionsData


# ─────────────────────────────────────────────
# ANSWER SCORING
# ─────────────────────────────────────────────

class ScoreRequest(BaseModel):
    userId:       str
    questionType: QuestionType
    question:     str
    answer:       str


class ScoreBreakdown(BaseModel):
    clarity:    int   # out of 10
    relevance:  int   # out of 10
    structure:  int   # out of 10
    confidence: int   # out of 10


class ScoreData(BaseModel):
    questionType:   QuestionType
    question:       str
    scoreBreakdown: ScoreBreakdown
    overallScore:   int            # out of 100
    feedback:       str            # 2-3 sentence qualitative feedback
    improvementTip: str            # 1 actionable tip


class ScoreResponse(BaseModel):
    success:    bool
    statusCode: int
    message:    str
    data:       ScoreData