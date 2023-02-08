import argparse
import os
import shutil
import subprocess
import threading
from queue import Queue

from tqdm import tqdm

from utils.sub_util import read_srt


def concat_video(folder_path, simple_postfix=False, if_print=True, queue_=Queue()):
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
    queue_.put(os.path.join(os.path.dirname(folder_path), file_name))
    return os.path.join(os.path.dirname(folder_path), file_name)


def cut_video(video_path, srt_path, if_print=True, max_delta_second=1, max_all_second=None):
    video_path = os.path.abspath(video_path)
    video_name = os.path.basename(video_path)
    output_dir = os.path.join(os.path.dirname(video_path), os.path.splitext(video_name)[0]+'_concat')
    if not os.path.exists(output_dir):
        os.mkdir(output_dir)
    if srt_path is None:
        srt_path = os.path.splitext(video_path)[0] + '.srt'
    srt_datas = read_srt(srt_path, max_delta_second, max_all_second)
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


def cli_run(args):
    video_path = args.video_path
    srt_path = args.srt_path
    max_delta_second = args.max_delta_second
    max_all_second = args.max_all_second
    output_dir = cut_video(video_path, srt_path, max_delta_second=max_delta_second, max_all_second=max_all_second)
    concat_video(output_dir)


def invoke_run(video_path, srt_path=None, delete_assembly_folder=True, lock_=threading.Lock()):
    output_dir = cut_video(video_path, srt_path, if_print=False)
    queue = Queue()
    with lock_:
        t = threading.Thread(target=concat_video, args=[output_dir], kwargs={'simple_postfix': True, 'if_print': False, 'queue_': queue})
        t.start()
        t.join()
        result_file_path = queue.get(block=False)
    if delete_assembly_folder:
        shutil.rmtree(output_dir)
    print(f"视频合并完毕，开始上传...")
    return result_file_path


if __name__ == '__main__':
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('video_path', help='视频文件的路径')
    parser.add_argument('-s', '--srt_path', help='字幕文件的路径，如果不提供，则为视频文件路径后缀名改为srt')
    parser.add_argument('--max_delta_second', help='如果指定，则字幕中如存在特定字符，将限制单句时长为此秒', type=int)
    parser.add_argument('--max_all_second', help='如果指定，将限制字幕所有单句时长为此秒，此选项优先级大于max_delta_second', type=int)
    args = parser.parse_args()
    cli_run(args)
