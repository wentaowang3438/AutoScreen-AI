"""
OpenAI / DeepSeek API 调用与 Excel 批处理逻辑
"""
import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, Tuple

import pandas as pd
from openai import OpenAI

from config import (
    save_api_config,
    load_api_config,
    DEFAULT_BASE_URL,
    DEFAULT_MODEL,
)

# 全局客户端与当前模型配置，由 init_client 设置
_client: Optional[OpenAI] = None
_base_url: str = DEFAULT_BASE_URL
_model: str = DEFAULT_MODEL


def init_client(api_key: str, base_url: Optional[str] = None, model: Optional[str] = None) -> OpenAI | None:
    """
    初始化并保存 API 客户端。
    - api_key: 用户输入的密钥
    - base_url: 可选，自定义接口地址；为空时使用默认
    - model: 可选，模型名称；为空时使用默认
    """
    global _client, _base_url, _model

    if not api_key or not api_key.strip():
        return None
    api_key = api_key.strip()

    if not base_url:
        base_url = DEFAULT_BASE_URL
    if not model:
        model = DEFAULT_MODEL

    _base_url = base_url
    _model = model

    # 持久化配置
    save_api_config(api_key, _base_url, _model)

    _client = OpenAI(api_key=api_key, base_url=_base_url)
    return _client


def restore_client_from_config() -> Tuple[Optional[OpenAI], str]:
    """
    根据本地配置文件恢复 client（用于程序启动时自动加载）。
    返回：(client 或 None, 当前模型名)
    """
    global _client, _base_url, _model
    cfg = load_api_config()
    api_key = cfg.get("api_key") or ""
    _base_url = cfg.get("base_url") or DEFAULT_BASE_URL
    _model = cfg.get("model") or DEFAULT_MODEL
    if not api_key:
        _client = None
        return None, _model
    try:
        _client = OpenAI(api_key=api_key, base_url=_base_url)
        return _client, _model
    except Exception as e:
        logging.warning(f"根据本地配置恢复 API Client 失败: {e}")
        _client = None
        return None, _model


def get_client() -> OpenAI | None:
    """返回当前客户端（供测试等使用）。"""
    return _client


def get_current_model() -> str:
    """返回当前使用的模型名称。"""
    return _model or DEFAULT_MODEL


def get_current_base_url() -> str:
    """返回当前使用的 base_url。"""
    return _base_url or DEFAULT_BASE_URL


def call_model(prompt: str, max_retries: int = 3) -> str:
    if _client is None:
        raise RuntimeError("Client 未初始化")

    backoff_base = 2
    for attempt in range(max_retries):
        try:
            resp = _client.chat.completions.create(
                model=_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
            )
            return (resp.choices[0].message.content or "").strip()
        except Exception as e:
            logging.warning(f"模型调用重试 ({attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(backoff_base**attempt)
            else:
                return ""
    return ""


def process_row(row_index, merged_text, delimiter, prompt_template, cache_key):
    prompt = prompt_template.replace("{merged_text}", merged_text).replace(
        "{delimiter}", delimiter
    )
    result = call_model(prompt)

    error = False
    error_msg = ""

    if not result:
        error = True
        error_msg = "API 返回空"
        result = f"FAIL{delimiter}FAIL"
    elif delimiter not in result:
        error = True
        error_msg = "缺少分隔符"
        result = f"FAIL{delimiter}FAIL"

    return {
        "index": row_index,
        "output": result,
        "cache_key": cache_key,
        "error": error,
        "error_msg": error_msg,
    }


def run_processing(
    input_path,
    cols,
    delimiter,
    output_path,
    prompt,
    progress_cb,
    log_cb,
    stop_flag,
    max_workers=20,
):
    try:
        df = pd.read_excel(input_path)
    except Exception as e:
        return False, f"读取 Excel 失败: {e}"

    df["AI_Output"] = ""
    total = len(df)
    cache = {}
    results = []
    error_rows = []
    done_cnt = 0

    log_cb(f"开始处理 {total} 行数据... (并发数: {max_workers})")

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        tasks = []
        for idx, row in df.iterrows():
            if stop_flag():
                break

            row_vals = []
            for c in cols:
                val = row.get(c, "")
                row_vals.append(str(val) if pd.notna(val) else "")

            merged_text = "\n".join(row_vals)
            key = f"{merged_text}|{delimiter}|{prompt}"

            if key in cache:
                cached = cache[key]
                r = {
                    "index": idx,
                    "output": cached["output"],
                    "cache_key": key,
                    "error": cached["error"],
                    "error_msg": cached["error_msg"],
                }
                results.append(r)
                if r["error"]:
                    error_rows.append(idx)
                done_cnt += 1
                progress_cb(done_cnt, total)
            else:
                future = pool.submit(
                    process_row, idx, merged_text, delimiter, prompt, key
                )
                tasks.append(future)

        for future in as_completed(tasks):
            if stop_flag():
                break
            r = future.result()
            results.append(r)
            cache[r["cache_key"]] = {
                "output": r["output"],
                "error": r["error"],
                "error_msg": r["error_msg"],
            }
            if r["error"]:
                error_rows.append(r["index"])
                log_cb(f"[警告] 行 {r['index']} 失败: {r['error_msg']}")

            done_cnt += 1
            progress_cb(done_cnt, total)

    for r in results:
        df.at[r["index"], "AI_Output"] = r["output"]

    try:
        df.to_excel(output_path, index=False)
        log_cb(f"文件已保存至: {output_path}")
    except Exception as e:
        return False, f"保存文件失败: {e}"

    processed_count = len(results)
    if stop_flag():
        return False, f"用户中断。处理 {processed_count}/{total} 行。"
    else:
        status = f"完成。共 {total} 行，失败 {len(error_rows)} 行。"
        return True, status
