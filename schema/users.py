from pydantic import BaseModel, ConfigDict

class UserResponse(BaseModel):
    username: str
    model_config = ConfigDict(from_attributes=True)