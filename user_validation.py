from typing import Optional
import re
from pydantic import BaseModel, EmailStr, ValidationError, validator

class DataValidation(BaseModel):
    username: Optional[str]
    nickname: Optional[str]
    password: Optional[str]
    gender: Optional[str]
    email: Optional[EmailStr]
    
    @validator('username', 'nickname', pre=True)
    def validate_names(cls, v):
        if v is None: return v  # 如果字段是可选的且未提供，直接返回
        if len(v) < 3:
            raise ValueError('Minimum 3 characters required')
        if len(v) > 20:
            raise ValueError('Maximum 20 characters')
        if not re.match(r"^[a-zA-Z0-9_]+$", v):
            raise ValueError('Can only consist of alphanumeric characters and underscores')
        return v
    
    @validator('password', pre=True)
    def validate_password(cls, v):
        if v is None: return v  # 同上
        if len(v) < 3:
            raise ValueError('Minimum 3 characters required')
        if len(v) > 20:
            raise ValueError('Maximum 20 characters')
        if not re.match(r"^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[^\da-zA-Z]).+$", v):
            raise ValueError('Password must include an uppercase letter, lowercase letter, number, and special symbol')
        return v


class Validation:
    @staticmethod
    def vali_data(data):
        try:
            result = DataValidation(**data)
            return {"validated":True,"data":result.dict(exclude_none=True)}
        except ValidationError as e:
            errors = e.errors()
            error_details = []
            for error in errors:
                field = "->".join(str(part) for part in error['loc']) 
                message = error['msg']
                error_details.append({"field":field,"error":message}) 
            return {"validated": False, "data": error_details}

#Using Examples : 
# userdata = {
#     "username": "testuser",
#     "nickname": "testnick",
#     "password": "Valid1@",
#     "gender": "male",
#     "email": "test@examplecn"
# }
# logindata = {
#     "username": "testuser!!",
#     "password": "Valid1@"
# }    
# result = Validation.vali_data(data=logindata)
# if result["validated"]:
#     print(result["data"])
# else:
#     print(result["data"])