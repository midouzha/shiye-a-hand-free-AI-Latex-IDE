from pathlib import Path
from typing import Any


def get_openai_client() -> Any:
    """Return the OpenAI client configured in call_example.py.

    The repository root call_example.py is the single source of truth for
    the api_key and base_url used by Step3 generation requests.
    """
    from call_example import client

    return client
