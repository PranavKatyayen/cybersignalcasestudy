"""Centralized config."""

import os
from dotenv import load_dotenv

load_dotenv()  # no-op in production if .env doesn't exist


class SnowflakeConfig:
    ACCOUNT = os.environ.get("SNOWFLAKE_ACCOUNT")
    USER = os.environ.get("SNOWFLAKE_USER")
    PASSWORD = os.environ.get("SNOWFLAKE_PASSWORD")
    ROLE = os.environ.get("SNOWFLAKE_ROLE", "ACCOUNTADMIN")
    WAREHOUSE = os.environ.get("SNOWFLAKE_WAREHOUSE", "CYBERSIGNAL_WH")
    DATABASE = os.environ.get("SNOWFLAKE_DATABASE", "CYBERSIGNAL")
    SCHEMA = os.environ.get("SNOWFLAKE_SCHEMA", "RAW")

    @classmethod
    def validate(cls):
        missing = [k for k in ["ACCOUNT", "USER", "PASSWORD"] if not getattr(cls, k)]
        if missing:
            raise RuntimeError(
                f"Missing required Snowflake config: {missing}. "
                f"Copy .env.example to .env and fill in real values."
            )


class AnthropicConfig:
    API_KEY = os.environ.get("ANTHROPIC_API_KEY")
