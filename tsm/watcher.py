import time
from pathlib import Path

from loguru import logger
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer


class FileWatcher:
    def __init__(self, file_path: Path, callback):
        self.file_path = Path(file_path)
        self.callback = callback
        self._observer = Observer()
        self._event_handler = _FileChangeHandler(self.file_path, self.callback)
        self._running = False

    def start(self):
        if not self._running:
            logger.debug(f"Starting watcher for {self.file_path}")
            self._observer.schedule(
                self._event_handler, str(self.file_path.parent), recursive=False
            )
            self._observer.start()
            self._running = True
            try:
                while self._running:
                    time.sleep(0.5)
            except KeyboardInterrupt:
                self.stop()

    def stop(self):
        if self._running:
            logger.debug(f"Stopping watcher for {self.file_path}")
            self._observer.stop()
            self._observer.join()
            self._running = False


class _FileChangeHandler(FileSystemEventHandler):
    def __init__(self, file_path: Path, callback):
        super().__init__()
        self.file_path = file_path.resolve()
        self.callback = callback

    def _handle(self, event):
        if Path(event.src_path).resolve() == self.file_path:
            logger.debug(f"Detected {event.event_type} event for {self.file_path}")
            self.callback()

    def on_modified(self, event):
        self._handle(event)

    def on_created(self, event):
        self._handle(event)

    def on_moved(self, event):
        # event.dest_path is the new path after move
        if Path(getattr(event, "dest_path", "")) == self.file_path:
            logger.debug(f"Detected moved event to {self.file_path}")
            self.callback()
        else:
            self._handle(event)
