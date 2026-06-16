#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Paradox 启动器下载信息解析
从 GitLink launch Release 获取当前安装包文件名与下载地址
"""

import re
import logging
import requests
from typing import Dict

from ..config import (
    DLC_API_URL,
    PARADOX_LAUNCHER_RELEASE_TAG,
    PARADOX_LAUNCHER_DOWNLOAD_BASE,
    PARADOX_LAUNCHER_FILENAME_PREFIX,
    REQUEST_TIMEOUT,
)

logger = logging.getLogger(__name__)

MIN_LAUNCHER_SIZE = 100 * 1024 * 1024
_LAUNCHER_VERSION_PATTERN = re.compile(
    rf"{re.escape(PARADOX_LAUNCHER_FILENAME_PREFIX)}-(\d+)_(\d+)\.exe$",
    re.IGNORECASE,
)


def _launcher_version_key(filename: str):
    """从文件名解析版本号用于排序，如 paradox-launcher-installer-2026_6.exe"""
    match = _LAUNCHER_VERSION_PATTERN.search(filename)
    if match:
        return (int(match.group(1)), int(match.group(2)))
    return (0, 0)


def launcher_size_tolerance(expected_size: int) -> int:
    """GitLink API 返回的文件大小可能与实际文件略有偏差，允许一定误差。"""
    if expected_size <= 0:
        return 0
    return max(8192, int(expected_size * 0.002))


def is_launcher_file_complete(local_size: int, expected_size: int = 0) -> bool:
    """判断本地启动器安装包是否可视为完整。"""
    if local_size < MIN_LAUNCHER_SIZE:
        return False
    if expected_size <= 0:
        return True
    return abs(local_size - expected_size) <= launcher_size_tolerance(expected_size)


def validate_launcher_download(downloaded: int, expected_size: int = 0):
    """校验下载结果，仅在明显不完整时抛出异常。"""
    if downloaded < MIN_LAUNCHER_SIZE:
        raise Exception("下载的文件大小异常，可能已损坏")
    if expected_size <= 0:
        return
    tolerance = launcher_size_tolerance(expected_size)
    if downloaded + tolerance < expected_size:
        raise Exception(f"下载不完整（{downloaded}/{expected_size} 字节）")
    if downloaded > expected_size + tolerance:
        raise Exception(f"下载大小异常（{downloaded}/{expected_size} 字节）")


def _parse_attachment_size(filesize_str) -> int:
    """将 GitLink API 返回的文件大小字符串转为字节数"""
    if not filesize_str:
        return 0

    match = re.search(r"([\d.]+)\s*(B|KB|MB|GB)", str(filesize_str), re.IGNORECASE)
    if not match:
        return 0

    size_value = float(match.group(1))
    unit = match.group(2).upper()

    if unit == "B":
        return int(size_value)
    if unit == "KB":
        return int(size_value * 1024)
    if unit == "MB":
        return int(size_value * 1024 * 1024)
    if unit == "GB":
        return int(size_value * 1024 * 1024 * 1024)
    return 0


def resolve_paradox_launcher_download() -> Dict[str, object]:
    """
    从 GitLink launch Release 解析当前 Paradox 启动器安装包信息。

    返回:
        dict: {"url": str, "filename": str, "size": int}

    抛出:
        Exception: 未找到可用安装包或 API 请求失败
    """
    timeout = (10, REQUEST_TIMEOUT)
    logger.info("正在从 GitLink 获取 Paradox 启动器安装包信息...")

    response = requests.get(DLC_API_URL, timeout=timeout)
    response.raise_for_status()
    data = response.json()

    release = None
    for item in data.get("releases", []):
        if item.get("tag_name") == PARADOX_LAUNCHER_RELEASE_TAG:
            release = item
            break

    if not release:
        raise Exception(
            f"未找到 tag 为 '{PARADOX_LAUNCHER_RELEASE_TAG}' 的 Release，"
            "请确认 GitLink 上已发布启动器资源"
        )

    candidates = []
    for attachment in release.get("attachments", []):
        filename = attachment.get("title", "")
        if not filename.lower().endswith(".exe"):
            continue
        if filename.startswith(PARADOX_LAUNCHER_FILENAME_PREFIX):
            candidates.append(attachment)

    if not candidates:
        raise Exception(
            f"launch Release 中未找到以 '{PARADOX_LAUNCHER_FILENAME_PREFIX}' 开头的安装包"
        )

    # 多个版本并存时，按版本号取最新（如 2026_6 > 2026_2）
    candidates.sort(key=lambda item: _launcher_version_key(item.get("title", "")), reverse=True)
    attachment = candidates[0]
    filename = attachment.get("title", "")

    attachment_url = attachment.get("url", "")
    if attachment_url:
        download_url = "https://gitlink.org.cn" + attachment_url
    else:
        download_url = PARADOX_LAUNCHER_DOWNLOAD_BASE + filename

    file_size = _parse_attachment_size(attachment.get("filesize", ""))

    logger.info(f"已解析启动器安装包: {filename}")
    return {
        "url": download_url,
        "filename": filename,
        "size": file_size,
    }
