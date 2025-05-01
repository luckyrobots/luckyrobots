import os
import platform
import re
import sys
import zipfile
from datetime import datetime

import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

from .check_updates import check_updates

base_url = "https://builds.luckyrobots.xyz/"


def get_base_url():
    import requests
    from requests.exceptions import RequestException

    def is_server_active(url):
        try:
            response = requests.get(url, timeout=1)
            return response.status_code == 200
        except RequestException:
            return False

    local_url = "http://192.168.1.148/builds"
    remote_url = "https://builds.luckyrobots.xyz"

    if is_server_active(local_url):
        print("Using local server:", local_url)
        return local_url
    else:
        print("Using remote server:", remote_url)
        return remote_url


def get_os_type():
    os_type = platform.system().lower()
    if os_type == "darwin":
        return "mac"
    elif os_type == "windows":
        return "win"
    elif os_type == "linux":
        return "linux"
    else:
        raise ValueError(f"Unsupported operating system: {os_type}")


def apply_changes(changes):
    # Iterate through changes and handle each change type
    for item in changes:
        if item["change_type"] in ["modified", "new_file"]:
            # Check if the item is a directory
            if item.get("type") == "directory":
                # Create the directory
                item_path = os.path.join("./Binary", item["path"])
                os.makedirs(item_path, exist_ok=True)
                print(f"Created directory: {item_path}")
            else:
                # Handle file download with progress bar
                os_type = get_os_type()
                file_url = f"{base_url}{os_type}/{item['path']}"

                # Ensure the directory exists
                item_path = os.path.join("./Binary", item["path"])
                item_dir = os.path.dirname(item_path)
                os.makedirs(item_dir, exist_ok=True)

                # Download the file with progress bar
                try:
                    response = requests.get(file_url, stream=True)
                    response.raise_for_status()
                    total_size = int(response.headers.get("content-length", 0))
                    # " ▁▂▃▄▅▆▇█"
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
                    # print(f"Downloaded: {item_path}")
                except requests.RequestException as e:
                    print(f"Error downloading {item_path}: {e}")

        elif item["change_type"] == "deleted":
            # Delete the file or directory
            item_path = os.path.join("./Binary", item["path"])
            try:
                if os.path.isdir(item_path):
                    os.rmdir(item_path)
                    print(f"Deleted directory: {item_path}")
                else:
                    os.remove(item_path)
                    print(f"Deleted file: {item_path}")
            except OSError as e:
                print(f"Error deleting {item_path}: {e}")
