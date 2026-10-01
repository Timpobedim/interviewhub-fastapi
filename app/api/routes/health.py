from asyncpg.pool import Pool
from fastapi import APIRouter, Depends

from app.api.dependencies.database import _get_db_pool

router = APIRouter()


@router.get("", name="health:check")
async def health_check(pool: Pool = Depends(_get_db_pool)) -> dict[str, str]:
    async with pool.acquire() as connection:
        await connection.fetchval("SELECT 1")
    return {"status": "ok"}
