# websocket connection manager , initiate active_connections (clients)
from fastapi import WebSocket,WebSocketDisconnect
from typing import Dict, List, Union
from contextlib import asynccontextmanager
from modules.FormatedLogger import logger as logging
class ChatUnit:
    def __init__(self,websocket:WebSocket,room:object=None) -> None:
        self.websocket = websocket
        self.room = room
        

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, ChatUnit] = {}
        
    @asynccontextmanager
    async def connect(self, client_id:str, websocket: WebSocket):
        await websocket.accept()
        if client_id in self.active_connections:
            logging.info("client has in the active connections")
            chat_unit = self.active_connections.get(client_id)
            chat_unit.websocket = websocket
        else:
            self.active_connections[client_id] = ChatUnit(websocket)
        try:
            yield
        finally:
            pass
        
    async def getdata(self, client_id:str):
        data =  await self.active_connections[client_id].websocket.receive_json()
        return data

    async def disconnect(self, client_id:str):
        # need to add a delay method
        # chat_unit = self.active_connections.pop(client_id,None)
        # if chat_unit:
        #     if chat_unit.websocket:
        #         try:
        #             await chat_unit.websocket.close()
        #         except RuntimeError:
                    pass

    async def send_personal_message(self, client_id:str, data:Union[List,Dict,str]):
        chat_unit = self.active_connections.get(client_id)
        if chat_unit:
            if chat_unit.websocket:
                await chat_unit.websocket.send_json(data)

    async def broadcast(self, message: str):
        disconnected_clients = []
        for client_id, chat_unit in self.active_connections.items():
            try:
                await chat_unit.websocket.send_text(message)
            except WebSocketDisconnect:
                disconnected_clients.append(client_id)
        for client_id in disconnected_clients:
            await self.disconnect(client_id)
            
    async def cleanup(self):
        disconnected_clients = []
        for client_id, chat_unit in self.active_connections.items():
            try:
                await chat_unit.websocket.send_text("Cleaning Up Websocket...")
            except WebSocketDisconnect:
                disconnected_clients.append(client_id)
        for client_id in disconnected_clients:
            chat_unit = self.active_connections.pop(client_id,None)
            if chat_unit:
                if chat_unit.websocket:
                    try:
                        await chat_unit.websocket.close()
                    except RuntimeError:
                        pass
            
    def set_room(self,client_id:str,room:object):
        chat_unit = self.active_connections.get(client_id)
        if chat_unit:
            chat_unit.room = room
        else:
            logging.info(f"Client {client_id} does not exist.")
            
    def get_room(self, client_id: str):
        chat_unit = self.active_connections.get(client_id)
        if chat_unit:
            if chat_unit.room != None:
                return chat_unit.room
            else:
                return False
        else:
            logging.info(f"Client {client_id} does not exist.")