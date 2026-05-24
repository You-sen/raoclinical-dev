from fastapi import APIRouter, HTTPException, status
from app.Services.masterCV.masterCV_schema import (
    MasterCVData,
    EnhancedMasterCVResponse,
    EnhanceChallengeRequest,
    EnhanceChallengeResponse,
)
from app.Services.masterCV.masterCV import enhance_master_cv, enhance_challenge
from typing import List, Any
from pydantic import BaseModel

router = APIRouter(prefix="/master-cv", tags=["MasterCV"])


# ─────────────────────────────────────────────
# Request body: masterCV + role skill collection
# ─────────────────────────────────────────────

# class EnhanceMasterCVRequest(BaseModel):
#     masterCV: MasterCVRequest
#     roleSkills: List[Any] = []   # skill list for the candidate's role/domain


# ─────────────────────────────────────────────
# POST /master-cv/enhance
# ─────────────────────────────────────────────

@router.post(
    "/enhance",
    response_model=EnhancedMasterCVResponse,
    status_code=status.HTTP_200_OK,
)
async def enhance_master_cv_endpoint(body: MasterCVData):
    """
    Accepts a MasterCV + optional role skill collection from the frontend.
    Returns the fully enhanced MasterCV with skills, skill gaps, AI impacts,
    STAR-formatted challenges, and an AI score.
    """
    try:
        # cv_data = body.masterCV.data

        # enhanced_data = await enhance_master_cv(
        #     cv=cv_data,
        #     role_skill_collection=body.roleSkills,
        # )
        enhanced_data = await enhance_master_cv(
            cv=body,
            role_skill_collection=[],
        )

        return EnhancedMasterCVResponse(
            success=True,
            statusCode=200,
            message="MasterCV enhanced successfully!",
            data=enhanced_data,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"MasterCV enhancement failed: {str(e)}",
        )
    
# ─────────────────────────────────────────────
# POST /master-cv/enhance-challenge
# ─────────────────────────────────────────────
 
@router.post(
    "/enhance-challenge",
    response_model=EnhanceChallengeResponse,
    status_code=status.HTTP_200_OK,
)
async def enhance_challenge_endpoint(body: EnhanceChallengeRequest):
    """
    Receives userId + raw STAR fields (situation, task, action, result).
    Returns enhanced STAR story with an AI-inferred challengeName.
    No DB read or write.
    """
    try:
        data = await enhance_challenge(body)
 
        return EnhanceChallengeResponse(
            success=True,
            statusCode=200,
            message="Challenge enhanced successfully!",
            data=data,
        )
 
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Challenge enhancement failed: {str(e)}",
        )
# from fastapi import APIRouter, HTTPException, status
# from app.Services.masterCV.masterCV_schema import (
#     MasterCVRequest,
#     EnhancedMasterCVResponse,
#     EnhanceChallengeRequest,
#     EnhanceChallengeResponse,
# )
# from app.Services.masterCV.masterCV import enhance_master_cv, enhance_challenge
# from typing import List, Any
# from pydantic import BaseModel

# router = APIRouter(prefix="/master-cv", tags=["MasterCV"])


# # ─────────────────────────────────────────────
# # Request body: masterCV + role skill collection
# # ─────────────────────────────────────────────

# # class EnhanceMasterCVRequest(BaseModel):
# #     masterCV: MasterCVRequest
# #     roleSkills: List[Any] = []   # skill list for the candidate's role/domain


# # ─────────────────────────────────────────────
# # POST /master-cv/enhance
# # ─────────────────────────────────────────────

# @router.post(
#     "/enhance",
#     response_model=EnhancedMasterCVResponse,
#     status_code=status.HTTP_200_OK,
# )
# async def enhance_master_cv_endpoint(body: MasterCVRequest):
#     """
#     Accepts a MasterCV + optional role skill collection from the frontend.
#     Returns the fully enhanced MasterCV with skills, skill gaps, AI impacts,
#     STAR-formatted challenges, and an AI score.
#     """
#     try:
#         # cv_data = body.masterCV.data

