"""Parameter server implementation for LuckyRobots.

This module provides a centralized parameter server for storing configuration
parameters that can be accessed by all nodes in the system, similar to ROS.
"""

import json
import logging
import os
import threading
from typing import Any, Dict, List

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("param_server")


class ParameterServer:
    """Singleton class that implements a ROS-like parameter server"""

    _instance = None
    _lock = threading.RLock()
    _params: Dict[str, Any] = {}

    def __new__(cls):
        """Ensure only one instance of ParameterServer exists"""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(ParameterServer, cls).__new__(cls)
            return cls._instance

    def __init__(self):
        """Initialize the parameter server"""
        # Already initialized if instance exists
        if hasattr(self, "_initialized"):
            return

        self._params = {}
        self._initialized = True
        logger.info("Parameter server initialized")

    def set_param(self, name: str, value: Any) -> None:
        """Set a parameter value.

        Args:
            name: Parameter name (can be namespaced with '/')
            value: Parameter value (must be JSON serializable)
        """
        with self._lock:
            # Handle namespaced parameters
            if "/" in name and name != "/":
                parts = name.strip("/").split("/")
                current = self._params

                # Navigate to the right level in the parameter tree
                for i, part in enumerate(parts[:-1]):
                    if part not in current:
                        current[part] = {}
                    elif not isinstance(current[part], dict):
                        # Convert to dict if it wasn't already
                        current[part] = {"_value": current[part]}
                    current = current[part]

                # Set the final parameter
                current[parts[-1]] = value
            else:
                # Simple case - top level parameter
                self._params[name.strip("/")] = value

        logger.debug(f"Set parameter: {name} = {value}")

    def get_param(self, name: str, default: Any = None) -> Any:
        """Get a parameter value.

        Args:
            name: Parameter name (can be namespaced with '/')
            default: Default value to return if parameter doesn't exist

        Returns:
            The parameter value, or default if not found
        """
        with self._lock:
            # Handle namespaced parameters
            if "/" in name and name != "/":
                parts = name.strip("/").split("/")
                current = self._params

                # Navigate to the right level in the parameter tree
                for part in parts:
                    if part not in current:
                        return default
                    current = current[part]

                return current
            else:
                # Simple case - top level parameter
                return self._params.get(name.strip("/"), default)

    def has_param(self, name: str) -> bool:
        """Check if a parameter exists.

        Args:
            name: Parameter name to check

        Returns:
            True if the parameter exists, False otherwise
        """
        with self._lock:
            # Handle namespaced parameters
            if "/" in name and name != "/":
                parts = name.strip("/").split("/")
                current = self._params

                # Navigate to the right level in the parameter tree
                for part in parts:
                    if part not in current:
                        return False
                    current = current[part]

                return True
            else:
                # Simple case - top level parameter
                return name.strip("/") in self._params

    def delete_param(self, name: str) -> bool:
        """Delete a parameter.

        Args:
            name: Parameter name to delete

        Returns:
            True if parameter was deleted, False if it didn't exist
        """
        with self._lock:
            # Handle namespaced parameters
            if "/" in name and name != "/":
                parts = name.strip("/").split("/")
                current = self._params
                parents = []

                # Navigate to the right level in the parameter tree
                for part in parts[:-1]:
                    if part not in current:
                        return False
                    parents.append((current, part))
                    current = current[part]

                # Delete the parameter
                if parts[-1] in current:
                    del current[parts[-1]]

                    # Clean up empty dictionaries
                    for parent, key in reversed(parents):
                        if not parent[key]:
                            del parent[key]

                    logger.debug(f"Deleted parameter: {name}")
                    return True
                return False
            else:
                # Simple case - top level parameter
                name = name.strip("/")
                if name in self._params:
                    del self._params[name]
                    logger.debug(f"Deleted parameter: {name}")
                    return True
                return False

    def get_param_names(self) -> List[str]:
        """Get a list of all parameter names.

        Returns:
            A list of all parameter names
        """
        with self._lock:
            result = []

            def _collect_names(params: Dict[str, Any], prefix: str = ""):
                for key, value in params.items():
                    full_name = f"{prefix}/{key}" if prefix else key
                    if isinstance(value, dict):
                        _collect_names(value, full_name)
                    else:
                        result.append(full_name)

            _collect_names(self._params)
            return result

    def load_from_file(self, filename: str) -> bool:
        """Load parameters from a JSON file.

        Args:
            filename: Path to the JSON file

        Returns:
            True if successful, False otherwise
        """
        try:
            with open(filename, "r") as f:
                params = json.load(f)

            with self._lock:
                self._params.update(params)

            logger.info(f"Loaded parameters from file: {filename}")
            return True
        except Exception as e:
            logger.error(f"Error loading parameters from file {filename}: {e}")
            return False

    def save_to_file(self, filename: str) -> bool:
        """Save parameters to a JSON file.

        Args:
            filename: Path to the JSON file

        Returns:
            True if successful, False otherwise
        """
        try:
            os.makedirs(os.path.dirname(os.path.abspath(filename)), exist_ok=True)

            with self._lock:
                with open(filename, "w") as f:
                    json.dump(self._params, f, indent=2)

            logger.info(f"Saved parameters to file: {filename}")
            return True
        except Exception as e:
            logger.error(f"Error saving parameters to file {filename}: {e}")
            return False


# Create a global instance
param_server = ParameterServer()


# Convenience functions for easier access
def get_param(name: str, default: Any = None) -> Any:
    """Get a parameter value."""
    return param_server.get_param(name, default)


def set_param(name: str, value: Any) -> None:
    """Set a parameter value."""
    param_server.set_param(name, value)


def has_param(name: str) -> bool:
    """Check if a parameter exists."""
    return param_server.has_param(name)


def delete_param(name: str) -> bool:
    """Delete a parameter."""
    return param_server.delete_param(name)


def get_param_names() -> List[str]:
    """Get a list of all parameter names."""
    return param_server.get_param_names()


def load_from_file(filename: str) -> bool:
    """Load parameters from a JSON file."""
    return param_server.load_from_file(filename)


def save_to_file(filename: str) -> bool:
    """Save parameters to a JSON file."""
    return param_server.save_to_file(filename)
