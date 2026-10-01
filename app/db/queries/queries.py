import pathlib

import aiosql

# Все запросы хранятся в .sql-файлах и превращаются aiosql в async-методы.
# aiosql ≥ 12 требует явную сигнатуру параметров в имени запроса: «-- name: get-user(email)^».
queries = aiosql.from_path(pathlib.Path(__file__).parent / "sql", "asyncpg")
