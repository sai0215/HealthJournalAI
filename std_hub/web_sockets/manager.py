
from typing import Dict
from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str,WebSocket] = {}
    
    async def connect(self,client_id:str, websocket: WebSocket,):
        await websocket.accept()
        print(f"{self.__class__.__name__} : client id : {client_id} got connected")
        self.active_connections[client_id] = websocket

    def disconnect(self,client_id):
        if client_id in self.active_connections:
            print(f"{self.__class__.__name__} : client id : {client_id} got removed")
            del self.active_connections[client_id]

    async def send_personal_message(self,client_id:str, message: str, ):
        if client_id in self.active_connections:
            print(f"{self.__class__.__name__} : message is transported to client id : {client_id} ")
            connection = self.active_connections[client_id]
            await connection.send_text(message)
        else:
            print(f"{self.__class__.__name__} : client id : {client_id} is not alive")
    
    async def broadcast(self, message: str):
        for client_id,connection in self.active_connections.items():
            print(f"{self.__class__.__name__} : message is broadcasted to client id : {client_id} ")
            await connection.send_text(message)