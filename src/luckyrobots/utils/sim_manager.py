import atexit
import os
import platform
import subprocess
import sys
import tempfile
import signal
import threading
import time
import logging
from typing import Optional

if not os.getenv("PYTEST_CURRENT_TEST") and not os.getenv("LUCKYROBOTS_NO_LOGS"):
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
logger = logging.getLogger("luckyworld")

LOCK_FILE = os.path.join(tempfile.gettempdir(), "luckyworld_lock")
_process = None
_monitor_thread = None
_shutdown_event = threading.Event()


def cleanup():
    """Cleanup function to be called when the script exits"""
    global _process, _monitor_thread

    logger.info("Cleaning up LuckyWorld...")

    # Stop monitoring first
    if _monitor_thread is not None and _monitor_thread.is_alive():
        _shutdown_event.set()
        _monitor_thread.join(timeout=3)

    # Terminate process
    if _process is not None:
        try:
            if _process.poll() is None:  # Process is still running
                logger.info("Terminating LuckyWorld process...")
                _process.terminate()
                _process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            logger.warning("Process didn't terminate gracefully, force killing...")
            _process.kill()
            try:
                _process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                logger.error("Failed to kill process")
        except Exception as e:
            logger.error(f"Error during process cleanup: {e}")

    # Always remove lock file
    remove_lock_file()
    logger.info("Cleanup complete")


def monitor_process():
    """Monitor the LuckyWorld process and handle its termination"""
    global _process
    try:
        while not _shutdown_event.is_set():
            if _process is None or _process.poll() is not None:
                logger.warning("LuckyWorld process has terminated")
                # Don't kill the main process, just break out of monitoring
                break
            time.sleep(1)
    except Exception as e:
        logger.error(f"Error in process monitor: {e}")
    finally:
        # Ensure cleanup happens when monitoring stops
        if not _shutdown_event.is_set():
            logger.info("Process monitor detected termination, cleaning up...")
            remove_lock_file()


def is_luckyworld_running() -> bool:
    """Check if LuckyWorld is running by checking the lock file"""
    return os.path.exists(LOCK_FILE)


def create_lock_file(pid: int) -> None:
    """Create a lock file with the process ID"""
    with open(LOCK_FILE, "w") as f:
        f.write(str(pid))


def remove_lock_file() -> None:
    """Remove the lock file"""
    try:
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)
            logger.debug("Lock file removed successfully")
        else:
            logger.debug("Lock file doesn't exist, nothing to remove")
    except Exception as e:
        logger.error(f"Error removing lock file: {e}")


def signal_handler(signum, frame):
    """Handle termination signals"""
    logger.info(f"Received signal {signum}, shutting down...")
    cleanup()
    sys.exit(0)


def find_luckyworld_executable() -> Optional[str]:
    """Automatically find LuckyWorld executable in common locations"""
    is_wsl = "microsoft" in platform.uname().release.lower()

    # 1. Check environment variable first (highest priority)
    env_path = os.environ.get("LUCKYWORLD_PATH")
    if env_path:
        logger.info(f"Using LUCKYWORLD_PATH environment variable: {env_path}")
        if os.path.exists(env_path):
            return env_path
        else:
            logger.warning(f"LUCKYWORLD_PATH points to non-existent file: {env_path}")

    # 2. Check LUCKYWORLD_HOME environment variable
    env_home = os.environ.get("LUCKYWORLD_HOME")
    if env_home:
        logger.info(f"Using LUCKYWORLD_HOME environment variable: {env_home}")
        if platform.system() == "Linux" and not is_wsl:
            env_executable = os.path.join(env_home, "LuckyWorld.sh")
        elif platform.system() == "Darwin":
            env_executable = os.path.join(
                env_home, "LuckyWorld.app", "Contents", "MacOS", "LuckyWorld"
            )
        else:
            env_executable = os.path.join(env_home, "LuckyWorldV2.exe")

        if os.path.exists(env_executable):
            return env_executable
        else:
            logger.warning(
                f"LUCKYWORLD_HOME does not contain executable: {env_executable}"
            )

    # 3. System installation paths
    if platform.system() == "Linux" and not is_wsl:
        system_paths = [
            "/opt/LuckyWorld/LuckyWorld.sh",
            "/usr/local/bin/LuckyWorld.sh",
            os.path.expanduser("~/.local/share/LuckyWorld/LuckyWorld.sh"),
            os.path.expanduser("~/LuckyWorld/LuckyWorld.sh"),
        ]
    elif platform.system() == "Darwin":
        system_paths = [
            "/Applications/LuckyWorld/LuckyWorld.app/Contents/MacOS/LuckyWorld",
            os.path.expanduser(
                "~/Applications/LuckyWorld/LuckyWorld.app/Contents/MacOS/LuckyWorld"
            ),
        ]
    else:  # Windows or WSL2
        system_paths = [
            "C:\\Program Files\\LuckyWorld\\LuckyWorldV2.exe",
            "C:\\Program Files (x86)\\LuckyWorld\\LuckyWorldV2.exe",
            os.path.expanduser("~\\AppData\\Local\\LuckyWorld\\LuckyWorldV2.exe"),
        ]

        if is_wsl:
            system_paths.extend(
                [
                    "/mnt/c/Program Files/LuckyWorld/LuckyWorldV2.exe",
                    "/mnt/c/Program Files (x86)/LuckyWorld/LuckyWorldV2.exe",
                ]
            )

    for path in system_paths:
        if os.path.exists(path):
            logger.info(f"Found LuckyWorld at: {path}")
            return path

    return None


