import requests
from tqdm import tqdm
import platform
import re
from datetime import datetime
import zipfile
import os
from bs4 import BeautifulSoup
import sys 

def download_latest_build():
    base_url = "https://builds.luckyrobots.xyz"
    
    # Determine the current OS
    current_os = platform.system().lower()
    if current_os == "darwin":
        current_os = "mac"
    
    # Fetch the list of files from the server
    response = requests.get(base_url)
    if response.status_code != 200:
        print(f"Failed to fetch file list from {base_url}")
        return

    # Parse the HTML content to extract file names
    file_pattern = re.compile(f'href="(luckyrobots-{current_os}-\\d{{6}}\\.\\w+)"')
    matches = file_pattern.findall(response.text)

    if not matches:
        print(f"No matching files found for {current_os}")
        return

    # Sort files by date (descending)
    sorted_files = sorted(matches, key=lambda x: datetime.strptime(x.split('-')[2].split('.')[0], "%m%d%y"), reverse=True)

    # Display file options to user
    print(f"Available builds: (for {current_os}) (top one is the latest)")
    for i, file in enumerate(sorted_files, 1):
        print(f"{i}. {file}")

    # Ask user to choose a file
    while True:
        try:
            choice = int(input("Enter the number of the file you want to download (or 0 to cancel): "))
            if choice == 0:
                print("Download cancelled.")
                return
            if 1 <= choice <= len(sorted_files):
                selected_file = sorted_files[choice - 1]
                break
            else:
                print("Invalid choice. Please try again.")
        except ValueError:
            print("Invalid input. Please enter a number.")

    # Create Binary folder if it doesn't exist
    binary_folder = "./Binary"
    os.makedirs(binary_folder, exist_ok=True)

    # Download the selected file to Binary folder
    file_path = os.path.join(binary_folder, selected_file)
    print(f"Downloading {selected_file} to {binary_folder}...")

    file_url = f"{base_url}/{selected_file}"
    response = requests.get(file_url, stream=True)
    total_size = int(response.headers.get('content-length', 0))

    with open(file_path, 'wb') as file, tqdm(
        desc=selected_file,
        total=total_size,
        unit='iB',
        unit_scale=True,
        unit_divisor=1024,
    ) as progress_bar:
        for data in response.iter_content(chunk_size=1024):
            size = file.write(data)
            progress_bar.update(size)

    print(f"Download complete: {file_path}")
    
    # Unzip the downloaded file
    if file_path.endswith('.zip'):
        print(f"Unzipping {file_path}...")
        with zipfile.ZipFile(file_path, 'r') as zip_ref:
            zip_ref.extractall(binary_folder)
        print(f"Unzip complete. Files extracted to {binary_folder}")
        
        # Optionally, remove the zip file after extraction
        os.remove(file_path)
        print(f"Removed zip file: {file_path}")
    else:
        print(f"File {file_path} is not a zip file. Skipping unzip.")

def check_binary():
    base_url = "https://builds.luckyrobots.xyz"
    binary_folder = "./Binary"

    # Check if Binary folder exists
    if not os.path.exists(binary_folder):
        print("Binary folder not found. Downloading the latest binary...")
        download_latest_build()
        return get_newest_binary_path(binary_folder)

    # Get the list of files in the Binary folder
    date_pattern = re.compile(r'^\d{6}$')
    local_files = [f for f in os.listdir(binary_folder) if os.path.isdir(os.path.join(binary_folder, f)) and date_pattern.match(f)]

    if not local_files:
        print("No binaries found in the Binary folder. Downloading the latest binary...")
        download_latest_build()
        return get_newest_binary_path(binary_folder)

    # Get the list of files from the server
    response = requests.get(base_url)
    soup = BeautifulSoup(response.text, 'html.parser')
    server_files = [a['href'] for a in soup.find_all('a') if a['href'].startswith('luckyrobots-')]

    # Find the newest file on the server
    newest_server_file = max(server_files, key=lambda x: x.split('-')[-1])
    newest_server_date = newest_server_file.split('-')[-1].split('.')[0]

    # Find the newest local file
    newest_local_file = max(local_files, key=lambda x: datetime.strptime(x, "%m%d%y"))
    newest_local_date = newest_local_file

    # Compare dates
    if newest_server_date > newest_local_date:
        print(f"A newer binary ({newest_server_file}) is available on the server.")
        # Check if --lr-update argument is present
        if '--lr-update' in sys.argv:
            print("Updating to the latest binary...")
            download_latest_build()
            print("Update complete. Rechecking binary...")
            return check_binary()  # This won't cause an infinite loop as --lr-update is not checked in the recursive call
        print("To update to the latest binary, run with --lr-update argument.")
    else:
        print("You have the latest binary.")

    return os.path.join(binary_folder, newest_local_file)

def get_newest_binary_path(binary_folder):
    date_pattern = re.compile(r'^\d{6}$')
    local_files = [f for f in os.listdir(binary_folder) if os.path.isdir(os.path.join(binary_folder, f)) and date_pattern.match(f)]
    if not local_files:
        print("No valid binary found in the Binary folder.")
        exit()
    newest_local_file = max(local_files, key=lambda x: datetime.strptime(x, "%m%d%y"))
    return os.path.join(binary_folder, newest_local_file)