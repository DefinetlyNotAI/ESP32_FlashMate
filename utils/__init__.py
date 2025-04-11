from utils.exception import Handler, Colors
from utils.tprint import TPrint, TPrintColors, separator


DEBUG = True

tprint = TPrint(
    color_scheme={
        'info': TPrintColors.WHITE,
        'warning': TPrintColors.YELLOW,
        'error': TPrintColors.RED,
        'debug': TPrintColors.CYAN,
        'critical': TPrintColors.BRIGHT_RED,
        'success': TPrintColors.BRIGHT_GREEN,
        'input': TPrintColors.GREEN
    },
    debug_mode=DEBUG,
    purge_old_logs=True
)

handler = Handler(
    show_line=True,
    print_function=tprint.critical,
    trace=DEBUG
)

handler.formatter(
    message_color=Colors.RED,
)