def launch_luckyworld(
    scene: str = "ArmLevel",
    robot: str = "so100",
    task: Optional[str] = None,
    executable_path: Optional[str] = None,
    headless: bool = False,
    windowed: bool = True,
    verbose: bool = False,
) -> bool:
    """Launch LuckyWorld with simplified parameters"""
    global _process, _monitor_thread

    # Check if already running
    if is_luckyworld_running():
        logger.error("LuckyWorld is already running. Stop the existing instance first.")
        return False

    # Find executable if not provided
    if executable_path is None:
        executable_path = find_luckyworld_executable()
        if executable_path is None:
            logger.error(
                "Could not find LuckyWorld executable. Please provide the path manually."
            )
            logger.info("You can set the path using environment variables:")
            logger.info("  LUCKYWORLD_PATH=/full/path/to/LuckyWorldV2.exe")
            logger.info("  LUCKYWORLD_HOME=/path/to/luckyworld/directory")
            logger.info("Or check these common locations:")
            logger.info("  Development: Build/Windows/LuckyWorldV2.exe")
            logger.info("  Windows: C:\\Program Files\\LuckyWorld\\LuckyWorldV2.exe")
            logger.info("  WSL2: /mnt/c/Program Files/LuckyWorld/LuckyWorldV2.exe")
            return False

    if not os.path.exists(executable_path) or not executable_path.endswith(".exe"):
        logger.error(f"Executable not found at: {executable_path}")
        return False

    try:
        # Set execute permissions on Unix systems
        if platform.system() != "Windows":
            os.chmod(executable_path, 0o755)

        logger.info(f"Launching LuckyWorld: {executable_path}")

        # Build command
        command = [executable_path]
        command.append(f"-Scene={scene}")
        command.append(f"-Robot={robot}")

        if task:
            command.append(f"-Task={task}")

        if headless:
            command.append("-Headless")
        else:
            if windowed:
                command.append("-windowed")
            else:
                command.append("-fullscreen")

        command.append("-Realtime")

        logger.info(f"Command: {' '.join(command)}")

        # Launch process
        if platform.system() == "Windows":
            DETACHED_PROCESS = 0x00000008
            _process = subprocess.Popen(
                command,
                creationflags=DETACHED_PROCESS,
                close_fds=True,
                stdout=None if verbose else subprocess.DEVNULL,
                stderr=None if verbose else subprocess.DEVNULL,
            )
        else:
            _process = subprocess.Popen(
                command,
                start_new_session=True,
                stdout=None if verbose else subprocess.DEVNULL,
                stderr=None if verbose else subprocess.DEVNULL,
            )

        # Start monitoring
        _shutdown_event.clear()
        _monitor_thread = threading.Thread(target=monitor_process, daemon=True)
        _monitor_thread.start()

        create_lock_file(_process.pid)

        logger.info(f"LuckyWorld started successfully (PID: {_process.pid})")
        logger.info(f"Scene: {scene}, Robot: {robot}, Task: {task or 'None'}")

        return True

    except Exception as e:
        logger.error(f"Failed to launch LuckyWorld: {e}")
        cleanup()
        return False


def stop_luckyworld() -> bool:
    """Stop the running LuckyWorld instance"""
    global _process

    if not is_luckyworld_running():
        logger.info("LuckyWorld is not running")
        return True

    try:
        if _process:
            logger.info("Stopping LuckyWorld...")
            # First try graceful termination
            _process.terminate()
            try:
                _process.wait(timeout=60)
            except TimeoutError:
                # If graceful termination fails, force kill
                logger.info("Graceful termination failed, forcing process kill...")
                _process.kill()
                _process.wait(timeout=60)
            
            logger.info("LuckyWorld stopped successfully")
        cleanup()
        return True
    except Exception as e:
        logger.error(f"Error stopping LuckyWorld: {e}")
        return False


# Register cleanup and signal handlers
atexit.register(cleanup)
signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C
signal.signal(signal.SIGTERM, signal_handler)  # Termination signal
