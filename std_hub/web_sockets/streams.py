

import json
from typing import Any, List
from fastapi import WebSocket, WebSocketDisconnect
import websockets

from std_hub.utils import get_error_result





active_connections_log = {}



# Broadcast log to all connected WebSocket clients
async def broadcast_log(wsuid: str, log_entry: dict,active_connections:dict=active_connections_log):
    if wsuid in active_connections:
        for websocket in active_connections[wsuid]:
            try:
                await websocket.send_json(log_entry)
            except WebSocketDisconnect:
                active_connections[wsuid].remove(websocket)



# Function to send final_answer and prompt to the frontend (UI)
async def ask_for_feedback_n(wsuid: str, final_answer: Any, prompt: str = "", wait_for_res: bool = True, Type=None):
    print(f"\n🩺 Prompt: {prompt}")
    print(f"\n📋 Assistant Says: {final_answer}\n")
    
    if wait_for_res:
        response = input("🧑 Your response: ").strip()
        return {
            "client_id": wsuid + "__client",
            "feedback": response
        }
    return True

 