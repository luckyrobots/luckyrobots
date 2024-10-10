import os
import json
import zlib
import time
import platform
import requests
from urllib.parse import urljoin
import sys
import re
import mimetypes

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
    file_structure = []
    
    for dirpath, dirnames, filenames in os.walk(root_path):
        # Add directories
        for dirname in dirnames:
            dir_path = os.path.join(dirpath, dirname)
            relative_path = os.path.relpath(dir_path, root_path)
            file_structure.append({
                "path": relative_path,
                "type": "directory",
                "size": 0,  # Directories don't have a size in this context
                "mtime": os.path.getmtime(dir_path)
            })
        
        # Add files
        for filename in filenames:
            file_path = os.path.join(dirpath, filename)
            relative_path = os.path.relpath(file_path, root_path)
            file_stat = os.stat(file_path)
            
            # Guess the file type using mimetypes
            file_type, encoding = mimetypes.guess_type(file_path)
            if file_type is None:
                file_type = "application/octet-stream"  # Default to binary if type can't be guessed
            
            file_structure.append({
                "path": relative_path,
                "crc32": calculate_crc32(file_path),
                "size": file_stat.st_size,
                "mtime": file_stat.st_mtime,
                "type": "file",
                "mime_type": file_type
            })
    
    return file_structure

def save_json(data, filename):
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)

def load_json(filename):
    with open(filename, 'r') as f:
        return json.load(f)

def clean_path(path):
    # Remove ['children'] and quotes, replace '][' with '/'
    cleaned = re.sub(r"\['children'\]", "", path).replace("']['", "/").strip("[]'")
    # Replace remaining single quotes with nothing
    cleaned = cleaned.replace("'", "")
    # Split the path and the attribute that changed
    parts = cleaned.rsplit('/', 1)
    return parts[0], parts[1] if len(parts) > 1 else None

def compare_structures(json1, json2):
    abc = json.dumps(json1, sort_keys=True) == json.dumps(json2, sort_keys=True)
    print(abc)
    return abc

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
        
        # Create a flat JSON structure for changes
        flat_changes = []
        for change_type, files in changes.items():
            for file in sorted(files):
                if isinstance(file, list):
                    path = file[0].replace('root[', '', 1)  # Remove 'root[' prefix
                    flat_changes.append({
                        "path": path,
                        "changeType": change_type,
                        "attribute": file[1]
                    })
                else:
                    path = file.replace('root[', '', 1)  # Remove 'root[' prefix
                    flat_changes.append({
                        "path": path,
                        "changeType": change_type
                    })
        
        # Write the flat JSON to a file
        with open('changes.json', 'w') as f:
            json.dump(flat_changes, f, indent=2)
        
        print(f"Changes have been written to changes.json")
    else:
        print("No server structure available for comparison.")

    # Save the new structure
    save_json(client_structure, "./client_structure.json")

if __name__ == "__main__":
    lr_server_root = None
    
    for arg in sys.argv:
        if arg.startswith('--lr-server-root='):
            lr_server_root = arg.split('=', 1)[1]
            break

    if lr_server_root:
        # this is being used as a cron job on the main server to keep the client file structures up to date
        print(f"Scanning server at {lr_server_root}")
        scan_server(lr_server_root)
