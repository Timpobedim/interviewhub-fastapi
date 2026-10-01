"""Пул-заглушка: все «соединения» внутри теста — одно соединение в открытой транзакции.

После теста транзакция откатывается, поэтому тесты изолированы
и не требуют очистки таблиц, а репозитории работают с настоящим PostgreSQL.
"""

from types import TracebackType

from asyncpg import Connection
from asyncpg.pool import Pool
from asyncpg.transaction import Transaction


class FakeAsyncPGPool:
    def __init__(self, pool: Pool) -> None:
        self._pool = pool
        self._conn: Connection | None = None
        self._tx: Transaction | None = None

    @classmethod
    async def create_pool(cls, pool: Pool) -> "FakeAsyncPGPool":
        fake_pool = cls(pool)
        conn = await fake_pool._pool.acquire()
        tx = conn.transaction()
        await tx.start()
        fake_pool._conn = conn
        fake_pool._tx = tx
        return fake_pool

    async def close(self) -> None:
        assert self._tx is not None
        assert self._conn is not None
        await self._tx.rollback()
        await self._pool.release(self._conn)
        await self._pool.close()

    def acquire(self, *, timeout: float | None = None) -> "FakePoolAcquireContent":
        return FakePoolAcquireContent(self)


class FakePoolAcquireContent:
    def __init__(self, pool: FakeAsyncPGPool) -> None:
        self._pool = pool

    async def __aenter__(self) -> Connection:
        assert self._pool._conn is not None
        return self._pool._conn

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        return None
