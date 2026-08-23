"""Captura erros não tratados em arquivo de log local."""
import os
import sys
import threading
import traceback

LOG_PATH = os.path.join(
    os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share")),
    "powerzap",
    "error.log",
)


def _write(header: str):
    try:
        os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(f"\n=== {header} ===\n")
            traceback.print_exc(file=f)
    except Exception:
        pass


def install():
    def hook(exc_type, exc_value, exc_tb):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_tb)
            return
        sys.stderr.write("".join(traceback.format_exception(exc_type, exc_value, exc_tb)))
        _write(f"EXCECAO thread principal {threading.current_thread().name}")

    def threading_hook(args):
        _write(f"EXCECAO thread {args.thread.name}")

    sys.excepthook = hook
    threading.excepthook = threading_hook
