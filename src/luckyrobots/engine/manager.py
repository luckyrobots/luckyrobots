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

LOCK_FILE = os.path.join(tempfile.gettempdir(), "luckyengine_lock")


# ============================================================================
# EngineProcess — class-based lifecycle manager
# ============================================================================


class EngineProcess:
    """Manages a single LuckyEngine process lifecycle.

    Encapsulates process state that was previously held in module globals.
    A default instance is created at module level for backwards compatibility.
    """

    def __init__(self) -> None:
        self._process: Optional[subprocess.Popen] = None
        self._monitor_thread: Optional[threading.Thread] = None
        self._shutdown_event = threading.Event()

    def is_running(self) -> bool:
        """Check if LuckyEngine is currently running."""
        return os.path.exists(LOCK_FILE)

    def launch(
        self,
        scene: str = "ArmLevel",
        robot: str = "so100",
        task: Optional[str] = None,
        executable_path: Optional[str] = None,
        headless: bool = False,
        windowed: bool = True,
        verbose: bool = False,
    ) -> bool:
        """Launch LuckyEngine with the specified parameters.

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
        if self.is_running():
            logger.error(
                "LuckyEngine is already running. "
                "Stop the existing instance or remove the lock file at "
                f"{LOCK_FILE}"
            )
            return False

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
            if platform.system() != "Windows":
                os.chmod(executable_path, 0o755)

            logger.info(f"Launching LuckyEngine: {executable_path}")

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

            if platform.system() == "Windows":
                DETACHED_PROCESS = 0x00000008
                self._process = subprocess.Popen(
                    command,
                    creationflags=DETACHED_PROCESS,
                    close_fds=True,
                    stdout=None if verbose else subprocess.DEVNULL,
                    stderr=None if verbose else subprocess.DEVNULL,
                )
            else:
                self._process = subprocess.Popen(
                    command,
                    start_new_session=True,
                    stdout=None if verbose else subprocess.DEVNULL,
                    stderr=None if verbose else subprocess.DEVNULL,
                )

            self._shutdown_event.clear()
            self._monitor_thread = threading.Thread(
                target=self._monitor_process, daemon=True
            )
            self._monitor_thread.start()

            _create_lock_file(self._process.pid)

            logger.info(f"LuckyEngine started successfully (PID: {self._process.pid})")
            logger.info(f"Scene: {scene}, Robot: {robot}, Task: {task or 'None'}")

            return True

        except Exception as e:
            logger.error(f"Failed to launch LuckyEngine: {e}")
            self.stop()
            return False

    def stop(self) -> bool:
        """Stop the running LuckyEngine instance.

        Returns:
            True if stopped successfully, False otherwise.
        """
        if not self.is_running():
            logger.info("LuckyEngine is not running")
            return True

        try:
            if self._process:
                logger.info("Stopping LuckyEngine...")

                try:
                    self._process.terminate()
                    self._process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    logger.info("Graceful termination timeout, using kill_processes...")
                except Exception:
                    logger.info("Graceful termination failed, using kill_processes...")

                _kill_processes()

            _remove_lock_file()
            return True
        except Exception as e:
            logger.error(f"Error stopping LuckyEngine: {e}")
            return False

    def _monitor_process(self) -> None:
        """Monitor the LuckyEngine process and handle its termination."""
        try:
            while not self._shutdown_event.is_set():
                if self._process is None or self._process.poll() is not None:
                    logger.info("LuckyEngine process has terminated")
                    break
                time.sleep(1)
        except Exception as e:
            logger.error(f"Error in process monitor: {e}")
        finally:
            if not self._shutdown_event.is_set():
                _remove_lock_file()


# ============================================================================
# Module-level convenience (backwards compat)
# ============================================================================

_default = EngineProcess()

launch_luckyengine = _default.launch
stop_luckyengine = _default.stop
is_luckyengine_running = _default.is_running


# ============================================================================
# Standalone helpers (no instance state needed)
# ============================================================================


def find_luckyengine_executable() -> Optional[str]:
    """Automatically find LuckyEngine executable in common locations.

    Checks in order:
    1. LUCKYENGINE_PATH environment variable
    2. LUCKYENGINE_HOME environment variable
    3. System installation paths

    Returns:
        Path to executable if found, None otherwise.
    """
    is_wsl = "microsoft" in platform.uname().release.lower()

    env_path = os.environ.get("LUCKYENGINE_PATH")
    if env_path:
        logger.info(f"Using LUCKYENGINE_PATH environment variable: {env_path}")
        if os.path.exists(env_path):
            return env_path
        logger.warning(f"LUCKYENGINE_PATH points to non-existent file: {env_path}")

    env_home = os.environ.get("LUCKYENGINE_HOME")
    if env_home:
        logger.info(f"Using LUCKYENGINE_HOME environment variable: {env_home}")
        executable = _get_executable_for_platform(env_home, "LuckyEngine", is_wsl)
        if executable and os.path.exists(executable):
            return executable
        logger.warning(f"LUCKYENGINE_HOME does not contain executable: {executable}")

    system_paths = _get_system_paths(is_wsl)
    for path in system_paths:
        if os.path.exists(path):
            logger.info(f"Found LuckyEngine at: {path}")
            return path

    return None


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


def _create_lock_file(pid: int) -> None:
    """Create a lock file with the process ID."""
    with open(LOCK_FILE, "w") as f:
        f.write(str(pid))


def _remove_lock_file() -> None:
    """Remove the lock file."""
    try:
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)
            logger.debug("Lock file removed successfully")
        else:
            logger.debug("Lock file doesn't exist, nothing to remove")
    except Exception as e:
        logger.error(f"Error removing lock file: {e}")


def _kill_processes() -> None:
    """Kill all LuckyEngine processes."""
    system = platform.system()
    is_wsl = "microsoft" in platform.uname().release.lower()

    if is_wsl:
        _kill_wsl_processes()
    elif system == "Windows":
        _kill_windows_processes()
    else:
        # macOS and Linux use identical pkill logic
        _kill_unix_processes()


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


def _kill_unix_processes() -> None:
    """Kill LuckyEngine processes on macOS or Linux."""
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
        logger.error(f"Failed to kill processes: {e}")
