from fastapi import APIRouter, HTTPException, Query
from app.Services.careerJourney.careerJourney_schema import (
    ProfileScoreRequest,
    ProfileScoreResponse,
    GrowthTimelineResponse,
    FutureGrowthPathResponse,
    RoadmapResponse,
    OpportunitiesResponse
)
from app.Services.careerJourney import careerJourney

router = APIRouter()

@router.post("/profile-score", response_model=ProfileScoreResponse)
async def update_profile_score(req: ProfileScoreRequest):
    try:
        return await careerJourney.update_profile_score(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/growth-timeline", response_model=GrowthTimelineResponse)
async def get_growth_timeline(userId: str = Query(..., description="The user ID")):
    try:
        return await careerJourney.get_growth_timeline(userId)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/future-growth-path", response_model=FutureGrowthPathResponse)
async def get_future_growth_path(userId: str = Query(..., description="The user ID")):
    try:
        return await careerJourney.get_future_growth_path(userId)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/roadmap", response_model=RoadmapResponse)
async def get_roadmap(userId: str = Query(..., description="The user ID")):
    try:
        return await careerJourney.get_roadmap(userId)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/opportunities", response_model=OpportunitiesResponse)
async def get_opportunities(userId: str = Query(..., description="The user ID")):
    try:
        return await careerJourney.get_opportunities(userId)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
