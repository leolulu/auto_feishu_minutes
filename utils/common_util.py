import os
import subprocess
from pathlib import Path


def get_download_path():
    return os.path.join(Path.home(), "Downloads")


def mux_video(file_path):
    output_file_path = os.path.splitext(file_path)[0] + '.mp4'
    remux_log = os.path.splitext(file_path)[0] + '_remux.log'
    command = f'ffmpeg  -i "{file_path}" -c copy -y "{output_file_path}" 2>>"{remux_log}"'
    print(f"指令：{command}\n")
    subprocess.call(command, shell=True)
    os.rename(
        file_path,
        "_remuxed".join(os.path.splitext(file_path))
    )
