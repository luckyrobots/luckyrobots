import os
import tempfile
import psutil
import subprocess
import platform
import atexit
import sys

LOCK_FILE = os.path.join(tempfile.gettempdir(), 'luckeworld_lock')

def is_luckeworld_running():
    # Check for the lock file
    if os.path.exists(LOCK_FILE):
        with open(LOCK_FILE, 'r') as f:
            pid = int(f.read().strip())
        if psutil.pid_exists(pid):
            # Double-check if the process is actually LuckEWorld
            try:
                process = psutil.Process(pid)
                if "LuckEWorld" in process.name() or "luckyrobots" in process.name():
                    return True
            except psutil.NoSuchProcess:
                pass  # Process doesn't exist, continue to remove lock file
        
        # If we reach here, the lock file is stale
        remove_lock_file()
    
    # Check for any running LuckEWorld processes
    for proc in psutil.process_iter(['name']):
        if "LuckEWorld" in proc.info['name'] or "luckyrobots" in proc.info['name']:
            create_lock_file(proc.pid)
            return True
    
    return False

def create_lock_file(pid):
    with open(LOCK_FILE, 'w') as f:
        f.write(str(pid))

def remove_lock_file():
    if os.path.exists(LOCK_FILE):
        os.remove(LOCK_FILE)

def run_luckeworld_executable(directory_to_watch):
    # Determine the correct path based on the operating system
    if platform.system() == "Darwin":  # macOS
        executable_path = os.path.join(directory_to_watch, "..","..","..","MacOS", "luckyrobots")
    elif platform.system() == "Linux":  # Linux
        executable_path = os.path.join(directory_to_watch, "..","..","luckyrobots.sh")
    else:  # Windows or other platforms
        executable_path = os.path.join(directory_to_watch, "..","..","luckyrobots.exe")        

    # Check if the executable exists
    if not os.path.exists(executable_path):
        print(f"Error: Executable not found at {executable_path}")
        sys.exit(1)
        return

    try:
        # Set execute permissions
        os.chmod(executable_path, 0o755)
        print("running executable at:", executable_path)
        # Check if --lr-verbose flag is used
        verbose = "--lr-verbose" in sys.argv

        # Run the executable as a detached process
        if platform.system() == "Windows":
            # For Windows
            DETACHED_PROCESS = 0x00000008
            process = subprocess.Popen(
                executable_path,
                creationflags=DETACHED_PROCESS,
                close_fds=True,
                stdout=subprocess.DEVNULL if not verbose else None,
                stderr=subprocess.DEVNULL if not verbose else None
            )
        else:
            # For Unix-based systems (macOS, Linux)
            process = subprocess.Popen(
                executable_path,
                start_new_session=True,
                stdout=subprocess.DEVNULL if not verbose else None,
                stderr=subprocess.DEVNULL if not verbose else None
            )
        
        # Create lock file with the new process ID
        create_lock_file(process.pid)
        
        print("░▒▓█▓▒░     ░▒▓█▓▒░░▒▓█▓▒░░▒▓██████▓▒░░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░      ░▒▓███████▓▒░ ░▒▓██████▓▒░░▒▓███████▓▒░ ░▒▓██████▓▒░▒▓████████▓▒░▒▓███████▓▒░ ")
        print("░▒▓█▓▒░     ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░      ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░ ░▒▓█▓▒░  ░▒▓█▓▒░        ")
        print("░▒▓█▓▒░     ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░      ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░      ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░ ░▒▓█▓▒░  ░▒▓█▓▒░        ")
        print("░▒▓█▓▒░     ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░      ░▒▓███████▓▒░ ░▒▓██████▓▒░       ░▒▓███████▓▒░░▒▓█▓▒░░▒▓█▓▒░▒▓███████▓▒░░▒▓█▓▒░░▒▓█▓▒░ ░▒▓█▓▒░   ░▒▓██████▓▒░  ")
        print("░▒▓█▓▒░     ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░      ░▒▓█▓▒░░▒▓█▓▒░  ░▒▓█▓▒░          ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░ ░▒▓█▓▒░         ░▒▓█▓▒░ ")
        print("░▒▓█▓▒░     ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░  ░▒▓█▓▒░          ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░ ░▒▓█▓▒░         ░▒▓█▓▒░ ")
        print("░▒▓████████▓▒░▒▓██████▓▒░ ░▒▓██████▓▒░░▒▓█▓▒░░▒▓█▓▒░  ░▒▓█▓▒░          ░▒▓█▓▒░░▒▓█▓▒░░▒▓██████▓▒░░▒▓███████▓▒░ ░▒▓██████▓▒░  ░▒▓█▓▒░  ░▒▓███████▓▒░  ")
        print("                                                                                                                                                     ")
        print("                                                                                                                                                     ")
        print("Lucky Robots application started successfully as an independent process.")
        print("To move the robot from your python code, choose a level on the game, and tick the HTTP checkbox.")
        print("To receive the camera feed from your python code, choose a level on the game, and tick the Capture checkbox.")
        
        if verbose:
            print("LuckEWorld application started successfully as an independent process.")
    except subprocess.CalledProcessError as e:
        print(f"Error: Failed to start LuckEWorld application. {e}")
    except PermissionError as e:
        print(f"Error: Permission denied. Unable to set execute permissions. {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

# Ensure lock file is removed if the script exits unexpectedly
atexit.register(remove_lock_file)