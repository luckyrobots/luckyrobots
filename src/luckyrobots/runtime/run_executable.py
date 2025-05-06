import atexit
import os
import platform
import subprocess
import sys
import tempfile

import psutil

LOCK_FILE = os.path.join(tempfile.gettempdir(), "luckyworld_lock")


def is_luckyworld_running() -> bool:
    """Check if LuckyWorld is running by checking the lock file or process name"""
    # Check for the lock file
    if os.path.exists(LOCK_FILE):
        with open(LOCK_FILE, "r") as f:
            pid = int(f.read().strip())
        if psutil.pid_exists(pid):
            # Double-check if the process is actually LuckyWorld
            try:
                process = psutil.Process(pid)
                if "LuckyWorld" in process.name():
                    return True
            except psutil.NoSuchProcess:
                pass  # Process doesn't exist, continue to remove lock file

        # If we reach here, the lock file is stale
        remove_lock_file()

    # Check for any running LuckyWorld processes
    for proc in psutil.process_iter(["name"]):
        if "LuckyWorld" in proc.info["name"]:
            create_lock_file(proc.pid)
            return True

    return False


def create_lock_file(pid: int) -> None:
    """Create a lock file with the process ID to prevent multiple instances of LuckyWorld from running"""
    with open(LOCK_FILE, "w") as f:
        f.write(str(pid))


def remove_lock_file() -> None:
    """Remove the lock file to allow LuckyWorld to run again"""
    if os.path.exists(LOCK_FILE):
        os.remove(LOCK_FILE)


def run_luckyworld_executable(
    scene: str, robot_type: str, task: str, directory_to_watch: str
) -> None:
    """Run the LuckyWorld executable"""
    # Determine the correct path based on the operating system
    if platform.system() == "Darwin":  # macOS
        executable_path = os.path.join(
            directory_to_watch, "..", "..", "..", "MacOS", "LuckyWorld"
        )
    elif platform.system() == "Linux":  # Linux
        executable_path = os.path.join(directory_to_watch, "..", "..", "LuckyWorld.sh")
    else:  # Windows or other platforms
        executable_path = os.path.join(
            directory_to_watch, "..", "..", "luckyrobots.exe"
        )

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

        # Build command with simulation parameters
        command = [executable_path]
        if scene:
            command.extend(["--scene", scene])
        if robot_type:
            command.extend(["--robot-type", robot_type])
        if task:
            command.extend(["--task", task])

        # Run the executable as a detached process
        if platform.system() == "Windows":
            # For Windows
            DETACHED_PROCESS = 0x00000008
            process = subprocess.Popen(
                command,
                creationflags=DETACHED_PROCESS,
                close_fds=True,
                stdout=subprocess.DEVNULL if not verbose else None,
                stderr=subprocess.DEVNULL if not verbose else None,
            )
        else:
            # For Unix-based systems (macOS, Linux)
            process = subprocess.Popen(
                command,
                start_new_session=True,
                stdout=subprocess.DEVNULL if not verbose else None,
                stderr=subprocess.DEVNULL if not verbose else None,
            )

        # Create lock file with the new process ID
        create_lock_file(process.pid)

        if verbose:
            print(
                f"LuckyWorld application started successfully with scene={scene}, robot_type={robot_type}, task={task}"
            )
    except subprocess.CalledProcessError as e:
        print(f"Error: Failed to start LuckyWorld application. {e}")
    except PermissionError as e:
        print(f"Error: Permission denied. Unable to set execute permissions. {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


# Ensure lock file is removed if the script exits unexpectedly
atexit.register(remove_lock_file)
