import json
from typing import Any, Dict, Optional

from watchdog.events import FileSystemEvent, FileSystemEventHandler

from ..core.models import ObservationModel


class Handler(FileSystemEventHandler):
    """
    Handles file events in the robotdata directory.
    It will read the file and send the contents to the LuckyRobots server.
    """

    timestamp = 0
    chunk_size = 4096  # 4KB
    lucky_robots = None

    @classmethod
    def set_lucky_robots(cls, lr: object) -> None:
        cls.lucky_robots = lr

    @staticmethod
    def on_modified(event: FileSystemEvent) -> None:
        """
        Modified files are saved in the robotdata directory to capture observations
        """
        if not event.is_directory and event.src_path.endswith(".json"):
            # Skip temporary files
            if event.src_path.startswith("."):
                return

            # Get the actual file path (without temporary extensions)
            file_path = event.src_path
            if "~" in file_path:
                file_path = file_path.split("~")[0]

            Handler._process_observation(file_path, event.event_type)

    @staticmethod
    def _process_observation(file_path: str, event_type: str) -> None:
        """
        This method is called when the file watcher has detected a new file.
        It will read the file and send it to the message receiver function.
        """
        # Read the most recent observation from the file
        observation_data = Handler._read_json_tail(file_path)
        if observation_data is not None:
            try:
                # Convert the JSON data to a Pydantic model
                observation = ObservationModel(**observation_data)
                if Handler.lucky_robots is not None:
                    Handler.lucky_robots.subscriber("observation_handler", observation)
                else:
                    print("Warning: lucky_robots is not set in Handler class")
            except Exception as e:
                print(f"Error converting observation data to model: {e}")

    @staticmethod
    def _read_json_tail(file_path: str) -> Optional[Dict[str, Any]]:
        """
        Efficiently read only the most recent JSON object appended to a file
        without reading the entire file.
        """

        try:
            with open(file_path, "rb") as file:
                # Seek to end of file
                file.seek(0, 2)
                file_size = file.tell()

                # Start from the end with a reasonable chunk size
                pos = max(0, file_size - Handler.chunk_size)

                # We need to find the last complete JSON object
                brace_stack = []
                buffer = ""
                last_object_end = file_size

                while pos >= 0:
                    # Read chunk from the file
                    file.seek(pos)
                    chunk = file.read(
                        min(Handler.chunk_size, last_object_end - pos)
                    ).decode("utf-8")

                    # Process the chunk from right to left to find the start of the last object
                    combined = chunk + buffer

                    # Scan backward to find the matching opening brace
                    for i in range(len(combined) - 1, -1, -1):
                        if combined[i] == "}":
                            brace_stack.append("}")
                        elif combined[i] == "{":
                            if brace_stack and brace_stack[-1] == "}":
                                brace_stack.pop()
                                if not brace_stack:
                                    # Found the start of the last complete object
                                    try:
                                        json_str = combined[i : last_object_end - pos]
                                        return json.loads(json_str)
                                    except json.JSONDecodeError:
                                        # Not a valid JSON, continue searching
                                        pass
                            else:
                                brace_stack.append("{")

                    # Keep the unprocessed part for the next iteration
                    buffer = chunk
                    last_object_end = pos + len(chunk)

                    # Move to the previous chunk
                    pos = max(0, pos - Handler.chunk_size)

                    # If we're at the beginning of the file, process remaining content
                    if pos == 0:
                        try:
                            # Try parsing the entire buffer as a JSON object
                            return json.loads(buffer)
                        except json.JSONDecodeError:
                            # Try finding any complete JSON object in the buffer
                            brace_count = 0
                            start_pos = None

                            for i, char in enumerate(buffer):
                                if char == "{" and brace_count == 0:
                                    start_pos = i
                                    brace_count = 1
                                elif char == "{":
                                    brace_count += 1
                                elif char == "}":
                                    brace_count -= 1
                                    if brace_count == 0 and start_pos is not None:
                                        # Found a complete JSON object
                                        json_str = buffer[start_pos : i + 1]
                                        try:
                                            return json.loads(json_str)
                                        except json.JSONDecodeError:
                                            # Not a valid JSON, continue
                                            pass

                            # If we get here, we couldn't find a valid JSON object
                            return None

                # If we couldn't find a valid object
                return None

        except Exception as e:
            print(f"Error reading file {file_path}: {e}")
            return None
