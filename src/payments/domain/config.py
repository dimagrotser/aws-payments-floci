from __future__ import annotations

import os
from decimal import Decimal

from payments.domain.fraud import Rules


def rules_from_env(env: dict[str, str] | None = None) -> Rules:
    env = os.environ if env is None else env
    defaults = Rules()

    if "BLOCKED_COUNTRIES" in env:
        blocked = frozenset(
            c.strip().upper() for c in env["BLOCKED_COUNTRIES"].split(",") if c.strip()
        )
    else:
        blocked = defaults.blocked_countries

    return Rules(
        max_amount=Decimal(env.get("MAX_AMOUNT", str(defaults.max_amount))),
        blocked_countries=blocked,
        velocity_limit=int(env.get("VELOCITY_LIMIT", defaults.velocity_limit)),
        velocity_window_minutes=int(
            env.get("VELOCITY_WINDOW_MINUTES", defaults.velocity_window_minutes)
        ),
    )
