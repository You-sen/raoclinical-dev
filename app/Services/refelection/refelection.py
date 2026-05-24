from openai import AsyncOpenAI
from .refelection_schema import refelectionResponse
from app.prompt.prompt import refelection_system_prompt, refelection_user_prompt
from app.DB.mongodb.mongodb import MongoDB
from app.config.settings import settings
import json



class refelection:
     def __init__(self):
          self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
          self.mongodb = MongoDB()

     async def get_user_info(self, user_id: str) -> dict:
          try:
               user = await self.mongodb.get_resume_by_user_id(user_id)
               return user
          except Exception as e:
               print(e)
               return {}

     async def get_refelection(self, user_id: str, work_text: str, reasoning_text: str, impact_text: str) -> refelectionResponse:
          try:
               user_info = await self.get_user_info(user_id)
               print(user_info)
               completion = await self.client.chat.completions.create(
               model="gpt-4o-mini",
               messages=[
                    {"role": "system", "content": refelection_system_prompt.format(schema=refelectionResponse.model_json_schema())},
                    {"role": "user", "content": refelection_user_prompt.format(user_info=user_info,work_text=work_text, reasoning_text=reasoning_text, impact_text=impact_text)},
               ],
               response_format={"type": "json_object"},
          )
               response = completion.choices[0].message.content

               if response.startswith("```json"):
                    response = response[7:-3]
               
               response_dict = json.loads(response)
               print(response_dict)
               return refelectionResponse(**response_dict)
          except Exception as e:
               print(e)
               return refelectionResponse()
