import os
import json
import zlib
import time
import platform
import requests
from urllib.parse import urljoin

root_path = os.path.join(os.path.dirname(__file__), "..", "..", "examples/Binary/mac")
json_file = os.path.join(root_path, "file_structure.json")


def calculate_crc32(file_path):
    with open(file_path, 'rb') as file:
        crc32 = 0
        while True:
            data = file.read(65536)  # Read in 64kb chunks
            if not data:
                break
            crc32 = zlib.crc32(data, crc32)
    return crc32 & 0xFFFFFFFF  # Ensure unsigned 32-bit integer

def scan_directory(root_path):
    file_structure = {}
    
    for dirpath, dirnames, filenames in os.walk(root_path):
        current_dict = file_structure
        path_parts = os.path.relpath(dirpath, root_path).split(os.sep)
        
        for part in path_parts:
            if part == '.':
                continue
            if part not in current_dict:
                current_dict[part] = {"type": "directory", "children": {}}
            current_dict = current_dict[part]["children"]
        
        for filename in filenames:
            file_path = os.path.join(dirpath, filename)
            file_stat = os.stat(file_path)
            current_dict[filename] = {
                "type": "file",
                "size": file_stat.st_size,
                "mtime": file_stat.st_mtime,
                "crc32": calculate_crc32(file_path)
            }
    
    return file_structure

def save_json(data, filename):
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)

def load_json(filename):
    with open(filename, 'r') as f:
        return json.load(f)

def compare_structures(old_structure, new_structure):
    changes = {
        'new_files': [],
        'modified_files': [],
        'deleted_files': []
    }

    for path in new_structure:
        if path not in old_structure:
            changes['new_files'].append(path)
        else:
            for filename, new_file_info in new_structure[path]['children'].items():
                old_file_info = old_structure[path]['children'].get(filename)
                if not old_file_info:
                    changes['new_files'].append(os.path.join(path, filename))
                elif new_file_info['crc32'] != old_file_info['crc32']:
                    changes['modified_files'].append(os.path.join(path, filename))

    for path in old_structure:
        if path not in new_structure:
            changes['deleted_files'].extend([os.path.join(path, f) for f in old_structure[path]['children']])
        else:
            for filename in old_structure[path]['children']:
                if filename not in new_structure[path]['children']:
                    changes['deleted_files'].append(os.path.join(path, filename))

    return changes

def check_updates(root_path):



    # Determine the operating system
    os_type = platform.system().lower()

    # Set the base URL
    base_url = "https://builds.luckyrobots.xyz/"

    # Construct the URL based on the operating system
    if os_type == "darwin":
        url = urljoin(base_url, "mac/hashmap.json")
    elif os_type == "windows":
        url = urljoin(base_url, "win/hashmap.json")
    elif os_type == "linux":
        url = urljoin(base_url, "linux/hashmap.json")
    else:
        raise ValueError(f"Unsupported operating system: {os_type}")

    # Download the JSON file
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for HTTP errors
        server_json = response.json()
    except requests.RequestException as e:
        print(f"Error downloading JSON file: {e}")
        server_json = None

    if json_file is None:
        print("Using local scan as no remote file could be downloaded.")

    # Scan the directory and create a new file structure
    client_structure = scan_directory(root_path)

    # If a previous scan exists, compare and show changes
    if os.path.exists(json_file):
        server_structure = load_json(server_json)
        changes = compare_structures(client_structure, server_structure)
        
        print("Changes detected:")
        for change_type, files in changes.items():
            if files:
                print(f"{change_type.replace('_', ' ').capitalize()}:")
                for file in files:
                    print(f"  - {file}")
    else:
        print("Initial scan completed.")

    # Save the new structure
    save_json(client_structure, json_file)

if __name__ == "__main__":
    check_updates(root_path, json_file)