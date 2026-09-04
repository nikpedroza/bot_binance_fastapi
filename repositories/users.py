from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone

from models import Users
from schema import UserLogin

class UsersRepository():
    def __init__(self, db: AsyncSession):
        self.db = db
    
    def _base_active_query(self) -> Users | None:
        return select(Users).where(Users.is_active == True)
    
    async def get_user(self, user: UserLogin):
        query = self._base_active_query().where(Users.username == user.username)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def update_last_login(self, user: Users):
        user.last_login = datetime.now(timezone.utc)
        await self.db.commit()