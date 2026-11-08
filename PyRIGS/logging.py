import datetime
import logging
import re
from pathlib import Path

from django.core.exceptions import DisallowedHost


class SkipDisallowedHost(logging.Filter):
    """Drop log records caused by requests with an invalid Host header"""

    def filter(self, record):
        exc_info = record.exc_info
        return not (exc_info and isinstance(exc_info[1], DisallowedHost))


class DailyFileHandler(logging.Handler):
    """
    Writes to ``<directory>/<prefix>.<YYYY-MM-DD>.log`` (UTC date), starting a new file each day and deleting files
    older than ``backup_count`` days.

    The stdlib rotating handlers rename the live file, which corrupts it when several gunicorn workers share it. Here
    nothing is ever renamed: every process appends to the file named for today's date, so they agree without
    coordinating, and each line is a single append.
    """

    def __init__(self, directory, prefix="access", backup_count=30):
        super().__init__()
        self.directory = Path(directory)
        self.prefix = prefix
        self.backup_count = backup_count
        self.pattern = re.compile(rf"^{re.escape(prefix)}\.(\d{{4}}-\d{{2}}-\d{{2}})\.log$")
        self.directory.mkdir(parents=True, exist_ok=True)
        self.day = None
        self.stream = None

    def path_for(self, day):
        return self.directory / f"{self.prefix}.{day.isoformat()}.log"

    def emit(self, record):
        try:
            day = datetime.datetime.fromtimestamp(record.created, datetime.timezone.utc).date()
            if day != self.day:
                self.roll_to(day)
            self.stream.write(self.format(record) + "\n")
            self.stream.flush()
        except Exception:
            self.handleError(record)

    def roll_to(self, day):
        if self.stream:
            self.stream.close()
        self.stream = open(self.path_for(day), "a", encoding="utf-8")
        self.day = day
        self.prune(day)

    def prune(self, today):
        oldest_kept = today - datetime.timedelta(days=self.backup_count - 1)
        for path in self.directory.iterdir():
            match = self.pattern.match(path.name)
            if match and datetime.date.fromisoformat(match.group(1)) < oldest_kept:
                path.unlink(missing_ok=True)

    def close(self):
        with self.lock:
            if self.stream:
                self.stream.close()
                self.stream = None
        super().close()
