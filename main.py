from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware

from app.DB.vectorDB.vectordb import create_collections, client, GIG_COLLECTION, VECTOR_SIZE
from app.DB.vectorDB.router import router as vectorDB_router
from app.DB.mongodb.router import router as mongodb_router

from app.Services.resume_parse.resume_parse_router import router as resume_parse_router
from app.Services.refelection.refelection_router import router as refelection_router
from app.Services.recommend_skill.recommend_skill_router import router as recommend_skill_router
from app.Services.clearity_score.clearity_score_router import router as clearity_score_router
from app.Services.skill_impact.skill_impact_router import router as skill_impact_router
from app.Services.match_gig.match_gig_router import router as match_gig_router
from app.Services.user_skillgap.user_skillgap_router import router as user_skillgap_router
from app.Services.mentor_match.mentor_match_router import router as mentor_match_router
from app.Services.masterCV.masterCV_router import router as master_cv_router
from app.Services.coverLetter.coverLetter_router import router as cover_letter_router
from app.Services.tailorCV.tailorCV_router import router as tailor_cv_router
from app.Services.interviewPrepare.interviewPrepare_router import router as interview_router


from app.utils.cron import start_scheduler
from app.Services.match_gig.match_gig import get_match_gig


@asynccontextmanager
async def lifespan(app: FastAPI):
     try:
          info = await client.get_collection(GIG_COLLECTION)
          existing_dim = info.config.params.vectors.size
          if existing_dim != VECTOR_SIZE:
               print(f"⚠️  Dimension mismatch: existing={existing_dim}, required={VECTOR_SIZE}")
               print("🔄 Recreating collections...")
               from app.DB.vectorDB.vectordb import recreate_collections
               await recreate_collections()
          else:
               await create_collections()
     except Exception:
          await create_collections()

     get_match_gig()
     start_scheduler()
     yield


app = FastAPI(
     title="SkillQuix",
     description="SkillQuix AI API",
     version="1.0.0",
     docs_url="/docs",
     redoc_url="/redoc",
     lifespan=lifespan,
)

app.add_middleware(
     CORSMiddleware,
     allow_origins=["*"],
     allow_credentials=True,
     allow_methods=["*"],
     allow_headers=["*"],
)

app.include_router(resume_parse_router,   prefix="/v1", tags=["Resume Parse"])
app.include_router(refelection_router,    prefix="/v1", tags=["Refelection"])
app.include_router(recommend_skill_router,prefix="/v1", tags=["Recommend Skill"])
app.include_router(skill_impact_router,   prefix="/v1", tags=["Skill Impact"])
app.include_router(match_gig_router,      prefix="/v1", tags=["Match Gig"])
app.include_router(vectorDB_router,       prefix="/v1", tags=["VectorDB Operation"])
app.include_router(clearity_score_router, prefix="/v1", tags=["Clearity Score"])
app.include_router(user_skillgap_router,  prefix="/v1", tags=["User Skill Gap"])
app.include_router(mentor_match_router,   prefix="/v1", tags=["Mentor Match"])
app.include_router(mongodb_router,        prefix="/v1", tags=["MongoDB"])
app.include_router(master_cv_router,      prefix="/v1", tags=["MasterCV"])
app.include_router(cover_letter_router, prefix="/v1", tags=["Cover Letter"])
app.include_router(tailor_cv_router, prefix="/v1", tags=["Tailor CV"])
app.include_router(interview_router, prefix="/v1", tags=["Interview Prepare"])



@app.get("/")
def read_root():
     return {"message": "Welcome to SkillQuix AI API"}


@app.on_event("startup")
async def startup_event():
     print("SkillQuix AI API is starting...")


@app.on_event("shutdown")
async def shutdown_event():
     print("SkillQuix AI API is shutting down...")


if __name__ == "__main__":
     import uvicorn
     uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
# pre work start here
# from fastapi import FastAPI,HTTPException
# from contextlib import asynccontextmanager
# from fastapi import FastAPI
# from app.DB.vectorDB.vectordb import create_collections
# from fastapi.middleware.cors import CORSMiddleware
# from app.Services.resume_parse.resume_parse_router import router as resume_parse_router
# from app.Services.refelection.refelection_router import router as refelection_router
# from app.Services.recommend_skill.recommend_skill_router import router as recommend_skill_router
# from app.Services.clearity_score.clearity_score_router import router as clearity_score_router
# from app.Services.skill_impact.skill_impact_router import router as skill_impact_router
# from app.Services.match_gig.match_gig_router import router as match_gig_router
# from app.DB.vectorDB.router import router as vectorDB_router
# from app.utils.cron import start_scheduler
# from app.Services.match_gig.match_gig import get_match_gig
# from app.DB.vectorDB.vectordb import create_collections, client, GIG_COLLECTION, VECTOR_SIZE
# from app.Services.user_skillgap.user_skillgap_router import router as user_skillgap_router
# from app.Services.mentor_match.mentor_match_router import router as mentor_match_router
# from app.DB.mongodb.router import router as mongodb_router

# @asynccontextmanager
# async def lifespan(app: FastAPI):
#      try:
#           info = await client.get_collection(GIG_COLLECTION)
#           existing_dim = info.config.params.vectors.size
#           if existing_dim != VECTOR_SIZE:
#                print(f"⚠️  Dimension mismatch: existing={existing_dim}, required={VECTOR_SIZE}")
#                print("🔄 Recreating collections...")
#                from app.DB.vectorDB.vectordb import recreate_collections
#                await recreate_collections()
#           else:
#                # ✅ Gigs OK — but still ensure resumes & mentors exist
#                await create_collections()
#      except Exception:
#           # GIG collection didn't exist at all — create everything
#           await create_collections()

#      get_match_gig()
#      start_scheduler()
#      yield

# app = FastAPI(
#      title="SkillQuix",
#      description="SkillQuix AI API",
#      version="1.0.0",
#      docs_url="/docs",
#      redoc_url="/redoc",
#      lifespan=lifespan
# )

# app.add_middleware(
#      CORSMiddleware,
#      allow_origins=["*"],
#      allow_credentials=True,
#      allow_methods=["*"],
#      allow_headers=["*"],
# )

# app.include_router(resume_parse_router,prefix="/v1",tags=["Resume Parse"])
# app.include_router(refelection_router,prefix="/v1",tags=["Refelection"])
# app.include_router(recommend_skill_router,prefix="/v1",tags=["Recommend Skill"])
# app.include_router(skill_impact_router,prefix="/v1",tags=["Skill Impact"])
# app.include_router(match_gig_router,prefix="/v1",tags=["Match Gig"])
# app.include_router(vectorDB_router,prefix="/v1",tags=["VectorDB Operation"])
# app.include_router(clearity_score_router,prefix="/v1",tags=["Clearity Score"])
# app.include_router(user_skillgap_router,prefix="/v1",tags=["User Skill Gap"])
# app.include_router(mentor_match_router,prefix="/v1",tags=["Mentor Match"])
# app.include_router(mongodb_router,prefix="/v1",tags=["MongoDB"])

# @app.get("/")
# def read_root():
#      return {"message": "Welcome to SkillQuix AI API"}

# @app.on_event("startup")
# async def startup_event():

#      print("SkillQuix AI API is starting...")

# @app.on_event("shutdown")
# async def shutdown_event():
#      print("SkillQuix AI API is shutting down...")

# if __name__ == "__main__":
#      import uvicorn
#      uvicorn.run("main:app", 
#                host="0.0.0.0", 
#                port=8000, 
#                reload=True
#           ) 
# prev work end here