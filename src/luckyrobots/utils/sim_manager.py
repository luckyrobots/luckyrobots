import os
import platform
import subprocess
import tempfile
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


def monitor_process():
    """Monitor the LuckyWorld process and handle its termination"""
    global _process
    try:
        while not _shutdown_event.is_set():
            if _process is None or _process.poll() is not None:
                logger.info("LuckyWorld process has terminated")
                # Don't kill the main process, just break out of monitoring
                break
            time.sleep(1)
    except Exception as e:
        logger.error(f"Error in process monitor: {e}")
    finally:
        # Ensure cleanup happens when monitoring stops
        if not _shutdown_event.is_set():
            remove_lock_file()


def is_luckyworld_running() -> bool:
    """Check if LuckyWorld is running by checking the lock file"""
    return os.path.exists(LOCK_FILE)


def create_lock_file(pid: int) -> None:
    """Create a lock file with the process ID"""
    with open(LOCK_FILE, "w") as f:
        f.write(str(pid))


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
    debug: bool = False,
    executable_path: Optional[str] = None,
    headless: bool = False,
    windowed: bool = True,
    verbose: bool = False,
) -> bool:
    """Launch LuckyWorld with simplified parameters"""
    global _process, _monitor_thread

    # Check if already running
    if is_luckyworld_running():
        logger.error(
            "LuckyWorld is already running. \
            Stop the existing instance or remove the luckyworld lock file located at /tmp/luckyworld_lock."
        )
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
            logger.info("  Development: Builds/Windows/LuckyWorldV2.exe")
            logger.info("  Windows: C:\\Program Files\\LuckyWorld\\LuckyWorldV2.exe")
            logger.info("  WSL2: /mnt/c/Program Files/LuckyWorld/LuckyWorldV2.exe")
            return False

    if not os.path.exists(executable_path):
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

        if debug:
            command.append("-Debug")

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
        stop_luckyworld()
        return False


def kill_processes():
    """Kill all LuckyWorld processes"""
    system = platform.system()
    is_wsl = "microsoft" in platform.uname().release.lower()

    if is_wsl:
        return _kill_wsl_processes()
    elif system == "Windows":
        return _kill_windows_processes()
    elif system == "Darwin":
        return _kill_macos_processes()
    else:
        return _kill_linux_processes()


def _kill_wsl_processes():
    try:
        result = subprocess.run(
            [
                "/mnt/c/Windows/System32/taskkill.exe",
                "/F",
                "/IM",
                "LuckyWorldV2.exe",  # NOTE: Make sure this is the name of the LuckyWorld executable
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode == 0:
            return True
        elif result.returncode == 128:  # Process not found
            logger.error("No LuckyWorld processes found running")
            return False
        else:
            logger.warning(
                f"taskkill failed with code {result.returncode}: {result.stderr}"
            )
            return False

    except subprocess.TimeoutExpired:
        logger.error("taskkill command timed out")
        return False
    except Exception as e:
        logger.error(f"Failed to kill processes: {e}")
        return False


def _kill_windows_processes():
    """Windows-specific process killing"""
    try:
        # Kill LuckyWorldV2.exe
        result = subprocess.run(
            ["taskkill", "/F", "/IM", "LuckyWorldV2.exe"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode == 0:
            logger.info("Successfully killed LuckyWorldV2.exe processes")
            return True
        elif result.returncode == 128:  # Process not found
            logger.info("No LuckyWorldV2.exe processes found")
            return True
        else:
            logger.warning(f"taskkill failed: {result.stderr}")
            return False

    except subprocess.TimeoutExpired:
        logger.error("taskkill command timed out")
        return False
    except FileNotFoundError:
        logger.error("taskkill command not found")
        return False
    except Exception as e:
        logger.error(f"Failed to kill Windows processes: {e}")
        return False


def _kill_macos_processes():
    """macOS-specific process killing"""
    try:
        # Kill LuckyWorld processes
        result = subprocess.run(
            ["pkill", "-f", "LuckyWorld"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode == 0:
            logger.info("Successfully killed LuckyWorld processes")
            return True
        elif result.returncode == 1:  # No processes found
            logger.info("No LuckyWorld processes found")
            return True
        else:
            logger.warning(f"pkill failed: {result.stderr}")
            return False

    except subprocess.TimeoutExpired:
        logger.error("pkill command timed out")
        return False
    except FileNotFoundError:
        logger.error("pkill command not found")
        return False
    except Exception as e:
        logger.error(f"Failed to kill macOS processes: {e}")
        return False


def _kill_linux_processes():
    """Linux-specific process killing"""
    try:
        # Kill LuckyWorld processes
        result = subprocess.run(
            ["pkill", "-f", "LuckyWorld"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode == 0:
            logger.info("Successfully killed LuckyWorld processes")
            return True
        elif result.returncode == 1:  # No processes found
            logger.info("No LuckyWorld processes found")
            return True
        else:
            logger.warning(f"pkill failed: {result.stderr}")
            return False

    except subprocess.TimeoutExpired:
        logger.error("pkill command timed out")
        return False
    except FileNotFoundError:
        logger.error("pkill command not found")
        return False
    except Exception as e:
        logger.error(f"Failed to kill Linux processes: {e}")
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

            try:
                _process.terminate()
                _process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.info("Graceful termination timeout, using kill_processes...")
            except Exception:
                logger.info("Graceful termination failed, using kill_processes...")

            kill_processes()

        remove_lock_file()
        return True
    except Exception as e:
        logger.error(f"Error stopping LuckyWorld: {e}")
        return False
