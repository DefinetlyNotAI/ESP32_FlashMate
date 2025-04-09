import traceback
import datetime
import sys
import re
from .colors import Colors, Format
from .messages import GENERIC_MESSAGES


class Handler:
    def __init__(self,
                 show_line: bool = False,
                 trace: bool = False,
                 use_timestamp: bool = False,
                 exit_script: bool = False,
                 print_function: callable = print,
                 return_string_rather_than_print: bool = False
                 ):
        # Handler defaults
        self.show_line: bool = show_line
        self.trace: bool = trace
        self.use_timestamp: bool = use_timestamp
        self.exit_script: bool = exit_script
        self.print_function: callable = print_function
        self.return_string_rather_than_print: bool = return_string_rather_than_print

        # Formatter defaults
        # # Color wise
        self.main_color: Colors = Colors.WHITE
        self.message_color: Colors = self.main_color
        self.trace_color: Colors = self.main_color
        self.timestamps_color: Colors = self.main_color
        # # Format wise
        self.main_format: Format = Format.NORMAL
        self.message_text_format: Format = self.main_format
        self.trace_text_format: Format = self.main_format
        self.timestamps_text_format: Format = self.main_format
        # # # Datetime wise
        self.datetime_format: str = "%Y-%m-%d %H:%M:%S"

    def formatter(self,
                  main_format: Format = None,
                  timestamps_format: Format = None,
                  trace_format: Format = None,
                  message_format: Format = None,
                  main_color: Colors = None,
                  timestamps_color: Colors = None,
                  trace_color: Colors = None,
                  message_color: Colors = None,
                  datetime_format: str = None
                  ):
        # Format wise
        self.main_format: Format = main_format or self.main_format  # Default to the main format
        self.timestamps_text_format: Format = timestamps_format or self.main_format
        self.trace_text_format: Format = trace_format or self.main_format
        self.message_text_format: Format = message_format or self.main_format

        # Color wise
        self.main_color: Colors = main_color or self.main_color  # Default to the main main_color
        self.timestamps_color: Colors = timestamps_color or self.main_color
        self.trace_color: Colors = trace_color or self.main_color
        self.message_color: Colors = message_color or self.main_color

        # Datetime format
        self.datetime_format: str = datetime_format if datetime_format else self.datetime_format

    @staticmethod
    def _fallback_message(exc_type):
        exc_name = exc_type.__name__.replace('.', ' ')
        readable = re.sub(r'(?<!^)(?=[A-Z])', ' ', exc_name)
        return f"{readable} occurred [Unknown Exception for handler],"

    def exception(self,
                  msg=None,
                  exit_script=None,
                  quit_code=1,
                  return_string_rather_than_print: bool = False
                  ):
        exc_type, exc_obj, tb = sys.exc_info()
        line: str = tb.tb_lineno if tb and self.show_line else ''
        trace_str: str = ''.join(traceback.format_exception(exc_type, exc_obj, tb)) if self.trace else ''

        readable: str = GENERIC_MESSAGES.get(exc_type, self._fallback_message(exc_type))
        time_str: str = datetime.datetime.now().strftime(self.datetime_format) if self.use_timestamp else ''

        final_msg: str = (
            f"{self.timestamps_text_format}{self.timestamps_color}{time_str}{Colors.RESET}"
            f"{self.message_text_format}{self.message_color}{readable}"
            f"{'' if line == '' else f' on line {line}'}"
            f"{'' if not msg else f' in-detailed info: {msg}'}{Colors.RESET}"
        )

        if self.trace:
            final_msg += (
                f"\n{self.trace_text_format}{self.trace_color}{trace_str}{Colors.RESET}"
            )

        if (return_string_rather_than_print is None and self.return_string_rather_than_print) or return_string_rather_than_print:
            return final_msg
        self.print_function(final_msg)

        if (exit_script is None and self.exit_script) or exit_script:
            sys.exit(quit_code)
