import atexit
import os
import platform
import subprocess
import sys
import tempfile
import signal
import threading
import time

import psutil
import logging

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("executable")

LOCK_FILE = os.path.join(tempfile.gettempdir(), "luckyworld_lock")
_process = None  # Global variable to store the process
_monitor_thread = None  # Global variable to store the monitor thread
_shutdown_event = threading.Event()


def cleanup():
    """Cleanup function to be called when the script exits"""
    global _process, _monitor_thread
    if _process is not None:
        try:
            # Try to terminate the process gracefully
            _process.terminate()
            _process.wait(timeout=5)  # Wait up to 5 seconds for graceful termination
        except subprocess.TimeoutExpired:
            # If process doesn't terminate gracefully, force kill it
            _process.kill()
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

    if _monitor_thread is not None and _monitor_thread.is_alive():
        _shutdown_event.set()
        _monitor_thread.join(timeout=5)

    remove_lock_file()


def monitor_process():
    """Monitor the LuckyWorld process and handle its termination"""
    global _process
    try:
        while not _shutdown_event.is_set():
            if _process is None or _process.poll() is not None:
                logger.error("LuckyWorld process has terminated unexpectedly")
                # Signal the main process to exit
                os.kill(os.getpid(), signal.SIGTERM)
                break
            time.sleep(1)  # Check every second
    except Exception as e:
        logger.error(f"Error in process monitor: {e}")
        os.kill(os.getpid(), signal.SIGTERM)


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
    scene: str, robot: str, task: str = None, pkg_path: str = None
) -> None:
    """Run the LuckyWorld executable"""
    global _process, _monitor_thread
    is_wsl = "microsoft" in platform.uname().release.lower()

    if platform.system() == "Linux" and not is_wsl:
        platform_name = "linux"
    elif platform.system() == "Darwin":
        platform_name = "mac"
    else:
        platform_name = "win"

    if pkg_path is None:
        pkg_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "examples", "Binary", platform_name
        )

    if platform_name == "mac":
        executable_path = os.path.join(
            pkg_path, "LuckyWorld.app", "Contents", "MacOS", "LuckyWorld"
        )
    elif platform_name == "linux":
        executable_path = os.path.join(pkg_path, "LuckyWorld.sh")
    else:  # Windows or WSL2
        executable_path = os.path.join(pkg_path, "LuckyWorldV2.exe")

    # Check if the executable exists
    if not os.path.exists(executable_path):
        logger.error(f"Error: Executable not found at {executable_path}")
        sys.exit(1)
        return

    try:
        # Set execute permissions (only needed on Unix systems)
        if platform.system() != "Windows":
            os.chmod(executable_path, 0o755)

        logger.info(f"Running executable at: {executable_path}")
        verbose = "--lr-verbose" in sys.argv

        # Build command as separate arguments
        command = [executable_path]
        if scene:
            command.append(f"-Scene={scene}")
        if robot:
            command.append(f"-Robot={robot}")
        if task:  # Task is optional
            command.append(f"-Task={task}")

        # Log the full command for debugging
        logger.info(f"Full command: {' '.join(command)}")

        # Run the executable as a detached process
        if platform.system() == "Windows":
            # Only use creationflags when actually running on Windows
            DETACHED_PROCESS = 0x00000008
            _process = subprocess.Popen(
                command,
                creationflags=DETACHED_PROCESS,
                close_fds=True,
                stdout=subprocess.DEVNULL if not verbose else None,
                stderr=subprocess.DEVNULL if not verbose else None,
            )
        else:
            # For Unix-based systems (macOS, Linux, WSL2)
            # Use start_new_session to detach the process
            _process = subprocess.Popen(
                command,
                start_new_session=True,
                stdout=subprocess.DEVNULL if not verbose else None,
                stderr=subprocess.DEVNULL if not verbose else None,
            )

        # Start the monitor thread
        _shutdown_event.clear()
        _monitor_thread = threading.Thread(target=monitor_process, daemon=True)
        _monitor_thread.start()

        create_lock_file(_process.pid)

        logger.info(
            f"LuckyWorld application started successfully (PID: {_process.pid})"
        )
        if verbose:
            logger.info(f"Arguments: scene={scene}, robot={robot}, task={task}")

    except subprocess.CalledProcessError as e:
        logger.error(f"Error: Failed to start LuckyWorld application. {e}")
        cleanup()
        sys.exit(1)
    except PermissionError as e:
        logger.error(
            f"Error: Permission denied. Unable to execute {executable_path}. {e}"
        )
        cleanup()
        sys.exit(1)
    except FileNotFoundError as e:
        logger.error(f"Error: File not found. {e}")
        cleanup()
        sys.exit(1)
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        cleanup()
        sys.exit(1)


# Register cleanup function to be called on exit
atexit.register(cleanup)
