from __future__ import annotations

import json
from typing import Any

from app.DB.mongodb.mongodb import MongoDB
from app.config.settings import settings
from app.prompt.prompt import recommend_skill_system_prompt, recommend_skill_user_prompt
from .recommend_skill_schema import RecommendedSkill
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI


def _normalize_text(value: Any) -> str:
     if value is None:
          return ""
     if isinstance(value, str):
          return value.strip()
     return str(value).strip()


def _extract_resume_context(resume_doc: Any) -> tuple[str, str, list[str], str]:
     if not isinstance(resume_doc, dict):
          return "", "", [], _normalize_text(resume_doc)

     domain = _normalize_text(
          resume_doc.get("domain")
          or resume_doc.get("resumeDomain")
          or resume_doc.get("category")
     )
     subdomain = _normalize_text(
          resume_doc.get("subDomain")
          or resume_doc.get("subdomain")
          or resume_doc.get("resumeSubdomain")
          or resume_doc.get("sub_category")
     )

     skills: list[str] = []
     for skill_group in resume_doc.get("skills", []) or []:
          if not isinstance(skill_group, dict):
               continue

          category = _normalize_text(skill_group.get("category") or skill_group.get("Category"))
          if category:
               skills.append(category)

          raw_skills = skill_group.get("Skills") or skill_group.get("skills") or []
          if isinstance(raw_skills, list):
               for skill in raw_skills:
                    normalized = _normalize_text(skill)
                    if normalized:
                         skills.append(normalized)

     seen = set()
     deduped_skills = []
     for skill in skills:
          key = skill.lower()
          if key in seen:
               continue
          seen.add(key)
          deduped_skills.append(skill)

     summary = _normalize_text(resume_doc.get("summary"))
     return domain, subdomain, deduped_skills, summary


def _render_prompt(template: str, **values: Any) -> str:
     rendered = template
     for key, value in values.items():
          rendered = rendered.replace(f"{{{key}}}", str(value))
     return rendered


class RecommendSkillAgent:
     def __init__(self):
          self.model = ChatOpenAI(
               model="gpt-4o-mini",
               temperature=0.1,
               max_tokens=1000,
               timeout=30,
               api_key=settings.OPENAI_API_KEY,
          )
          self.db = MongoDB()

     def _post_process(self, skills: list[dict[str, Any]]) -> list[dict[str, Any]]:
          cleaned_skills: list[dict[str, Any]] = []
          seen: set[str] = set()

          for skill in skills:
               if not isinstance(skill, dict):
                    continue

               name = _normalize_text(skill.get("skill"))
               if not name:
                    continue

               normalized_name = name.lower()
               if normalized_name in seen:
                    continue
               seen.add(normalized_name)

               cleaned_skills.append(
                    {
                         "category": _normalize_text(skill.get("category") or "General"),
                         "skill": name,
                         "demand_level": _normalize_text(skill.get("demand_level") or "Medium"),
                         "reason": _normalize_text(skill.get("reason") or ""),
                    }
               )

          return cleaned_skills[:5]

     async def get_response(self, user_id: str):
          try:
               resume_doc = await self.db.get_resume_by_user_id(user_id)
               if not resume_doc:
                    raise ValueError("Resume not found for this user")

               domain, subdomain, skills, summary = _extract_resume_context(resume_doc)
               system_prompt = _render_prompt(
                    recommend_skill_system_prompt,
                    schema=json.dumps(RecommendedSkill.model_json_schema(), ensure_ascii=False),
               )

               user_prompt = _render_prompt(
                    recommend_skill_user_prompt,
                    user_resume=json.dumps(
                         {
                              "domain": domain,
                              "subdomain": subdomain,
                              "skills": skills,
                              "summary": summary,
                         },
                         indent=2,
                         ensure_ascii=False,
                    ),
               )

               output_content = await self.model.ainvoke([
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=user_prompt),
               ])

               final_message = _normalize_text(output_content.content)
               clean_json = final_message.replace("```json", "").replace("```", "").strip()
               parsed_result = json.loads(clean_json)

               recommended_skills = RecommendedSkill(**parsed_result)
               model_output = recommended_skills.model_dump()
               model_output["recommended_skills"] = self._post_process(model_output.get("recommended_skills", []))

               return model_output

          except Exception as e:
               raise e