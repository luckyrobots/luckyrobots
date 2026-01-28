"""
Download and update LuckyEngine executable files.

This module handles downloading updates and applying changes to the LuckyEngine binary.
"""

import logging
import os
import platform
from typing import Optional

import requests
from tqdm import tqdm

from .check_updates import check_updates

logger = logging.getLogger("luckyrobots.engine.download")

BASE_URL = "https://builds.luckyrobots.xyz/"


def get_base_url() -> str:
    """
    Get the base URL for downloads, checking local server first.

    Returns:
        Base URL string (local or remote).
    """
    local_url = "http://192.168.1.148/builds"
    remote_url = "https://builds.luckyrobots.xyz"

    try:
        response = requests.get(local_url, timeout=1)
        if response.status_code == 200:
            logger.info(f"Using local server: {local_url}")
            return local_url
    except requests.RequestException:
        pass

    logger.info(f"Using remote server: {remote_url}")
    return remote_url


def get_os_type() -> str:
    """
    Get the operating system type as a string.

    Returns:
        "mac", "win", or "linux"

    Raises:
        ValueError: If the OS is not supported.
    """
    os_type = platform.system().lower()
    if os_type == "darwin":
        return "mac"
    elif os_type == "windows":
        return "win"
    elif os_type == "linux":
        return "linux"
    else:
        raise ValueError(f"Unsupported operating system: {os_type}")


def apply_changes(changes: list[dict], binary_path: str = "./Binary") -> None:
    """
    Apply changes by downloading new/modified files and deleting removed files.

    Args:
        changes: List of change dictionaries with 'change_type', 'path', etc.
        binary_path: Base path where binary files are stored.
    """
    base_url = get_base_url()
    os_type = get_os_type()

    for item in changes:
        change_type = item.get("change_type")
        item_path = os.path.join(binary_path, item["path"])

        if change_type in ["modified", "new_file"]:
            if item.get("type") == "directory":
                # Create the directory
                os.makedirs(item_path, exist_ok=True)
                logger.debug(f"Created directory: {item_path}")
            else:
                # Handle file download with progress bar
                file_url = f"{base_url}{os_type}/{item['path']}"

                # Ensure the directory exists
                item_dir = os.path.dirname(item_path)
                os.makedirs(item_dir, exist_ok=True)

                # Download the file with progress bar
                try:
                    response = requests.get(file_url, stream=True, timeout=30)
                    response.raise_for_status()
                    total_size = int(response.headers.get("content-length", 0))

                    with open(item_path, "wb") as f, tqdm(
                        desc=f"{item['path'][:8]}...{item['path'][-16:]}",
                        total=total_size,
                        unit="iB",
                        unit_scale=True,
                        unit_divisor=1024,
                        ascii=" ▆",
                    ) as progress_bar:
                        for data in response.iter_content(chunk_size=1024):
                            size = f.write(data)
                            progress_bar.update(size)

                    logger.debug(f"Downloaded: {item_path}")
                except requests.RequestException as e:
                    logger.error(f"Error downloading {item_path}: {e}")

        elif change_type == "deleted":
            # Delete the file or directory
            try:
                if os.path.isdir(item_path):
                    os.rmdir(item_path)
                    logger.debug(f"Deleted directory: {item_path}")
                else:
                    os.remove(item_path)
                    logger.debug(f"Deleted file: {item_path}")
            except OSError as e:
                logger.error(f"Error deleting {item_path}: {e}")
