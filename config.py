"""
应用配置与 API Key 管理
"""
import os
import json
import base64
import logging

CONFIG_PATH = os.path.join(os.path.expanduser("~"), ".deepseek_config.json")
TEMPLATE_DIR = os.path.join(os.path.expanduser("~"), ".deepseek_templates")


def encode_key(key: str) -> str:
    return base64.b64encode(key.encode("utf-8")).decode("utf-8")


def decode_key(data: str) -> str:
    try:
        return base64.b64decode(data.encode("utf-8")).decode("utf-8")
    except Exception:
        return ""


def save_api_key(key: str) -> None:
    try:
        data = {"api_key": encode_key(key)}
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except Exception as e:
        logging.error(f"保存 API Key 失败：{e}")


def load_api_key() -> str:
    if not os.path.exists(CONFIG_PATH):
        return ""
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return decode_key(data.get("api_key", ""))
    except Exception:
        return ""
