from fastapi import APIRouter, HTTPException, status
from app.Services.coverLetter.coverLetter_schema import (
    CoverLetterRequest,
    CoverLetterResponse,
)
from app.Services.coverLetter.coverLetter import generate_cover_letter

router = APIRouter(prefix="/cover-letter", tags=["Cover Letter"])


# ─────────────────────────────────────────────
# POST /cover-letter/generate
# ─────────────────────────────────────────────

@router.post(
    "/generate",
    response_model=CoverLetterResponse,
    status_code=status.HTTP_200_OK,
)
async def generate_cover_letter_endpoint(body: CoverLetterRequest):
    """
    Fetches the user's enhancedMasterCV from MongoDB, then generates
    a tailored cover letter based on the job details, template, and tone.
    """
    try:
        data = await generate_cover_letter(body)

        return CoverLetterResponse(
            success=True,
            statusCode=200,
            message="Cover letter generated successfully!",
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
            detail=f"Cover letter generation failed: {str(e)}",
        )