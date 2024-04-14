from datetime import datetime
from rich import print as rprint
from rich.prompt import Prompt
from enum import IntEnum

import vsmu.path_handler as pathhandler
import vsmu.language_handler as languagehandler


class LoggingLevel(IntEnum):
    INFO    = 0b0001,
    WARNING = 0b0010,
    ERROR   = 0b0100,
    DEBUG   = 0b1000,
    ALL     = 0b1111


DEFAULT_LOGGING_LEVEL = LoggingLevel.ALL & ~LoggingLevel.DEBUG
global_logging_level = DEFAULT_LOGGING_LEVEL

class LogEnviroment(IntEnum):
    CONSOLE = 0b01,
    DISK    = 0b10,
    BOTH    = 0b11


class Logger:
    def __init__(self, logging_level: LoggingLevel = DEFAULT_LOGGING_LEVEL):
        global global_logging_level

        global_logging_level = logging_level
        self.lang_handler = languagehandler.LanguageHandler('en_US')
    
    def set_language_handler(self, lang_handler: languagehandler.LanguageHandler = languagehandler.LanguageHandler) -> None:
        self.lang_handler = lang_handler
    
    def info(self, msg: str, logging_level: LoggingLevel = global_logging_level, env: LogEnviroment = LogEnviroment.BOTH, custom = False) -> None:
        if not ((logging_level & LoggingLevel.INFO) > 0):
            return

        # Write to disk
        if env & LogEnviroment.DISK:
            self.write_log(msg)
        
        # Print to console
        if env & LogEnviroment.CONSOLE:
            rprint(msg)
    
    def warning(self, msg: str, logging_level: LoggingLevel = global_logging_level, env: LogEnviroment = LogEnviroment.BOTH, custom = False) -> None:
        if not ((logging_level & LoggingLevel.WARNING) > 0):
            return

        # Write to disk
        if env & LogEnviroment.DISK:
            self.write_log(msg)
        
        # Print to console
        if env & LogEnviroment.CONSOLE:
            rprint(msg)
    
    def error(self, msg: str, logging_level: LoggingLevel = global_logging_level, env: LogEnviroment = LogEnviroment.BOTH, custom = False) -> None:
        if not ((logging_level & LoggingLevel.ERROR) > 0):
            return

        # Write to disk
        if env & LogEnviroment.DISK:
            rprint(f"[red]{self.lang_handler.get('error_msg')}[/red]")
            self.write_log(msg)
        
        # Print to console
        if env & LogEnviroment.CONSOLE:
            rprint(msg)
                
    
    def debug(self, msg: str, logging_level: LoggingLevel = global_logging_level, env: LogEnviroment = LogEnviroment.BOTH, custom = False) -> None:
        if not ((logging_level & LoggingLevel.DEBUG) > 0):
            return 

        # Write to disk
        if env & LogEnviroment.DISK:
            self.write_log(msg)
        
        # Print to console
        if env & LogEnviroment.CONSOLE:
            rprint(msg)

    # Creation of a logfile
    @staticmethod
    def write_log(msg: str) -> None:
        log_path = pathhandler.get_logs_path().joinpath(f'debug-log-{datetime.today().strftime("%Y%m%d%H%M%S")}.txt')

        with open(log_path, 'a', encoding='UTF-8') as log_file:
            log_file.write(f'{datetime.today().strftime("%Y-%m-%d %H:%M:%S")} : {msg}\n')

