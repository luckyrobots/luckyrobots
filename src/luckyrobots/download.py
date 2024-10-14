import requests
from tqdm import tqdm
import platform
from datetime import datetime
import zipfile
import os
from bs4 import BeautifulSoup
import sys 
import re

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
    


def check_binary():
    base_url = get_base_url()
    binary_folder = "./Binary"

    changes = check_updates(binary_folder)
    print(changes)
    # apply_changes(changes)
    
    return binary_folder

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
        if item['change_type'] in ['modified', 'new_file']:
            # Construct the URL for the file
            os_type = get_os_type()
            file_url = f"{base_url}{os_type}/{item['path']}"
            
            # Ensure the directory exists
            item_path = "./Binary/" + item['path']
            item_dir = os.path.dirname("./Binary/" + item['path'])
            os.makedirs(item_dir, exist_ok=True)
            print(f"Downloading: {file_url} to {item_path}")
            # Download the file
            try:
                response = requests.get(file_url, stream=True)
                response.raise_for_status()
                
                with open(item_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                print(f"Downloaded: {item_path}")
            except requests.RequestException as e:
                print(f"Error downloading {item_path}: {e}")
        
        elif item['change_type'] == 'deleted':
            # Delete the file
            item_path = "./Binary/" + item['path']
            item_dir = os.path.dirname("./Binary/" + item['path'])
            try:
                os.remove(item_path)
                print(f"Deleted: {item_path}")
            except OSError as e:
                print(f"Error deleting {item_path}: {e}")
