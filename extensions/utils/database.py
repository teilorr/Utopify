from __future__ import annotations
import typing as t

import asqlite
import pathlib
import inspect

from enum import Enum

if t.TYPE_CHECKING:
    from types import TracebackType


__all__ = (
    "DataType",
    "Database",
)

if t.TYPE_CHECKING:
    SQLSerializable: t.TypeAlias = t.Union[t.Type[None], str, int, float, bytes]
else:
    SQLSerializable: tuple = (type(None), str, int, float, bytes)


FuncT = t.TypeVar("FuncT", bound=t.Callable[..., t.Any])


def copy_signature(origin: FuncT) -> t.Callable[[FuncT], FuncT]:
    def deco(func: FuncT) -> FuncT:
        sig = inspect.signature(origin)
        func.__signature__ = sig
        return origin

    return deco


class DataType(Enum):
    DATETIME_NOW = "TIMESTAMP DEFAULT (DATETIME('now', 'localtime'))"
    INTEGER = "INTEGER"
    NULL = "NULL"
    REAL = "REAL"
    TEXT = "TEXT"


class WhereClauseMixin:
    def __init__(self) -> None:
        super().__init__()
        self.where_clause: t.List[t.Tuple[str, t.Any]] = []

    def where(self, **conditions: t.Any) -> t.Self:
        self.where_clause.extend(conditions.items())
        return self

    def _generate_where_conditions(self) -> str:
        return " AND ".join(f"{column} = ?" for column, _ in self.where_clause)

    def _where_values(self) -> t.List[t.Any]:
        return [value for _, value in self.where_clause]


class SetClauseMixin:
    def __init__(self) -> None:
        super().__init__()
        self.set_clauses: t.List[t.Tuple[str, t.Any]] = []

    def set(self, **columns: t.Any) -> t.Self:
        self.set_clauses.extend(columns.items())
        return self

    def _generate_set_conditions(self) -> str:
        return ", ".join(f"{column} = ?" for column, _ in self.set_clauses)

    def _set_values(self) -> t.List[t.Any]:
        return [value for _, value in self.set_clauses]


class UpdateQuery(SetClauseMixin, WhereClauseMixin):
    def __init__(self, db: Database) -> None:
        super().__init__()
        self._db: Database = db
        self.set_clauses: t.List[t.Tuple[str, t.Any]] = []

    async def execute(self) -> int:
        if not self.set_clauses:
            raise ValueError("No columns provided to update.")

        if not self.where_clause:
            raise ValueError("No conditions provided to update.")

        set_conditions = self._generate_set_conditions()
        where_conditions = self._generate_where_conditions()

        update_query = f"UPDATE {self._db.table_name} SET {set_conditions} WHERE {where_conditions}"

        set_values = self._set_values()
        where_values = self._where_values()

        async with self._db._conn.cursor() as cr:
            await cr.execute(update_query, *[*set_values, *where_values])
            await self._db._conn.commit()
            rowcount = cr._cursor.rowcount
        return rowcount


class DeleteQuery(WhereClauseMixin):
    def __init__(self, db: Database) -> None:
        super().__init__()
        self._db: Database = db

    async def execute(self) -> int:
        if not self.where_clause:
            raise ValueError("No conditions provided for deletion.")

        where_conditions = self._generate_where_conditions()
        where_values = self._where_values()

        delete_query = f"DELETE FROM {self._db.table_name} WHERE {where_conditions}"

        async with self._db._conn.cursor() as cr:
            await cr.execute(delete_query, *where_values)
            await self._db._conn.commit()
            rowcount = cr._cursor.rowcount
        return rowcount


class FetchQuery(WhereClauseMixin):
    def __init__(self, db: Database) -> None:
        super().__init__()
        self._db: Database = db
        self.columns_to_fetch: t.List[str] = []

    def select(self, *columns: str) -> t.Self:
        self.columns_to_fetch.extend(columns)
        return self

    async def execute(self) -> list[asqlite.sqlite3.Row]:
        where_values: list[t.Any] = []

        columns = ", ".join(self.columns_to_fetch)
        select_query = f"SELECT {columns} FROM {self._db.table_name} "

        if self.where_clause:
            where_conditions = self._generate_where_conditions()
            where_values = self._where_values()
            select_query += f"WHERE {where_conditions}"

        async with self._db._conn.cursor() as cr:
            await cr.execute(select_query, *where_values)
            result = await cr.fetchall()

        return result


