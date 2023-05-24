from __future__ import annotations
import typing as t

from types import TracebackType

from collections import defaultdict
import random
import string

import asqlite
import datetime

__all__ = ("MarkovModel",)


Chain: t.TypeAlias = defaultdict[str, list[str]]


if t.TYPE_CHECKING:

    class MarkovDBRow(asqlite.sqlite3.Row):
        @t.overload
        def __getitem__(self, __key: t.Literal[0]) -> str:
            ...

        @t.overload
        def __getitem__(self, __key: t.Literal[1]) -> datetime.datetime:
            ...

        def __getitem__(self, *args: object) -> t.Any:
            ...


class DBProtocol(t.Protocol):
    async def __aenter__(self) -> t.Self:
        ...

    async def __aexit__(
        self,
        exc_type: t.Type[BaseException],
        exc_value: BaseException,
        traceback: TracebackType,
    ) -> None:
        ...

    async def add_message(self, msg: str) -> None:
        ...

    async def fetch_messages(self) -> t.Optional[list[MarkovDBRow]]:
        ...

    async def trim_messages(
        self,
        *,
        before: t.Union[datetime.datetime, datetime.timedelta],
    ) -> None:
        ...


class MarkovDB(DBProtocol):
    def __init__(self) -> None:
        self._first_enter = True

    async def __aenter__(self) -> t.Self:
        self.conn = conn = await asqlite.connect(
            database="./data/markov.db",
            detect_types=asqlite.PARSE_DECLTYPES,
        ).__aenter__()

        if self._first_enter:
            async with conn.cursor() as cr:
                query = """
                CREATE TABLE IF NOT EXISTS messages (
                    message TEXT,
                    timestamp TIMESTAMP DEFAULT (
                        DATETIME('now', 'localtime')
                    )
                )
                """
                await cr.execute(query)
                await conn.commit()

        self._first_enter = False
        return self

    async def __aexit__(
        self,
        exc_type: t.Type[BaseException],
        exc_value: BaseException,
        traceback: TracebackType,
    ) -> None:
        await self.conn.__aexit__(exc_type, exc_value, traceback)

    async def add_message(self, msg: str) -> None:
        msg = msg.lower()
        async with self.conn.cursor() as cr:
            await cr.execute("INSERT INTO messages (message) VALUES (?)", (msg,))
            await self.conn.commit()

    async def fetch_messages(self) -> t.Optional[list[MarkovDBRow]]:
        async with self.conn.cursor() as cr:
            await cr.execute("SELECT * FROM messages")
            messages = await cr.fetchall()

            if not messages:
                return None

            return messages  # type: ignore

    async def trim_messages(
        self,
        *,
        before: t.Union[datetime.datetime, datetime.timedelta],
    ) -> None:
        """
        Trims messages stored in the database before a specified datetime or timedelta.

        Parameters:
        ----------
            before (`Union[datetime.datetime, datetime.timedelta]`):
                A datetime or timedelta object specifying the threshold for trimming messages.

                . If a datetime object is provided, messages older than that datetime will be deleted.

                . If a timedelta object is provided, messages older than timedelta from the current datetime will be deleted.

        Raises:
        -------
            `ValueError`: If an invalid 'before' argument is provided.
        """
        if isinstance(before, datetime.timedelta):
            threshold_datetime = datetime.datetime.now() - before

        elif isinstance(before, datetime.datetime):
            threshold_datetime = before

        else:
            raise ValueError(
                "Invalid 'before' argument. Expected datetime.datetime or datetime.timedelta."
            )

        async with self.conn.cursor() as cr:
            await cr.execute(
                "DELETE FROM messages WHERE timestamp < ?",
                (threshold_datetime,),
            )
            await self.conn.commit()


class MarkovModel:
    db: DBProtocol

    def __init__(self, db: t.Optional[DBProtocol] = None) -> None:
        if db is None:
            db = MarkovDB()

        self.db = db

    def _process_text(self, body: str) -> str:
        body = body.translate(
            str.maketrans("", "", string.punctuation),
        )
        return body

    def _create_chain(self, words: list[str], state_size: int = 1) -> Chain:
        chain: Chain = defaultdict(list)

        for current_state, next_word in zip(words, words[state_size:]):
            if next_word not in chain[current_state]:
                chain[current_state].append(next_word)

        return chain

    def _generate_text(self, chain: Chain, n_words: int) -> str:
        first_word = random.choice(list(chain.keys()))
        generated_words = [first_word]

        for _ in range(n_words - 1):
            current_word = generated_words[-1]
            if not chain.get(current_word):
                continue

            next_word = random.choice(chain[current_word])
            generated_words.append(next_word)

        return " ".join(generated_words)

    async def generate_text(self, input: str, n_words: int) -> str:
        """Generates a text based on the given input and the messages stored in the database.

        Parameters:
        -----------
            input (`str`): The input text to use as a starting point for generating the text.
            n_words (`int`): The number of words to generate in the output text.

        Returns:
        --------
            `str`: The generated text based on the input and the database messages.

        Raises:
        -------
            `ValueError`: If the database does not contain any entries.

        """        
        text = self._process_text(input)
        words = text.lower().split(" ")

        rows = await self.fetch_messages()
        if rows is None:
            raise ValueError("The database does not contains any entries")

        for row in rows:
            words.extend(row[0].split(" "))

        chain = self._create_chain(words)

        ret = self._generate_text(chain, n_words)
        del chain
        return ret

    async def store_message(self, msg: str):
        async with self.db as db:
            await db.add_message(msg)

    async def fetch_messages(self):
        async with self.db as db:
            result = await db.fetch_messages()

        await self.trim_messages(before=datetime.timedelta(days=1))
        return result

    async def trim_messages(
        self,
        *,
        before: t.Union[datetime.datetime, datetime.timedelta],
    ):
        async with self.db as db:
            return await db.trim_messages(before=before)
