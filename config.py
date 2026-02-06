"""
应用配置与 API 相关持久化
"""
import os
import json
import base64
import logging
from typing import Dict, Any

CONFIG_PATH = os.path.join(os.path.expanduser("~"), ".deepseek_config.json")

# 模板目录：放在项目根目录下，随项目一起迁移/备份
_PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(_PROJECT_ROOT, "templates")

# 默认 API 配置（硅基流动，模型名可自由修改）
DEFAULT_BASE_URL = "https://api.siliconflow.cn/v1"
DEFAULT_MODEL = "THUDM/GLM-4-9B-0414"


def encode_key(key: str) -> str:
    return base64.b64encode(key.encode("utf-8")).decode("utf-8")


def decode_key(data: str) -> str:
    try:
        return base64.b64decode(data.encode("utf-8")).decode("utf-8")
    except Exception:
        return ""


def _read_raw_config() -> Dict[str, Any]:
    if not os.path.exists(CONFIG_PATH):
        return {}
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _write_raw_config(data: Dict[str, Any]) -> None:
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logging.error(f"保存配置失败：{e}")


# === 多 API Profile 支持 ===

def save_api_profile(
    profile_id: str,
    api_key: str,
    base_url: str,
    model: str,
    set_current: bool = True,
) -> None:
    """
    为指定 profile 保存一份独立配置：
    - profile_id: 例如 "siliconflow"
    - api_key: 明文 key，将以 base64 存储
    - base_url / model: 平台与模型
    """
    data = _read_raw_config()
    profiles = data.get("profiles", {})
    profiles[profile_id] = {
        "api_key": encode_key(api_key) if api_key else "",
        "base_url": base_url,
        "model": model,
    }
    data["profiles"] = profiles
    if set_current:
        data["current_profile"] = profile_id
    _write_raw_config(data)


def load_api_profile(
    profile_id: str,
    default_base_url: str = DEFAULT_BASE_URL,
    default_model: str = DEFAULT_MODEL,
) -> Dict[str, str]:
    """
    读取指定 profile 的配置，若不存在则回落到全局配置 / 默认值。
    返回字段：api_key, base_url, model（api_key 已解码）
    """
    data = _read_raw_config()
    profiles = data.get("profiles", {})
    p = profiles.get(profile_id)

    # 若尚未为该 profile 单独保存配置，则兼容旧字段
    if not p:
        api_key = ""
        if "api_key" in data:
            api_key = decode_key(data.get("api_key", ""))
        base_url = data.get("base_url", default_base_url)
        model = data.get("model", default_model)
        return {
            "api_key": api_key,
            "base_url": base_url,
            "model": model,
        }

    api_key = ""
    if p.get("api_key"):
        api_key = decode_key(p.get("api_key", ""))
    base_url = p.get("base_url", default_base_url)
    model = p.get("model", default_model)
    return {
        "api_key": api_key,
        "base_url": base_url,
        "model": model,
    }


def load_current_profile_id(default_id: str) -> str:
    """
    读取当前选中的 profile id，若不存在则返回默认值。
    """
    data = _read_raw_config()
    return data.get("current_profile", default_id)


# === 兼容旧接口：保留单一配置读写 ===

def save_api_config(api_key: str, base_url: str, model: str) -> None:
    """
    兼容旧逻辑：保存一份“全局”配置，同时将其作为 current_profile 写入。
    默认使用 profile_id = "default"。
    """
    save_api_profile("default", api_key, base_url, model, set_current=True)


def load_api_config() -> Dict[str, str]:
    """
    兼容旧逻辑：读取当前 profile 配置，若没有则回落到默认。
    """
    data = _read_raw_config()
    profile_id = data.get("current_profile", "default")
    return load_api_profile(profile_id, DEFAULT_BASE_URL, DEFAULT_MODEL)


def save_api_key(key: str) -> None:
    """
    兼容旧接口：仅保存 API Key 到 default profile。
    """
    save_api_config(key, DEFAULT_BASE_URL, DEFAULT_MODEL)


def load_api_key() -> str:
    """
    兼容旧接口：仅返回当前 profile 的 API Key。
    """
    cfg = load_api_config()
    return cfg.get("api_key", "")


def clear_api_profile(profile_id: str) -> None:
    """
    清除指定 profile 的 API 配置（删除保存的 API Key）。
    - profile_id: 要清除的 profile id
    """
    data = _read_raw_config()
    profiles = data.get("profiles", {})
    if profile_id in profiles:
        # 清除该 profile 的 api_key，保留 base_url 和 model
        profiles[profile_id]["api_key"] = ""
        data["profiles"] = profiles
        _write_raw_config(data)


# === 并发设置 ===

DEFAULT_MAX_WORKERS = 20


def save_max_workers(max_workers: int) -> None:
    """
    保存并发线程数设置。
    - max_workers: 最大并发线程数（1-100）
    """
    max_workers = max(1, min(100, max_workers))  # 限制在 1-100 之间
    data = _read_raw_config()
    data["max_workers"] = max_workers
    _write_raw_config(data)


def load_max_workers() -> int:
    """
    读取并发线程数设置，默认返回 20。
    """
    data = _read_raw_config()
    max_workers = data.get("max_workers", DEFAULT_MAX_WORKERS)
    # 确保返回值在合理范围内
    return max(1, min(100, max_workers))

