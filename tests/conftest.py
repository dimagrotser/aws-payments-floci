import os

# Importing a handler builds a boto3 client, and boto3 refuses to build one without a
# region. Set here so the unit tests need no real configuration.
os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
os.environ.setdefault("AWS_ACCESS_KEY_ID", "test")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "test")
