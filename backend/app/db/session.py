from collections.abc import Iterator, Sequence
from contextlib import contextmanager

from pgvector.psycopg import register_vector
from psycopg import Connection
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from app.core.config import get_settings

_pool: ConnectionPool | None = None


def _configure(conn: Connection) -> None:
    register_vector(conn)


def get_pool() -> ConnectionPool:
    global _pool
    if _pool is None:
        _pool = ConnectionPool(
            get_settings().database_url,
            min_size=1,
            max_size=10,
            configure=_configure,
            kwargs={"row_factory": dict_row},
            open=True,
        )
    return _pool


def close_pool() -> None:
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None


@contextmanager
def scoped_transaction(business_lines: Sequence[str]) -> Iterator[Connection]:
    """Open a transaction whose Row Level Security scope is limited to ``business_lines``.

    ``set_config(..., true)`` is the function form of ``SET LOCAL``: the setting dies with the
    transaction, so a pooled connection never leaks one tenant's scope into the next request.
    """
    with get_pool().connection() as conn, conn.transaction():
        conn.execute(
            "SELECT set_config('app.business_lines', %s, true)", (",".join(business_lines),)
        )
        yield conn
