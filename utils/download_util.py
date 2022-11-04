from pathlib import Path
import os


def get_download_path():
    return os.path.join(Path.home(), "Downloads")
