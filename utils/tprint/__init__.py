from __future__ import annotations
import datetime
from .colors import TPrintColors


# TPrint class handles the printing and logging mechanism with customizable color schemes.
class TPrint:
    """
    A class that handles printing messages to the console with customizable colors,
    logging options, and timestamp support. Messages can be styled with various colors
    and printed at different log levels (info, warning, error, etc.). Optionally, messages
    can be logged to a file.
    """

    def __init__(self,
                 color_scheme: dict[str, str] = None,
                 debug_mode: bool = False,
                 log_file: str | None = None,
                 use_timestamps: bool = False,
                 purge_old_logs: bool = False,
                 ):
        """
        Initializes the TPrint instance with optional custom color schemes and logging options.

        Args:
            color_scheme (dict): Custom color scheme dictionary for log levels (default: None).
            debug_mode (bool): Flag to enable/disable debug mode (default: False).
            log_file (str): Path to the log file (default: None).
            use_timestamps (bool): Flag to enable/disable timestamp usage in logs (default: False).
            purge_old_logs (bool): Flag to enable/disable old log purging (default: False).
        """
        self.default_colors = {
            'info': TPrintColors.WHITE,
            'warning': TPrintColors.YELLOW,
            'error': TPrintColors.RED,
            'debug': TPrintColors.CYAN,
            'input': TPrintColors.GREEN,
            'critical': TPrintColors.RED,
            'success': TPrintColors.GREEN
        }

        # Validate the color_scheme dictionary
        if color_scheme is not None and isinstance(color_scheme, dict):
            unknown_keys = set(color_scheme) - set(self.default_colors)
            if unknown_keys:
                raise ValueError(f"Unknown keys in color_scheme: {unknown_keys}")

        # Use user-supplied scheme or merge it with defaults
        self.color_scheme = {**self.default_colors, **(color_scheme or {})}
        self.debug_mode = debug_mode
        self.log_file = log_file
        self.use_timestamps = use_timestamps
        self.purge_old_logs = purge_old_logs

    @staticmethod
    def __print_message(message, color: TPrintColors, symbol: str, timestamp: str = None, style=None):
        """
        Prints the formatted message to the console with the specified color, symbol, and timestamp.

        Args:
            message (str): The message to print.
            color (str): The ANSI escape code for the desired color.
            symbol (str): A symbol representing the log level (e.g., "*", "!", "x").
            timestamp (str): The timestamp to prepend to the message (default: None).
            style (str): The text style to apply (default: None).
        """
        # Apply style (bold, underline, reversed) if provided
        styled_message = f"{style}{message}" if style else message
        # Print the formatted message with the correct color and timestamp
        if timestamp:
            print(f"{color}[{symbol}] [{timestamp}] {styled_message}{TPrintColors.RESET}")
        else:
            print(f"{color}[{symbol}] {styled_message}{TPrintColors.RESET}")

    def __log_message(self, message, symbol: str, timestamp=None):
        """
        Logs the message to a file if logging is enabled.

        Args:
            message (str): The message to log.
            symbol (str): The symbol representing the log level.
            timestamp (str): The timestamp to prepend to the message (default: None).
        """
        # Optionally log messages to a file
        if self.log_file:
            with open(self.log_file, 'a', encoding='utf-8') as log:
                if timestamp:
                    log.write(f"[{symbol}] [{timestamp}] {message}\n")
                else:
                    log.write(f"[{symbol}] {message}\n")

    # Log levels
    def info(self, message, log_to_file: bool = None, style: TPrintColors = None):
        """
        Logs an informational message.

        Args:
            message (str): The message to log.
            log_to_file (bool): Whether to log the message to a file (default: None).
            style (str): The style to apply to the message (default: None).
        """
        if log_to_file is None:
            log_to_file = self.log_file
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S') if self.use_timestamps else None
        self.__print_message(message, self.color_scheme['info'], "*", timestamp, style)
        if log_to_file:
            self.__log_message(message, "*", timestamp)

    def warning(self, message, log_to_file: bool = None, style: TPrintColors = None):
        """
        Logs a warning message.

        Args:
            message (str): The message to log.
            log_to_file (bool): Whether to log the message to a file (default: False).
            style (str): The style to apply to the message (default: None).
        """
        if log_to_file is None:
            log_to_file = self.log_file
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S') if self.use_timestamps else None
        self.__print_message(message, self.color_scheme['warning'], "!", timestamp, style)
        if log_to_file:
            self.__log_message(message, "!", timestamp)

    def error(self, message, log_to_file: bool = None, style: TPrintColors = None):
        """
        Logs an error message.

        Args:
            message (str): The message to log.
            log_to_file (bool): Whether to log the message to a file (default: False).
            style (str): The style to apply to the message (default: None).
        """
        if log_to_file is None:
            log_to_file = self.log_file
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S') if self.use_timestamps else None
        self.__print_message(message, self.color_scheme['error'], "x", timestamp, style)
        if log_to_file:
            self.__log_message(message, "x", timestamp)

    def debug(self, message, log_to_file: bool = None, style: TPrintColors = None):
        """
        Logs a debug message if debug mode is enabled.

        Args:
            message (str): The message to log.
            log_to_file (bool): Whether to log the message to a file (default: False).
            style (str): The style to apply to the message (default: None).
        """
        if log_to_file is None:
            log_to_file = self.log_file
        if self.debug_mode:  # Only print debug messages if debug mode is enabled
            timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S') if self.use_timestamps else None
            self.__print_message(message, self.color_scheme['debug'], "-", timestamp, style)
            if log_to_file:
                self.__log_message(message, "-", timestamp)

    def critical(self, message, log_to_file: bool = None, style: TPrintColors = None):
        """
        Logs a critical message.

        Args:
            message (str): The message to log.
            log_to_file (bool): Whether to log the message to a file (default: False).
            style (str): The style to apply to the message (default: None).
        """
        if log_to_file is None:
            log_to_file = self.log_file
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S') if self.use_timestamps else None
        self.__print_message(message, self.color_scheme['critical'], "x", timestamp, style)
        if log_to_file:
            self.__log_message(message, "x", timestamp)

    def success(self, message, log_to_file: bool = None, style: TPrintColors = None):
        """
        Logs a success message.

        Args:
            message (str): The message to log.
            log_to_file (bool): Whether to log the message to a file (default: False).
            style (str): The style to apply to the message (default: None).
        """
        if log_to_file is None:
            log_to_file = self.log_file
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S') if self.use_timestamps else None
        self.__print_message(message, self.color_scheme['success'], "✓", timestamp, style)
        if log_to_file:
            self.__log_message(message, "✓", timestamp)

    def input(self, message, log_to_file: bool = None) -> str:
        """
        Prompts the user for input with a colored message.

        Args:
            message (str): The message to display when prompting for input.
            log_to_file (bool): Whether to log the message to a file (default: False).

        Returns:
            str: The user's input.
        """
        answer = input(f"{self.color_scheme['input']}[?] {message}")
        if log_to_file is None:
            log_to_file = self.log_file

        if log_to_file:
            timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S') if self.use_timestamps else None
            self.__log_message(message, "?", timestamp)
            self.__log_message(answer, ">", timestamp)

        return answer

    # Setting dynamic updates
    def formatter(self,
                  color_scheme: dict[str, str] = None,
                  debug_mode: bool = None,
                  use_timestamps: bool = None,
                  log_file: str | None = None,
                  purge_old_logs: bool = None
                  ):
        """
        Modify previously set settings dynamically.

        Args:
            debug_mode (bool): The new debug mode flag.
            color_scheme (dict): The new color scheme.
            use_timestamps (bool): The new timestamp flag.
            log_file (str | None): The new log file path or None to disable logging.
            purge_old_logs (bool): The new purge flag.

        """
        # Allows for dynamic color updates
        if color_scheme:
            self.color_scheme.update(color_scheme)
            unknown_keys = set(color_scheme) - set(self.default_colors)
            if unknown_keys:
                raise ValueError(f"Unknown keys in color_scheme: {unknown_keys}")

        self.use_timestamps = use_timestamps if use_timestamps is not None else self.use_timestamps
        self.log_file = log_file if log_file is not None else self.log_file
        self.purge_old_logs = purge_old_logs if purge_old_logs is not None else self.purge_old_logs
        self.debug_mode = debug_mode if debug_mode is not None else self.debug_mode


def separator(title, color: TPrintColors = TPrintColors.MAGENTA):
    """
    Prints a separator with a title in bold and specified color.

    Args:
        title (str): The title to display in the separator.
        color (TPrintColors): The color to use - defaults to magenta.
    """
    print(f"{TPrintColors.BOLD}{color}--- {title} ---{TPrintColors.RESET}")
