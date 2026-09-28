from payments.db.engine import database_url

CREDENTIALS = {
    "engine": "postgres",
    "host": "floci",
    "port": 7001,
    "dbname": "payments",
    "username": "payments",
    "password": "s3cr#t/with:characters",
}


def test_builds_a_pg8000_url_from_the_secret():
    url = database_url(CREDENTIALS)

    assert url.drivername == "postgresql+pg8000"
    assert url.host == "floci"
    assert url.port == 7001
    assert url.database == "payments"


def test_the_host_can_be_overridden():
    # Floci advertises a hostname only containers can resolve, so anything running on the
    # host keeps the port from the secret and replaces the name.
    url = database_url(CREDENTIALS, host="localhost")

    assert url.host == "localhost"
    assert url.port == 7001


def test_a_password_with_punctuation_survives_the_round_trip():
    url = database_url(CREDENTIALS)

    assert url.password == "s3cr#t/with:characters"
    assert "s3cr#t" not in str(url), "rendering a URL should not leak the password"
