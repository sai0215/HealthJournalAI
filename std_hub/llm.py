
import copy
from datetime import datetime, timezone
from openai import OpenAI

from std_hub.llm_logs import end_db_add, start_db_add
from std_hub.utils import get_error_result
from std_hub.constants import API_KEY,BASE_URL,MODEL

from std_hub.db.mongodb import db_client

# Handle case where MongoDB is not available
if db_client:
    db = db_client["flow_project"]
    col_projects = db["projects"]
    col_kickoffs = db["kickoffs"]
else:
    db = None
    col_projects = None
    col_kickoffs = None


 

# Point to the local server
base_client = OpenAI(api_key=API_KEY,base_url=BASE_URL)
 
 

class AgentProject:
	def __init__(self, project_id:str=None,user_id:str=None,kickoff_id:str=None,description:str=None,project_name:str=None,inputs_types:dict=None,base_client:OpenAI=base_client,model:str=MODEL):
		self.project_name=project_name
		self.user_id = user_id
		self.project_id = project_id
		self.kickoff_id= kickoff_id
		self.description = description
		self.inputs_types=inputs_types
		self.all_messages = {}
		self.base_client = base_client
		self.model = model

            
	def setup(self,project_id:str=None,user_id:str=None,kickoff_id:str=None,description:str=None,project_name:str=None,inputs_types:dict=None,base_client:OpenAI=None,model:str=None,):
		self.user_id = user_id or self.user_id 
		self.project_id = project_id or self.project_id 
		self.kickoff_id= kickoff_id or self.kickoff_id
		self.description = description or self.description
		self.project_name=project_name or self.project_name
		self.inputs_types=inputs_types or self.inputs_types
		self.base_client = base_client or self.base_client
		self.model = model or self.model

	def get_data(self):
		data = {
			"project_name":self.project_name,
			"project_id":self.project_id,
			"description":self.description,
			"project_type":"flow",
			"var_list":list(self.inputs_types.keys()),
			"inputs_types":self.inputs_types

		}
		return data


	def set_llm_messages(self,message_id:str,message:list,user_id:str=None):
		if not user_id:
			self.all_messages[message_id]=message

		if user_id and col_projects:
	
			query= {"project_id": self.project_id,"user_id":user_id,"message_id":message_id}
			operation={
					# '$inc': {"counter_field": 1},  # Increment the counterField by 1
					'$setOnInsert': { 
						"project_id": self.project_id,
						"user_id":user_id,
						"message_id":message_id,
						'message': message,
						# 'counter_field': 1, 
						
					}
				}

			# Perform the update with upsert
			result = col_projects.update_one(query, operation,upsert=True  )

			# Check if the operation was successful
			if result.matched_count > 0:
				print(f"Document with messageId {message_id} was updated.")
			elif result.upserted_id:
				print(f"New document with messageId {message_id} was created.")
			
	def get_llm_messages(self,message_id:str,variables:dict=None,user_id:str=None):
		
		message = copy.deepcopy(self.all_messages[message_id])

		user_id = user_id or self.user_id 
		if user_id and col_projects:
			query= {"project_id": self.project_id,"user_id":self.user_id,"message_id":message_id}
			res = list(col_projects.find(query))
			if res:
				for data in res:
					if data["message_id"]==message_id:
						if data["message"]:
							message = message

		if variables:
		

			for i, msg in enumerate(message):
				if isinstance(msg["content"],str):
					message[i]["content"] = msg["content"].format(**variables)
				else:
					for j, content_item in enumerate(msg["content"]):
						if content_item["type"] == "text":
							message[i]["content"][j]["text"] = content_item["text"].format(**variables)
						elif content_item["type"] == "image_url":
							message[i]["content"][j]["image_url"]["url"] = content_item["image_url"]["url"].format(**variables)
	

		return message
	





	def generate(self, messages: list, message_id: str = None, model: str = None, client=None, *args, **kwargs):
		import traceback

		model = model or self.model or MODEL
		main_client = client or self.base_client

		# Prepare DB tracking (optional)
		db_data = {
			"project_id": self.project_id,
			"user_id": self.user_id,
			"kickoff_id": self.kickoff_id,
			"model": model,
			"messages": messages,
			"message_id": message_id,
			"status": "Running",
		}
		db_id = start_db_add(db_data=db_data)
		query = {
			"project_id": self.project_id,
			"user_id": self.user_id,
			"kickoff_id": self.kickoff_id,
			"message_id": message_id,
			"_id": db_id,
		}

		error = None
		raw = None
		result = None

		try:
			# OpenAI-compatible API call (works with Perplexity)
			response = main_client.chat.completions.create(
				model=model,
				messages=messages
			)
			raw = response.choices[0].message.content

			result = {
				"raw": raw,
				"token_usage": {
					"prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
					"completion_tokens": response.usage.completion_tokens if response.usage else 0,
					"total_tokens": response.usage.total_tokens if response.usage else 0
				}
			}

			db_data = {"status": "Completed", "result": result}
			end_db_add(query, db_data=db_data)

		except Exception as e:
			error = {
				"error": str(e),
				"iserror": True,
				"error_traceback": traceback.format_exc(),
				"context": None,
			}
			raw = error
			db_data = {"status": "Failed", "error_message": error}
			end_db_add(query, db_data=db_data)

		return raw

 



 

 
 