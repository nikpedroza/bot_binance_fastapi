from pydantic import BaseModel, ConfigDict

#HACER HACER
class UserResponse(BaseModel):
    username: str
    model_config = ConfigDict(from_attributes=True)