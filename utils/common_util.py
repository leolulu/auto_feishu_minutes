import os
import subprocess
from pathlib import Path


def get_download_path():
    return os.path.join(Path.home(), "Downloads")


def mux_video(file_path):
    def get_command(if_copy):
        if if_copy:
            copy_component = "-c copy -map_chapters"
        else:
            copy_component = ""
        return f'ffmpeg  -i "{file_path}" {copy_component} -1 -y "{output_file_path}" 2>>"{remux_log}"'

    output_file_path = os.path.splitext(file_path)[0] + '.mp4'
    remux_log = os.path.splitext(file_path)[0] + '_remux.log'
    command = get_command(if_copy=True)
    print(f"指令：{command}")
    subprocess.call(command, shell=True)
    if (not os.path.exists(output_file_path)) or (os.path.getsize(output_file_path) == 0):
        print("remux失败，使用重编码！")
        command = get_command(if_copy=False)
        print(f"指令：{command}")
        subprocess.call(command, shell=True)
    os.rename(
        file_path,
        "_remuxed".join(os.path.splitext(file_path))
    )
