from pathlib import Path
from typing import Any
from openai import OpenAI


def get_openai_client() -> Any:
    from call_example import client
    return client


def get_model_name() -> str:
    """从配置文件读取模型名称"""
    model_file = Path("model_config.txt")
    if model_file.exists():
        return model_file.read_text(encoding="utf-8").strip()
    return "deepseek-chat"
