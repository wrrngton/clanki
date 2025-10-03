import sys


def cli_handle_error(message: str, code: int) -> None:
    sys.stderr.write(message)
    sys.exit(code)
