"""
LuckyEngine engine lifecycle management.

This module handles launching, stopping, and managing the LuckyEngine executable.
"""

import logging
import os
import platform
import subprocess
import tempfile
import threading
import time
from typing import Optional

logger = logging.getLogger("luckyrobots.luckyengine")

# Module-level state
LOCK_FILE = os.path.join(tempfile.gettempdir(), "luckyengine_lock")
_process: Optional[subprocess.Popen] = None
_monitor_thread: Optional[threading.Thread] = None
_shutdown_event = threading.Event()


# ============================================================================
# Public API
# ============================================================================


def find_luckyengine_executable() -> Optional[str]:
    """
    Automatically find LuckyEngine executable in common locations.

    Checks in order:
    1. LUCKYENGINE_PATH environment variable
    2. LUCKYENGINE_HOME environment variable
    3. System installation paths

    Returns:
        Path to executable if found, None otherwise.
    """
    is_wsl = "microsoft" in platform.uname().release.lower()

    # 1. Check LUCKYENGINE_PATH environment variable (highest priority)
    env_path = os.environ.get("LUCKYENGINE_PATH")
    if env_path:
        logger.info(f"Using LUCKYENGINE_PATH environment variable: {env_path}")
        if os.path.exists(env_path):
            return env_path
        logger.warning(f"LUCKYENGINE_PATH points to non-existent file: {env_path}")

    # 2. Check LUCKYENGINE_HOME environment variable
    env_home = os.environ.get("LUCKYENGINE_HOME")
    if env_home:
        logger.info(f"Using LUCKYENGINE_HOME environment variable: {env_home}")
        executable = _get_executable_for_platform(env_home, "LuckyEngine", is_wsl)
        if executable and os.path.exists(executable):
            return executable
        logger.warning(f"LUCKYENGINE_HOME does not contain executable: {executable}")

    # 3. System installation paths
    system_paths = _get_system_paths(is_wsl)
    for path in system_paths:
        if os.path.exists(path):
            logger.info(f"Found LuckyEngine at: {path}")
            return path

    return None


def is_luckyengine_running() -> bool:
    """
    Check if LuckyEngine is currently running.

    Returns:
        True if lock file exists, False otherwise.
    """
    return os.path.exists(LOCK_FILE)


def launch_luckyengine(
    scene: str = "ArmLevel",
    robot: str = "so100",
    task: Optional[str] = None,
    executable_path: Optional[str] = None,
    headless: bool = False,
    windowed: bool = True,
    verbose: bool = False,
) -> bool:
    """
    Launch LuckyEngine with the specified parameters.

    Args:
        scene: Scene name to load.
        robot: Robot name to spawn.
        task: Optional task name.
        executable_path: Path to executable (auto-detected if None).
        headless: Run without rendering.
        windowed: Run in windowed mode (vs fullscreen).
        verbose: Show engine output.

    Returns:
        True if launch succeeded, False otherwise.
    """
    global _process, _monitor_thread

    # Check if already running
    if is_luckyengine_running():
        logger.error(
            "LuckyEngine is already running. "
            "Stop the existing instance or remove the lock file at "
            f"{LOCK_FILE}"
        )
        return False

    # Find executable if not provided
    if executable_path is None:
        executable_path = find_luckyengine_executable()
        if executable_path is None:
            logger.error(
                "Could not find LuckyEngine executable. "
                "Please provide the path manually."
            )
            logger.info("You can set the path using environment variables:")
            logger.info("  LUCKYENGINE_PATH=/full/path/to/LuckyEngine.exe")
            logger.info("  LUCKYENGINE_HOME=/path/to/luckyengine/directory")
            return False

    if not os.path.exists(executable_path):
        logger.error(f"Executable not found at: {executable_path}")
        return False

    try:
        # Set execute permissions on Unix systems
        if platform.system() != "Windows":
            os.chmod(executable_path, 0o755)

        logger.info(f"Launching LuckyEngine: {executable_path}")

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

        logger.info(f"LuckyEngine started successfully (PID: {_process.pid})")
        logger.info(f"Scene: {scene}, Robot: {robot}, Task: {task or 'None'}")

        return True

    except Exception as e:
        logger.error(f"Failed to launch LuckyEngine: {e}")
        stop_luckyengine()
        return False


def stop_luckyengine() -> bool:
    """
    Stop the running LuckyEngine instance.

    Returns:
        True if stopped successfully, False otherwise.
    """
    global _process

    if not is_luckyengine_running():
        logger.info("LuckyEngine is not running")
        return True

    try:
        if _process:
            logger.info("Stopping LuckyEngine...")

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
        logger.error(f"Error stopping LuckyEngine: {e}")
        return False


# ============================================================================
# Private Helpers
# ============================================================================


def _get_executable_for_platform(
    home_dir: str, base_name: str, is_wsl: bool
) -> Optional[str]:
    """Get the executable path for the current platform."""
    if platform.system() == "Linux" and not is_wsl:
        return os.path.join(home_dir, f"{base_name}.sh")
    elif platform.system() == "Darwin":
        return os.path.join(
            home_dir, f"{base_name}.app", "Contents", "MacOS", base_name
        )
    else:  # Windows or WSL2
        return os.path.join(home_dir, f"{base_name}.exe")


