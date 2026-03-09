from injector import inject
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.db.models.role import RoleModel
from app.repositories.db_repository import DbRepository
from app.schemas.role import RoleCreate


@inject
class RolesRepository(DbRepository[RoleModel]):
    def __init__(self, db: AsyncSession):
        super().__init__(RoleModel, db)

    async def create_role(self, role: RoleCreate):
        new_role = RoleModel(**role.model_dump())
        return await self.create(new_role)

    async def get_all_by_ids(self, ids: list[int]) -> list[RoleModel]:
        result = await self.db.execute(select(RoleModel).where(RoleModel.id.in_(ids)))
        return result.scalars().all()

    async def get_by_name(self, name: str) -> RoleModel:
        result = await self.db.execute(select(RoleModel).where(RoleModel.name == name))
        return result.scalars().first()
