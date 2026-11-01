"""Apply plain-SQL migrations with the admin role and provision the non-superuser app role.

The app role name and password are taken from DATABASE_URL so there is a single source of truth.
"""

import logging
from pathlib import Path

import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict

from app.core.config import get_settings

MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "migrations"
APP_ROLE = "brisamar_app"

logger = logging.getLogger(__name__)


def _ensure_app_role(conn: psycopg.Connection, password: str) -> None:
    exists = conn.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (APP_ROLE,)).fetchone()
    verb = sql.SQL("ALTER") if exists else sql.SQL("CREATE")
    conn.execute(
        sql.SQL("{} ROLE {} LOGIN NOSUPERUSER NOBYPASSRLS PASSWORD {}").format(
            verb, sql.Identifier(APP_ROLE), sql.Literal(password)
        )
    )


def run_migrations() -> list[str]:
    settings = get_settings()
    app_conninfo = conninfo_to_dict(settings.database_url)
    if app_conninfo.get("user") != APP_ROLE:
        raise RuntimeError(f"DATABASE_URL must connect as '{APP_ROLE}'")
    applied: list[str] = []
    with psycopg.connect(settings.database_admin_url, autocommit=True) as conn:
        conn.execute("SELECT pg_advisory_lock(hashtext('brisamar_migrations'))")
        try:
            _ensure_app_role(conn, str(app_conninfo.get("password", "")))
            conn.execute(
                "CREATE TABLE IF NOT EXISTS schema_migrations ("
                "name text PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now())"
            )
            done = {row[0] for row in conn.execute("SELECT name FROM schema_migrations")}
            for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
                if path.name in done:
                    continue
                with conn.transaction():
                    conn.execute(path.read_text(encoding="utf-8"))
                    conn.execute("INSERT INTO schema_migrations (name) VALUES (%s)", (path.name,))
                applied.append(path.name)
                logger.info("migration applied", extra={"migration": path.name})
        finally:
            conn.execute("SELECT pg_advisory_unlock(hashtext('brisamar_migrations'))")
    return applied


if __name__ == "__main__":
    from app.observability.logging import configure_logging

    configure_logging()
    names = run_migrations()
    logger.info("migrations complete", extra={"applied": names})
