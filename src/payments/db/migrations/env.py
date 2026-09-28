from __future__ import annotations

from alembic import context
from sqlalchemy import create_engine

from payments.db.engine import database_url_from_env
from payments.db.models import Base

target_metadata = Base.metadata


def run_migrations_online() -> None:
    engine = create_engine(database_url_from_env())
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


def run_migrations_offline() -> None:
    context.configure(
        url=str(database_url_from_env()),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
