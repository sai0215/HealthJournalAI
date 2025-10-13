 
from datetime import datetime,timezone
 
 
 
 
from std_hub.db.mongodb import db_client

# Handle case where MongoDB is not available
try:
    if db_client:
        db = db_client["flow_project"]
        col_projects = db["projects"]
        col_kickoffs = db["kickoffs"]
        # Create index with timeout handling
        try:
            col_kickoffs.create_index([('user_id', 1), ('kickoff_id', 1)])
        except Exception as e:
            print(f"Warning: Could not create MongoDB index: {e}")
    else:
        db = None
        col_projects = None
        col_kickoffs = None
except Exception as e:
    print(f"Warning: MongoDB connection failed: {e}")
    db = None
    col_projects = None
    col_kickoffs = None
 
 
# def log_data(data, project_id: str, user_id: str, kickoff_id: str, broadcast=False):
#     # Insert or update agent's configuration into the database
#     if broadcast:
#         print("connections:", streams.active_connections_log)
#         # Run the broadcast_log function asynchronously using asyncio.run
#         try :
#             asyncio.run(streams.broadcast_log(kickoff_id, data))
 
#         except Exception as e:
#             print("error : ",e)
#             print("log_entry : ",data)
   
#     return True  # Return some confirmation or the inserted data
 
    # Broadcast log to all connected WebSocket clients
   
 
 
# def get_log(query:dict, limit: int = 1000, skip: int = 0):
#     # Query the logs collection by user ID and request ID, sorted by timestamp
   
   
#     logs = col_kickoffs.find(
#         query
#     ).sort('timestamp', 1).skip(skip).limit(limit)
#     res= list(logs)
#     for i,r in enumerate(res):
#         # res[i]["_id"]= str(res[i]["_id"])
#         del(res[i]["_id"])
 
#     if not res:
#         return {"data":{},"entry":False}
#     else:
#         for data in res:
#             print("data :",data)
#         return {"data":data,"entry":True}
   
#     # Return logs as a list of dictionaries
   
 
def get_log(query:dict, limit: int = 1000, skip: int = 0):
    # Query the logs collection by user ID and request ID, sorted by timestamp
    if col_kickoffs is None:
        return {"data":{},"entry":False}
   
    logs = col_kickoffs.find(
        query)
    #).sort('timestamp', 1).skip(skip).limit(limit)
    res= list(logs)
    for i,r in enumerate(res):
        # res[i]["_id"]= str(res[i]["_id"])
        del(res[i]["_id"])

    if not res:
        return {"data":{},"entry":False}
    else:
        # for data in res:
        #     # print("data :",data)
        return {"data":res,"entry":True}
   
    # Return logs as a list of dictionaries
 
 
def get_kickoff_data(project_id: str, user_id: str,kickoff_id:str):
    query={
 
        "project_id": project_id,
        "user_id": user_id,
        "kickoff_id":kickoff_id,}
 
    res = get_log(query=query)
       
    return res
 
 
def get_kickoff_history(project_id: str, user_id: str,):
   
   
    query={  "project_id": project_id,
                "user_id": user_id,
                }
 
    res = get_log(query=query)
       
    return res
 
def start_db_add(db_data:dict):
    if col_kickoffs is None:
        print("MongoDB not available, skipping database insert")
        return None
    timestamp = datetime.now(timezone.utc)
    str_timestamp=str(timestamp)
    db_data["start_time"] = str_timestamp
    result = col_kickoffs.insert_one(db_data)
    print({"acknowledged":result.acknowledged} ) # Return some confirmation or the inserted data
    return result.inserted_id
 
def end_db_add(query:dict,db_data:dict):
    if col_kickoffs is None:
        print("MongoDB not available, skipping database update")
        return

    # Update operation
    timestamp = datetime.now(timezone.utc)
    str_timestamp = str(timestamp)
    db_data["end_time"]=str_timestamp
        # MongoDB query to find the document
    new_values = {"$set": db_data}

    # Update the document
    update_result = col_kickoffs.update_one(query, new_values)
   
    print({"acknowledged": update_result.acknowledged})