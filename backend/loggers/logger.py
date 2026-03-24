from datetime import datetime
import traceback
from typing import Dict

from config import PATH_CONFIG

_logs_path = PATH_CONFIG.LOGS_PATH / datetime.now().strftime('%Y-%m-%d_%H%M%S')
_logs_path.mkdir(exist_ok=True, parents=True)
class Logger:
    def __init__(self, name: str, log_format='{date} [{level}] - {message}'):
        self.name = name
        self.log_format = log_format

        self.file_path = _logs_path / f"{name}.log"
        with open(self.file_path, 'w'):
            pass

    def _write_log(self, content: str):
        with open(self.file_path, 'a', encoding='utf-8') as f:
            f.write(content + '\n')
    
    def info(self, message):
        content = self.log_format.format(
            date=str(datetime.now()),
            level='INFO',
            message=message
        )
        self._write_log(content)
    
    def error(self, error):
        content = self.log_format.format(
            date=str(datetime.now()),
            level='ERROR',
            message=traceback.format_exc()
        )
        self._write_log(content)
    def warning(self, message):
        content = self.log_format.format(
            date=str(datetime.now()),
            level='INFO',
            message=message
        )
        self._write_log(content)

_loggers: Dict[str, Logger] = {}

def get_logger(name: str) -> Logger:
    if name in _loggers:
        return _loggers[name]
    _loggers[name] = Logger(name)
    return _loggers[name]

