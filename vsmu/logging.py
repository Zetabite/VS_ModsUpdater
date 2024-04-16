from datetime import datetime
from rich import print as rprint
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


class LogEnvironment(IntEnum):
    CONSOLE = 0b01,
    DISK    = 0b10,
    BOTH    = 0b11


DEFAULT_LOGGING_ENVIRONMENT = LogEnvironment.BOTH
global_logging_environment = DEFAULT_LOGGING_ENVIRONMENT


class LoggerInterface:
    def __init__(self, lang_handler: languagehandler.LanguageHandler = languagehandler.LanguageHandler('en_US'), logging_level: LoggingLevel = DEFAULT_LOGGING_LEVEL):
        self.lang_handler = lang_handler
        self.logging_level = logging_level

    def set_language_handler(self, lang_handler: languagehandler.LanguageHandler = languagehandler.LanguageHandler) -> None:
        self.lang_handler = lang_handler
    
    def info(self, logging_level: LoggingLevel = global_logging_level) -> bool:
        return (logging_level & LoggingLevel.INFO) > 0

    def warning(self, logging_level: LoggingLevel = global_logging_level) -> bool:
        return (logging_level & LoggingLevel.WARNING) > 0
    
    def error(self, logging_level: LoggingLevel = global_logging_level) -> bool:
        return (logging_level & LoggingLevel.ERROR) > 0
    
    def debug(self, logging_level: LoggingLevel = global_logging_level) -> bool:
        return (logging_level & LoggingLevel.DEBUG) > 0


class Console(LoggerInterface):
    def __init__(self, lang_handler: languagehandler.LanguageHandler = languagehandler.LanguageHandler('en_US'), logging_level: LoggingLevel = DEFAULT_LOGGING_LEVEL):
        LoggerInterface.__init__(lang_handler=lang_handler, logging_level=logging_level)
        self.env = LogEnvironment.CONSOLE
    
    def info(self, msg: str, logging_level: LoggingLevel = global_logging_level, env: LogEnvironment = global_logging_environment, custom: bool = False) -> None:
        if not LoggerInterface.info(logging_level=logging_level):
            return

        # Print to console
        if env & LogEnvironment.CONSOLE:
            rprint(msg)
    
    def warning(self, msg: str, logging_level: LoggingLevel = global_logging_level, env: LogEnvironment = global_logging_environment, custom: bool = False) -> None:
        if not LoggerInterface.warning(logging_level=logging_level):
            return

        # Print to console
        if env & LogEnvironment.CONSOLE:
            rprint(msg)
    
    def error(self, msg: str, logging_level: LoggingLevel = global_logging_level, env: LogEnvironment = global_logging_environment, custom: bool = False) -> None:
        if not LoggerInterface.error(logging_level=logging_level):
            return

        # Print to console
        if env & LogEnvironment.CONSOLE:
            rprint(msg)
                
    
    def debug(self, msg: str, logging_level: LoggingLevel = global_logging_level, env: LogEnvironment = global_logging_environment, custom: bool = False) -> None:
        if not LoggerInterface.debug(logging_level=logging_level):
            return

        # Print to console
        if env & LogEnvironment.CONSOLE:
            rprint(msg)


class Log(LoggerInterface):
    def __init__(self, lang_handler: languagehandler.LanguageHandler = languagehandler.LanguageHandler('en_US'), logging_level: LoggingLevel = DEFAULT_LOGGING_LEVEL):
        LoggerInterface.__init__(lang_handler=lang_handler, logging_level=logging_level)
        self.env = LogEnvironment.LOG
    
    def info(self, msg: str, logging_level: LoggingLevel = global_logging_level, env: LogEnvironment = global_logging_environment, custom: bool = False) -> None:
        if not LoggerInterface.info(logging_level=logging_level):
            return

        # Write to disk
        if env & LogEnvironment.DISK:
            self.write_log(msg)
    
    def warning(self, msg: str, logging_level: LoggingLevel = global_logging_level, env: LogEnvironment = global_logging_environment, custom: bool = False) -> None:
        if not LoggerInterface.warning(logging_level=logging_level):
            return

        # Write to disk
        if env & LogEnvironment.DISK:
            self.write_log(msg)
    
    def error(self, msg: str, logging_level: LoggingLevel = global_logging_level, env: LogEnvironment = global_logging_environment, custom: bool = False) -> None:
        if not LoggerInterface.error(logging_level=logging_level):
            return

        # Write to disk
        if env & LogEnvironment.DISK:
            rprint(f"[red]{self.lang_handler.get('error_msg')}[/red]")
            self.write_log(msg)
    
    def debug(self, msg: str, logging_level: LoggingLevel = global_logging_level, env: LogEnvironment = global_logging_environment, custom: bool = False) -> None:
        if not LoggerInterface.debug(logging_level=logging_level):
            return

        # Write to disk
        if env & LogEnvironment.DISK:
            self.write_log(msg)

    # Creation of a logfile
    @staticmethod
    def write_log(msg: str) -> None:
        log_path = pathhandler.get_logs_path().joinpath(f'debug-log-{datetime.today().strftime("%Y%m%d%H%M%S")}.txt')

        with open(log_path, 'a', encoding='UTF-8') as log_file:
            log_file.write(f'{datetime.today().strftime("%Y-%m-%d %H:%M:%S")} : {msg}\n')


class Logger(Console, Log):
    def __init__(self, lang_handler: languagehandler.LanguageHandler = languagehandler.LanguageHandler('en_US'), logging_level: LoggingLevel = DEFAULT_LOGGING_LEVEL, env: LogEnvironment = DEFAULT_LOGGING_ENVIRONMENT):
        global global_logging_level, global_logging_environment
        self.logging_level = logging_level
        self.env = env
    
        global_logging_level = logging_level
        global_logging_environment = env
        self.lang_handler = lang_handler
    
    def info(self, msg: str, logging_level: LoggingLevel = global_logging_level, env: LogEnvironment = global_logging_environment, custom: bool = False) -> None:
        if not ((logging_level & LoggingLevel.INFO) > 0):
            return

        # Write to disk
        if env & LogEnvironment.DISK:
            self.write_log(msg)
        
        # Print to console
        if env & LogEnvironment.CONSOLE:
            rprint(msg)
    
    def warning(self, msg: str, logging_level: LoggingLevel = global_logging_level, env: LogEnvironment = global_logging_environment, custom: bool = False) -> None:
        if not ((logging_level & LoggingLevel.WARNING) > 0):
            return

        # Write to disk
        if env & LogEnvironment.DISK:
            self.write_log(msg)
        
        # Print to console
        if env & LogEnvironment.CONSOLE:
            rprint(msg)
    
    def error(self, msg: str, logging_level: LoggingLevel = global_logging_level, env: LogEnvironment = global_logging_environment, custom: bool = False) -> None:
        if not ((logging_level & LoggingLevel.ERROR) > 0):
            return

        # Write to disk
        if env & LogEnvironment.DISK:
            rprint(f"[red]{self.lang_handler.get('error_msg')}[/red]")
            self.write_log(msg)
        
        # Print to console
        if env & LogEnvironment.CONSOLE:
            rprint(msg)
                
    
    def debug(self, msg: str, logging_level: LoggingLevel = global_logging_level, env: LogEnvironment = global_logging_environment, custom: bool = False) -> None:
        if not ((logging_level & LoggingLevel.DEBUG) > 0):
            return 

        # Write to disk
        if env & LogEnvironment.DISK:
            self.write_log(msg)
        
        # Print to console
        if env & LogEnvironment.CONSOLE:
            rprint(msg)
