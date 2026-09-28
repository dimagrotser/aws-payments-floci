from __future__ import annotations

import json
import os
from collections.abc import Iterator
from contextlib import contextmanager
from functools import cache

import boto3
from sqlalchemy import Engine, create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import Session


def load_credentials(secret_id: str | None = None) -> dict:
    secret_id = secret_id or os.environ["DB_SECRET_ARN"]
    client = boto3.client("secretsmanager")
    return json.loads(client.get_secret_value(SecretId=secret_id)["SecretString"])


def database_url(credentials: dict, host: str | None = None) -> URL:
    return URL.create(
        "postgresql+pg8000",
        username=credentials["username"],
        password=credentials["password"],
        host=host or credentials["host"],
        port=int(credentials["port"]),
        database=credentials["dbname"],
    )


def database_url_from_env() -> URL:
    return database_url(load_credentials(), os.environ.get("DB_HOST"))


@cache
def get_engine() -> Engine:
    return create_engine(
        database_url_from_env(),
        pool_pre_ping=True,
        pool_size=1,
        max_overflow=0,
    )


@contextmanager
def session_scope() -> Iterator[Session]:
    with Session(get_engine()) as session, session.begin():
        yield session
