from pathlib import Path
from typing import Any
from openai import OpenAI


def get_openai_client() -> Any:
    """Return the OpenAI client configured in call_example.py"""
    from call_example import client
    return client


def get_model_name() -> str:
    """从配置文件读取模型名称"""
    model_file = Path("model_config.txt")
    if model_file.exists():
        return model_file.read_text(encoding="utf-8").strip()
    return "deepseek-chat"


def has_config() -> bool:
    """检查是否已配置 API"""
    try:
        from call_example import client
        return True
    except Exception:
        return False
