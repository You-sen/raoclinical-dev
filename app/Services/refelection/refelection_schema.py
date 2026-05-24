from pydantic import BaseModel, Field
from typing import List


class skill(BaseModel):
     skillName: str = Field(..., description="Name of the skill")
     skillCategory: str = Field(..., description="Category of the skill")
     proficiencyLevel: str = Field(..., description="Proficiency level of the skill")
     yearOfExperience: int = Field(..., description="Year of experience in the skill")

class refelectionResponse(BaseModel):
     extractedSkills: List[skill] = Field(default_factory=list , description="List of extracted skills from the reflection") 
     impectBullects: List[str] = Field(default_factory=list, description="List of impact bullets from the reflection")
     shortSummary: str = Field(default="", description="Summary of the reflection")

