from pydantic import BaseModel
from typing import Type
from fastapi import Request
# initiate pydantic Models
class EnterRoom(BaseModel):
    username: str
    nickname: str
    gender: str
    avatar: str
    facelooks: str
    credits: str
    ai_role_name: str
    ainame: str
    is_uncensored: str
    is_live_char: bool
    clientID: str
    language: str

def as_form(cls: Type[BaseModel]):
    async def _as_form(request:Request):
        form = await request.form()
        return cls(**form)
    return _as_form

