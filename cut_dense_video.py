import os
import shutil
import subprocess
import sys
import threading

from tqdm import tqdm

from utils.read_srt import read_srt


def concat_video(folder_path, simple_postfix=False, if_print=True):
    _cwd = os.getcwd()
    os.chdir(folder_path)
    if if_print:
        print(f"工作目录：{os.getcwd()}")

    if os.path.exists('filelist.txt'):
        os.remove('filelist.txt')
    with open('filelist.txt', 'a', encoding='utf-8') as f:
        for i in os.listdir('.'):
            if i in ['filelist.txt', 'cut_video.log']:
                continue
            f.write(f"file '{i}'\n")
    file_name = f"{os.path.basename(folder_path)}_cut_dense.mp4"
    if simple_postfix:
        file_name = file_name.replace("_concat_cut_dense", "_ccd")
    log_path = os.path.abspath(os.path.join(folder_path, "concat_video.log"))
    command = f'ffmpeg -f concat -safe 0 -i filelist.txt -c copy -y "{file_name}" 2>>"{log_path}"'
    if if_print:
        print(f"指令：{command}\n")
    subprocess.call(command, shell=True)
    shutil.move(file_name, os.path.dirname(folder_path))
    os.chdir(_cwd)
    return os.path.join(os.path.dirname(folder_path), file_name)


def cut_video(video_path, srt_path, if_print=True):
    video_path = os.path.abspath(video_path)
    video_name = os.path.basename(video_path)
    output_dir = os.path.join(os.path.dirname(video_path), os.path.splitext(video_name)[0]+'_concat')
    if not os.path.exists(output_dir):
        os.mkdir(output_dir)
    if srt_path is None:
        srt_path = os.path.splitext(video_path)[0] + '.srt'
    srt_datas = read_srt(srt_path)
    for idx, srt_data in enumerate(tqdm(srt_datas)):
        start_time, end_time, content = srt_data
        output_video_path = os.path.join(
            output_dir,
            "".join([
                os.path.splitext(video_name)[0],
                f"_{str(idx).zfill(6)}",
                os.path.splitext(video_name)[1]
            ])
        )
        log_path = os.path.abspath(os.path.join(output_dir, "cut_video.log"))
        command = f'ffmpeg -y -ss {start_time} -to {end_time} -i "{video_path}" -preset veryfast "{output_video_path}" 2>>"{log_path}"'
        if if_print:
            print(f"\n{command}")
        subprocess.call(command, shell=True)
    return output_dir


def cli_run(video_path, srt_path=None):
    output_dir = cut_video(video_path, srt_path)
    concat_video(output_dir)


def invoke_run(video_path, srt_path=None, delete_assembly_folder=True, lock_=threading.Lock()):
    output_dir = cut_video(video_path, srt_path, if_print=False)
    with lock_:
        result_file_path = concat_video(output_dir, simple_postfix=True, if_print=False)
    if delete_assembly_folder:
        shutil.rmtree(output_dir)
    return result_file_path


if __name__ == '__main__':
    if len(sys.argv) == 2:
        cli_run(sys.argv[1])
    elif len(sys.argv) == 3:
        cli_run(sys.argv[1], sys.argv[2])
