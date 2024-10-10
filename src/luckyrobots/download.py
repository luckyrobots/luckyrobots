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

    check_updates(binary_folder)
    
    return binary_folder



