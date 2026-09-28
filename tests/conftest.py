"""Boto3 refuses to build a client without a region, and importing the handler module
builds one. Setting these here keeps the unit tests free of any real configuration.
"""

import os

os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
os.environ.setdefault("AWS_ACCESS_KEY_ID", "test")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "test")
