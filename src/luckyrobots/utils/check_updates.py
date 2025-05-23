import json
import mimetypes
import os
import platform
import re
import sys
import time
import zlib
from urllib.parse import urljoin

import requests

root_path = os.path.join(os.path.dirname(__file__), "..", "..", "examples/Binary/mac")
json_file = os.path.join(root_path, "file_structure.json")
base_url = "https://builds.luckyrobots.xyz/"


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


def calculate_crc32(file_path):
    with open(file_path, "rb") as file:
        crc32 = 0
        while True:
            data = file.read(65536)  # Read in 64kb chunks
            if not data:
                break
            crc32 = zlib.crc32(data, crc32)
    return crc32 & 0xFFFFFFFF  # Ensure unsigned 32-bit integer


def scan_directory(root_path):
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
                    "size": 0,  # Directories don't have a size in this context
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
            file_type, encoding = mimetypes.guess_type(file_path)
            if file_type is None:
                file_type = "application/octet-stream"  # Default to binary if type can't be guessed

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


def save_json(data, filename):
    with open(filename, "w") as f:
        json.dump(data, f, indent=2)


def load_json(filename):
    with open(filename, "r") as f:
        return json.load(f)


def clean_path(path):
    # Remove ['children'] and quotes, replace '][' with '/'
    cleaned = re.sub(r"\['children'\]", "", path).replace("']['", "/").strip("[]'")
    # Replace remaining single quotes with nothing
    cleaned = cleaned.replace("'", "")
    # Split the path and the attribute that changed
    parts = cleaned.rsplit("/", 1)
    return parts[0], parts[1] if len(parts) > 1 else None


def compare_structures(json1, json2):
    dict1 = {item["path"]: item for item in json1}
    dict2 = {item["path"]: item for item in json2}

    result = []

    # Check for new and modified items
    for path, item in dict2.items():
        if path not in dict1:
            item["change_type"] = "new_file"
            result.append(item)
        elif item["type"] == "file" and item["crc32"] != dict1[path]["crc32"]:
            item["change_type"] = "modified"
            result.append(item)
        # Unchanged items are not added to the result

    # Check for deleted items
    for path, item in dict1.items():
        if path not in dict2:
            item["change_type"] = "deleted"
            result.append(item)

    # Remove the item with "path": "hashmap.json" from the result
    result = [item for item in result if item["path"] != "hashmap.json"]
    # save_json(result, "changes.json")
    return result


def scan_server(server_path):
    mac_path = os.path.join(server_path, "mac")
    win_path = os.path.join(server_path, "win")
    linux_path = os.path.join(server_path, "linux")

    mac_structure = scan_directory(mac_path)
    win_structure = scan_directory(win_path)
    linux_structure = scan_directory(linux_path)

    save_json(mac_structure, os.path.join(server_path, "mac/hashmap.json"))
    save_json(win_structure, os.path.join(server_path, "win/hashmap.json"))
    save_json(linux_structure, os.path.join(server_path, "linux/hashmap.json"))


def check_updates(root_path):
    # Determine the operating system
    os_type = get_os_type()
    global base_url
    # Set the base URL

    # Construct the URL based on the operating system
    os_type = get_os_type()
    url = urljoin(base_url, f"{os_type}/hashmap.json")

    # Download the JSON file
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for HTTP errors
        server_structure = response.json()
    except requests.RequestException as e:
        print(f"Error downloading JSON file: {e}")
        server_structure = None

    if server_structure is None:
        print("Using local scan as no remote file could be downloaded.")
        server_structure = {}

    # Scan the directory and create a new file structure
    client_structure = scan_directory(root_path)

    # If a previous scan exists, compare and show changes
    if server_structure:
        changes = compare_structures(client_structure, server_structure)

        # for future debugging
        # # Write the flat JSON to a file
        # with open('changes.json', 'w') as f:
        #     json.dump(changes, f, indent=2)

        # print(f"Changes have been written to changes.json")
    else:
        print("No server structure available for comparison.")

    # for future debugging
    # # Save the new structure
    # save_json(client_structure, "./client_structure.json")

    return changes


if __name__ == "__main__":
    lr_server_root = None

    for arg in sys.argv:
        if arg.startswith("--lr-server-root="):
            lr_server_root = arg.split("=", 1)[1]
            break

    if lr_server_root:
        # this is being used as a cron job on the main server to keep the client file structures up to date
        print(f"Scanning server at {lr_server_root}")
        scan_server(lr_server_root)
