from decimal import Decimal

from payments.domain.config import rules_from_env
from payments.domain.fraud import Rules


def test_falls_back_to_the_defaults():
    assert rules_from_env({}) == Rules()


def test_reads_every_threshold_from_the_environment():
    rules = rules_from_env(
        {
            "MAX_AMOUNT": "250",
            "BLOCKED_COUNTRIES": "ru, by ,KP",
            "VELOCITY_LIMIT": "2",
            "VELOCITY_WINDOW_MINUTES": "60",
        }
    )

    assert rules.max_amount == Decimal("250")
    assert rules.blocked_countries == frozenset({"RU", "BY", "KP"})
    assert rules.velocity_limit == 2
    assert rules.velocity_window_minutes == 60


def test_an_empty_list_blocks_nothing():
    # Setting the variable to "" is a deliberate choice and has to survive, otherwise
    # nobody could turn the country rule off from Terraform.
    assert rules_from_env({"BLOCKED_COUNTRIES": ""}).blocked_countries == frozenset()
