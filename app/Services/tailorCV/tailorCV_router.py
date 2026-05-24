from fastapi import APIRouter, HTTPException, status
from app.Services.tailorCV.tailorCV_schema import (
    TailorCVRequest,
    TailorCVResponse,
)
from app.Services.tailorCV.tailorCV import tailor_cv

router = APIRouter(prefix="/tailor-cv", tags=["Tailor CV"])


# ─────────────────────────────────────────────
# POST /tailor-cv/generate
# ─────────────────────────────────────────────

@router.post(
    "/generate",
    response_model=TailorCVResponse,
    status_code=status.HTTP_200_OK,
)
async def tailor_cv_endpoint(body: TailorCVRequest):
    """
    Fetches the user's enhancedMasterCV and rewrites it
    to best match the provided job description.
    Nothing is saved to the database — pure generation.
    """
    try:
        data = await tailor_cv(body)

        return TailorCVResponse(
            success=True,
            statusCode=200,
            message="CV tailored successfully!",
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
            detail=f"CV tailoring failed: {str(e)}",
        )