class CountQuery(WhereClauseMixin):
    def __init__(self, db: Database) -> None:
        super().__init__()
        self._db = db
        self.column_to_count: t.Optional[str] = None
        self.distinct: bool = False

    def count(self, column: str, distinct: bool = False) -> t.Self:
        self.column_to_count = column
        self.distinct = distinct
        return self

    def use_distinct(self, distinct: bool) -> t.Self:
        self.distinct = distinct
        return self

    async def execute(self) -> int:
        if self.column_to_count == "*" and self.distinct:
            raise ValueError(
                "Cannot count all columns while using DISTINCT at the same time."
            )

        where_values: list[t.Any] = []
        count_query = f"SELECT COUNT({'DISTINCT ' if self.distinct else ''}{self.column_to_count}) FROM {self._db.table_name} "

        if self.where_clause:
            where_conditions = self._generate_where_conditions()
            where_values = self._where_values()
            count_query += f"WHERE {where_conditions}"

        async with self._db._conn.cursor() as cr:
            await cr.execute(count_query, *where_values)
            count = (await cr.fetchone())[0]

        return count


class Database:
    _table_name: str
    _db_path: pathlib.Path
    _conn: asqlite.Connection
    _columns: dict[str, DataType]

    def __init__(self, table_name: str, *, columns: dict[str, DataType]) -> None:
        self._columns = columns

        self._table_name = table_name
        self._db_path = pathlib.Path("./data") / f"{table_name}.db"

        self._db_path.touch()

    async def _create_table(self, columns: dict[str, DataType]) -> None:
        definitions = [
            f"{name} {data_type.value}" for name, data_type in columns.items()
        ]

        query = (
            f"CREATE TABLE IF NOT EXISTS {self._table_name} ({', '.join(definitions)})"
        )

        async with self._conn.cursor() as cr:
            await cr.execute(query)
            await self._conn.commit()

    async def __aenter__(self) -> t.Self:
        self._conn = await asqlite.connect(
            database=self._db_path.as_posix(),
            detect_types=asqlite.PARSE_DECLTYPES,
        ).__aenter__()

        await self._create_table(self._columns)
        return self

    async def __aexit__(
        self,
        exc_type: t.Type[BaseException],
        exc_value: BaseException,
        traceback: TracebackType,
    ) -> None:
        return await self._conn.__aexit__(
            exc_type=exc_type,
            exc_value=exc_value,
            traceback=traceback,
        )

    @property
    def table_name(self) -> str:
        return self._table_name

    @table_name.setter
    def table_name(self, value: str) -> None:
        raise TypeError("Cannot overwrite the table_name property")

    def _is_sqlite_serializable(self, obj: t.Any) -> t.TypeGuard[SQLSerializable]:
        return isinstance(obj, SQLSerializable)  # type: ignore # SQLSerializable is a tuple at runtime

    async def insert(self, **kwds: t.Any) -> dict[str, t.Any]:
        if not kwds:
            raise ValueError("No values provided for insertion")

        # fmt: off
        has_unserializable = any([
            not self._is_sqlite_serializable(obj) 
            for obj in kwds.values()
        ])
        # fmt: on

        if has_unserializable:
            raise ValueError("You provided a non-serializable object to be stored")

        keys = tuple(kwds.keys())
        values = tuple(kwds.values())

        placeholders = ", ".join("?" for _ in keys)
        columns = ", ".join(keys)

        query = f"INSERT INTO {self._table_name} ({columns}) VALUES ({placeholders})"

        async with self._conn.cursor() as cr:
            await cr.execute(query, values)
            await self._conn.commit()

        return kwds

    def update(self, **columns: t.Any) -> UpdateQuery:
        if not columns:
            raise ValueError("No columns provided to update.")

        return UpdateQuery(self).set(**columns)

    def delete_where(self, **conditions: t.Any) -> DeleteQuery:
        if not conditions:
            raise ValueError("No conditions provided for deletion.")

        return DeleteQuery(self).where(**conditions)

    @t.overload
    def select(self, *columns: t.Literal["*"]) -> FetchQuery:
        ...

    @t.overload
    def select(self, *columns: str) -> FetchQuery:
        ...

    def select(self, *columns: str) -> FetchQuery:
        if not columns:
            raise ValueError("No columns provided for fetching.")

        return FetchQuery(self).select(*columns)

    @copy_signature(select)
    def fetch(self, *columns):
        return self.select(*columns)

    def count(
        self,
        column: t.Literal["*"] | str,
        *,
        distinct: bool = False,
    ) -> CountQuery:
        if not column:
            raise ValueError("No column provided for counting.")

        return CountQuery(self).count(column, distinct=distinct)