#         # enhanced_data = await enhance_master_cv(
#         #     cv=cv_data,
#         #     role_skill_collection=body.roleSkills,
#         # )
#         enhanced_data = await enhance_master_cv(
#             cv=body.data,
#             role_skill_collection=[],
#         )

#         return EnhancedMasterCVResponse(
#             success=True,
#             statusCode=200,
#             message="MasterCV enhanced successfully!",
#             data=enhanced_data,
#         )

#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"MasterCV enhancement failed: {str(e)}",
#         )
    
# # ─────────────────────────────────────────────
# # POST /master-cv/enhance-challenge
# # ─────────────────────────────────────────────
 
# @router.post(
#     "/enhance-challenge",
#     response_model=EnhanceChallengeResponse,
#     status_code=status.HTTP_200_OK,
# )
# async def enhance_challenge_endpoint(body: EnhanceChallengeRequest):
#     """
#     Receives userId + raw STAR fields (situation, task, action, result).
#     Returns enhanced STAR story with an AI-inferred challengeName.
#     No DB read or write.
#     """
#     try:
#         data = await enhance_challenge(body)
 
#         return EnhanceChallengeResponse(
#             success=True,
#             statusCode=200,
#             message="Challenge enhanced successfully!",
#             data=data,
#         )
 
#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Challenge enhancement failed: {str(e)}",
#         )
# from fastapi import APIRouter, HTTPException, status
# from app.Services.masterCV.masterCV_schema import (
#     MasterCVRequest,
#     EnhancedMasterCVResponse,
#     EnhanceChallengeRequest,
#     EnhanceChallengeResponse,
# )
# from app.Services.masterCV.masterCV import enhance_master_cv, enhance_challenge
# from typing import List, Any
# from pydantic import BaseModel

# router = APIRouter(prefix="/master-cv", tags=["MasterCV"])


# # ─────────────────────────────────────────────
# # Request body: masterCV + role skill collection
# # ─────────────────────────────────────────────

# # class EnhanceMasterCVRequest(BaseModel):
# #     masterCV: MasterCVRequest
# #     roleSkills: List[Any] = []   # skill list for the candidate's role/domain


# # ─────────────────────────────────────────────
# # POST /master-cv/enhance
# # ─────────────────────────────────────────────

# @router.post(
#     "/enhance",
#     response_model=EnhancedMasterCVResponse,
#     status_code=status.HTTP_200_OK,
# )
# async def enhance_master_cv_endpoint(body: MasterCVRequest):
#     """
#     Accepts a MasterCV + optional role skill collection from the frontend.
#     Returns the fully enhanced MasterCV with skills, skill gaps, AI impacts,
#     STAR-formatted challenges, and an AI score.
#     """
#     try:
#         # cv_data = body.masterCV.data

#         # enhanced_data = await enhance_master_cv(
#         #     cv=cv_data,
#         #     role_skill_collection=body.roleSkills,
#         # )
#         enhanced_data = await enhance_master_cv(
#             cv=body.data,
#             role_skill_collection=[],
#         )

#         return EnhancedMasterCVResponse(
#             success=True,
#             statusCode=200,
#             message="MasterCV enhanced successfully!",
#             data=enhanced_data,
#         )

#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"MasterCV enhancement failed: {str(e)}",
#         )
    
# # ─────────────────────────────────────────────
# # POST /master-cv/enhance-challenge
# # ─────────────────────────────────────────────
 
# @router.post(
#     "/enhance-challenge",
#     response_model=EnhanceChallengeResponse,
#     status_code=status.HTTP_200_OK,
# )
# async def enhance_challenge_endpoint(body: EnhanceChallengeRequest):
#     """
#     Receives userId + raw STAR fields (situation, task, action, result).
#     Returns enhanced STAR story with an AI-inferred challengeName.
#     No DB read or write.
#     """
#     try:
#         data = await enhance_challenge(body)
 
#         return EnhanceChallengeResponse(
#             success=True,
#             statusCode=200,
#             message="Challenge enhanced successfully!",
#             data=data,
#         )
 
#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Challenge enhancement failed: {str(e)}",
#         )