from fastapi import APIRouter, HTTPException, status
from app.Services.interviewPrepare.interviewPrepare_schema import (
    InterviewQuestionsRequest,
    InterviewQuestionsResponse,
    ScoreRequest,
    ScoreResponse,
)
from app.Services.interviewPrepare.interviewPrepare import (
    generate_interview_questions,
    score_answer,
)

router = APIRouter(prefix="/interview", tags=["Interview Prepare"])


# ─────────────────────────────────────────────
# POST /interview/questions
# ─────────────────────────────────────────────

@router.post(
    "/questions",
    response_model=InterviewQuestionsResponse,
    status_code=status.HTTP_200_OK,
)
async def get_interview_questions(body: InterviewQuestionsRequest):
    """
    Fetches the user's enhancedMasterCV and generates 15 personalised
    interview questions across 8 question types.
    """
    try:
        data = await generate_interview_questions(body)

        return InterviewQuestionsResponse(
            success=True,
            statusCode=200,
            message="Interview questions generated successfully!",
            data=data,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Question generation failed: {str(e)}",
        )


# ─────────────────────────────────────────────
# POST /interview/score
# ─────────────────────────────────────────────

@router.post(
    "/score",
    response_model=ScoreResponse,
    status_code=status.HTTP_200_OK,
)
async def score_interview_answer(body: ScoreRequest):
    """
    Scores a candidate's answer to an interview question.
    Dynamically loads CV context from MongoDB for question types
    that require profile-aware evaluation (Behavioral, Technical, etc).
    Returns clarity, relevance, structure, confidence scores and overall out of 100.
    """
    try:
        data = await score_answer(body)

        return ScoreResponse(
            success=True,
            statusCode=200,
            message="Answer scored successfully!",
            data=data,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Answer scoring failed: {str(e)}",
        )