def _get_system_paths(is_wsl: bool) -> list[str]:
    """Get system installation paths for the current platform."""
    paths = []

    if platform.system() == "Linux" and not is_wsl:
        paths.extend(
            [
                "/opt/LuckyEngine/LuckyEngine.sh",
                "/usr/local/bin/LuckyEngine.sh",
                os.path.expanduser("~/.local/share/LuckyEngine/LuckyEngine.sh"),
                os.path.expanduser("~/LuckyEngine/LuckyEngine.sh"),
            ]
        )
    elif platform.system() == "Darwin":
        paths.extend(
            [
                "/Applications/LuckyEngine/LuckyEngine.app/Contents/MacOS/LuckyEngine",
                os.path.expanduser(
                    "~/Applications/LuckyEngine/LuckyEngine.app/Contents/MacOS/LuckyEngine"
                ),
            ]
        )
    else:  # Windows or WSL2
        paths.extend(
            [
                "C:\\Program Files\\LuckyEngine\\LuckyEngine.exe",
                "C:\\Program Files (x86)\\LuckyEngine\\LuckyEngine.exe",
                os.path.expanduser("~\\AppData\\Local\\LuckyEngine\\LuckyEngine.exe"),
            ]
        )

        if is_wsl:
            paths.extend(
                [
                    "/mnt/c/Program Files/LuckyEngine/LuckyEngine.exe",
                    "/mnt/c/Program Files (x86)/LuckyEngine/LuckyEngine.exe",
                ]
            )

    return paths


def monitor_process() -> None:
    """Monitor the LuckyEngine process and handle its termination."""
    global _process
    try:
        while not _shutdown_event.is_set():
            if _process is None or _process.poll() is not None:
                logger.info("LuckyEngine process has terminated")
                break
            time.sleep(1)
    except Exception as e:
        logger.error(f"Error in process monitor: {e}")
    finally:
        # Ensure cleanup happens when monitoring stops
        if not _shutdown_event.is_set():
            remove_lock_file()


def create_lock_file(pid: int) -> None:
    """Create a lock file with the process ID."""
    with open(LOCK_FILE, "w") as f:
        f.write(str(pid))


def remove_lock_file() -> None:
    """Remove the lock file."""
    try:
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)
            logger.debug("Lock file removed successfully")
        else:
            logger.debug("Lock file doesn't exist, nothing to remove")
    except Exception as e:
        logger.error(f"Error removing lock file: {e}")


def kill_processes() -> None:
    """Kill all LuckyEngine processes."""
    system = platform.system()
    is_wsl = "microsoft" in platform.uname().release.lower()

    if is_wsl:
        _kill_wsl_processes()
    elif system == "Windows":
        _kill_windows_processes()
    elif system == "Darwin":
        _kill_macos_processes()
    else:
        _kill_linux_processes()


def _kill_wsl_processes() -> None:
    """Kill LuckyEngine processes on WSL."""
    try:
        result = subprocess.run(
            [
                "/mnt/c/Windows/System32/taskkill.exe",
                "/F",
                "/IM",
                "LuckyEngine.exe",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            logger.info("Killed LuckyEngine.exe processes")
        elif result.returncode == 128:  # Process not found
            logger.debug("No LuckyEngine processes found running")
    except Exception as e:
        logger.debug(f"Error killing WSL processes: {e}")


def _kill_windows_processes() -> None:
    """Kill LuckyEngine processes on Windows."""
    try:
        result = subprocess.run(
            ["taskkill", "/F", "/IM", "LuckyEngine.exe"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            logger.info("Successfully killed LuckyEngine.exe processes")
        elif result.returncode == 128:  # Process not found
            logger.info("No LuckyEngine processes found")
    except Exception as e:
        logger.debug(f"Error killing Windows processes: {e}")


def _kill_macos_processes() -> None:
    """Kill LuckyEngine processes on macOS."""
    try:
        result = subprocess.run(
            ["pkill", "-f", "LuckyEngine"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode == 0:
            logger.info("Successfully killed LuckyEngine processes")
        elif result.returncode == 1:  # No processes found
            logger.info("No LuckyEngine processes found")
        else:
            logger.warning(f"pkill failed: {result.stderr}")

    except subprocess.TimeoutExpired:
        logger.error("pkill command timed out")
    except FileNotFoundError:
        logger.error("pkill command not found")
    except Exception as e:
        logger.error(f"Failed to kill macOS processes: {e}")


def _kill_linux_processes() -> None:
    """Kill LuckyEngine processes on Linux."""
    try:
        result = subprocess.run(
            ["pkill", "-f", "LuckyEngine"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode == 0:
            logger.info("Successfully killed LuckyEngine processes")
        elif result.returncode == 1:  # No processes found
            logger.info("No LuckyEngine processes found")
        else:
            logger.warning(f"pkill failed: {result.stderr}")

    except subprocess.TimeoutExpired:
        logger.error("pkill command timed out")
    except FileNotFoundError:
        logger.error("pkill command not found")
    except Exception as e:
        logger.error(f"Failed to kill Linux processes: {e}")
