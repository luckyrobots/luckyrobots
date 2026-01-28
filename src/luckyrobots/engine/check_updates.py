"""
Check for LuckyEngine executable updates.

This module compares local and remote file structures to detect changes.
"""

import json
import logging
import mimetypes
import os
import platform
import re
import sys
import zlib
from typing import Optional
from urllib.parse import urljoin

import requests

logger = logging.getLogger("luckyrobots.engine.check_updates")

BASE_URL = "https://builds.luckyrobots.xyz/"


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


def calculate_crc32(file_path: str) -> int:
    """
    Calculate CRC32 checksum for a file.

    Args:
        file_path: Path to the file.

    Returns:
        CRC32 checksum as unsigned 32-bit integer.
    """
    crc32 = 0
    with open(file_path, "rb") as file:
        while True:
            data = file.read(65536)  # Read in 64kb chunks
            if not data:
                break
            crc32 = zlib.crc32(data, crc32)
    return crc32 & 0xFFFFFFFF  # Ensure unsigned 32-bit integer


def scan_directory(root_path: str) -> list[dict]:
    """
    Scan a directory and create a file structure representation.

    Args:
        root_path: Root directory to scan.

    Returns:
        List of dictionaries containing file/directory metadata.
    """
    file_structure = []

    for dirpath, dirnames, filenames in os.walk(root_path):
        # Add directories
        for dirname in dirnames:
            dir_path = os.path.join(dirpath, dirname)
            relative_path = os.path.relpath(dir_path, root_path)
            file_structure.append(
                {
                    "path": relative_path,
                    "type": "directory",
                    "size": 0,
                    "mtime": os.path.getmtime(dir_path),
                    "crc32": 0,
                    "mime_type": "directory",
                }
            )

        # Add files
        for filename in filenames:
            file_path = os.path.join(dirpath, filename)
            relative_path = os.path.relpath(file_path, root_path)
            file_stat = os.stat(file_path)

            # Guess the file type using mimetypes
            file_type, _ = mimetypes.guess_type(file_path)
            if file_type is None:
                file_type = "application/octet-stream"

            file_structure.append(
                {
                    "path": relative_path,
                    "crc32": calculate_crc32(file_path),
                    "size": file_stat.st_size,
                    "mtime": file_stat.st_mtime,
                    "type": "file",
                    "mime_type": file_type,
                }
            )

    return file_structure


def save_json(data: dict, filename: str) -> None:
    """Save data to a JSON file."""
    with open(filename, "w") as f:
        json.dump(data, f, indent=2)


def load_json(filename: str) -> dict:
    """Load data from a JSON file."""
    with open(filename, "r") as f:
        return json.load(f)


def clean_path(path: str) -> tuple[str, Optional[str]]:
    """
    Clean and parse a path string.

    Args:
        path: Path string to clean.

    Returns:
        Tuple of (directory_path, attribute_name).
    """
    # Remove ['children'] and quotes, replace '][' with '/'
    cleaned = re.sub(r"\['children'\]", "", path).replace("']['", "/").strip("[]'")
    # Replace remaining single quotes with nothing
    cleaned = cleaned.replace("'", "")
    # Split the path and the attribute that changed
    parts = cleaned.rsplit("/", 1)
    return parts[0], parts[1] if len(parts) > 1 else None


def compare_structures(
    client_structure: list[dict], server_structure: list[dict]
) -> list[dict]:
    """
    Compare two file structures and return list of changes.

    Args:
        client_structure: Local file structure.
        server_structure: Remote file structure.

    Returns:
        List of changes (new, modified, deleted files).
    """
    dict1 = {item["path"]: item for item in client_structure}
    dict2 = {item["path"]: item for item in server_structure}

    result = []

    # Check for new and modified items
    for path, item in dict2.items():
        if path not in dict1:
            item["change_type"] = "new_file"
            result.append(item)
        elif item["type"] == "file" and item["crc32"] != dict1[path]["crc32"]:
            item["change_type"] = "modified"
            result.append(item)

    # Check for deleted items
    for path, item in dict1.items():
        if path not in dict2:
            item["change_type"] = "deleted"
            result.append(item)

    # Remove hashmap.json from changes (it's metadata)
    result = [item for item in result if item["path"] != "hashmap.json"]

    return result


def scan_server(server_path: str) -> None:
    """
    Scan server directory structure and save hashmap files.

    Args:
        server_path: Path to server root directory.
    """
    mac_path = os.path.join(server_path, "mac")
    win_path = os.path.join(server_path, "win")
    linux_path = os.path.join(server_path, "linux")

    mac_structure = scan_directory(mac_path)
    win_structure = scan_directory(win_path)
    linux_structure = scan_directory(linux_path)

    save_json(mac_structure, os.path.join(server_path, "mac/hashmap.json"))
    save_json(win_structure, os.path.join(server_path, "win/hashmap.json"))
    save_json(linux_structure, os.path.join(server_path, "linux/hashmap.json"))


def check_updates(root_path: str, base_url: Optional[str] = None) -> list[dict]:
    """
    Check for updates by comparing local and remote file structures.

    Args:
        root_path: Local root directory to check.
        base_url: Base URL for remote server (uses default if None).

    Returns:
        List of changes detected.
    """
    if base_url is None:
        base_url = BASE_URL

    os_type = get_os_type()
    url = urljoin(base_url, f"{os_type}/hashmap.json")

    # Download the JSON file
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        server_structure = response.json()
    except requests.RequestException as e:
        logger.warning(f"Error downloading JSON file: {e}")
        server_structure = None

    if server_structure is None:
        logger.info("Using local scan as no remote file could be downloaded.")
        server_structure = {}

    # Scan the directory and create a new file structure
    client_structure = scan_directory(root_path)

    # Compare and return changes
    if server_structure:
        changes = compare_structures(client_structure, server_structure)
        return changes
    else:
        logger.info("No server structure available for comparison.")
        return []


if __name__ == "__main__":
    # This is used as a cron job on the main server to keep file structures up to date
    lr_server_root = None

    for arg in sys.argv:
        if arg.startswith("--lr-server-root="):
            lr_server_root = arg.split("=", 1)[1]
            break

    if lr_server_root:
        logger.info(f"Scanning server at {lr_server_root}")
        scan_server(lr_server_root)
    else:
        logger.error("--lr-server-root argument required")
