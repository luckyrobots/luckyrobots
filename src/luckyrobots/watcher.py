from watchdog.observers import Observer
from .handler import Handler

class Watcher:
    def __init__(self, directory_path: str) -> None:
        self.observer = Observer()
        self.directory_path = directory_path

    def run(self) -> None:
        """
        This method is used to run the file watcher.
        It will watch the directory for changes and call the Handler class to process the files.
        """
        event_handler = Handler()
        self.observer.schedule(event_handler, self.directory_path, recursive=False)
        self.observer.start()
        
        try:
            while self.observer.is_alive():
                self.observer.join(1)
        except KeyboardInterrupt:
            self.observer.stop()
        
        self.observer.join()