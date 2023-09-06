import argparse
import os
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import List, NamedTuple

from tqdm import tqdm

from utils.re_util import eng_only_sentence_len, if_eng_only_sentence
from utils.sub_util import CHAR_SPEAK_DURATION_RATIO, read_srt


class Command(NamedTuple):
    command: str
    log_path: str


def concat_video(folder_path, simple_postfix=False, if_print=True, move_to_upper_folder=False):
    if if_print:
        print(f"工作目录：{folder_path}")
    filelist_path = os.path.join(folder_path, "filelist.txt")
    if os.path.exists(filelist_path):
        os.remove(filelist_path)
    with open(filelist_path, "a", encoding="utf-8") as f:
        for i in os.listdir(folder_path):
            i = os.path.join(folder_path, i)
            if os.path.splitext(i)[-1].lower() in [".txt", ".log"] or os.path.isdir(i):
                continue
            i = i.replace("'", r"'\''")
            f.write(f"file '{i}'\n")
    file_path = os.path.join(folder_path, f"{os.path.basename(folder_path)}_cut_dense.mp4")
    if simple_postfix:
        file_path = file_path.replace("_concat_cut_dense", "_ccd")
    log_path = os.path.abspath(os.path.join(folder_path, "concat_video.log"))
    command = f'ffmpeg -f concat -safe 0 -i "{filelist_path}" -c copy -y "{file_path}" 2>>"{log_path}"'
    if if_print:
        print(f"指令：{command}\n")
    subprocess.call(command, shell=True)
    if move_to_upper_folder:
        file_path = shutil.move(file_path, os.path.dirname(folder_path))
    return file_path


def cut_video(
    video_path,
    srt_path,
    if_print=True,
    max_onomatopoeic_second=1.0,
    max_all_second=None,
    truncate_long_eng_sentence=False,
    parallel=False,
):
    video_path = os.path.abspath(video_path)
    video_name = os.path.basename(video_path)
    output_dir = os.path.join(os.path.dirname(video_path), os.path.splitext(video_name)[0] + "_concat")
    if not os.path.exists(output_dir):
        os.mkdir(output_dir)
    if srt_path is None:
        srt_path_obj = os.path.splitext(video_path)[0] + ".srt"
        if os.path.exists(srt_path_obj):
            srt_path = srt_path_obj
        else:
            srt_path = video_path + ".srt"
    srt_datas = read_srt(srt_path, max_onomatopoeic_second, max_all_second, truncate_long_eng_sentence)

    commands: List[Command] = []
    for idx, srt_data in enumerate(srt_datas):
        start_time, end_time, content = srt_data

        def strptime(x):
            return datetime.strptime(x, r"%H:%M:%S.%f")

        delta = strptime(end_time) - strptime(start_time)
        seconds = delta.seconds + delta.microseconds / 1000 / 1000
        if (
            (not (if_eng_only_sentence(content) and eng_only_sentence_len(content) * CHAR_SPEAK_DURATION_RATIO <= seconds))
            and ((max_onomatopoeic_second is not None) and (seconds > max_onomatopoeic_second))
            or ((max_all_second is not None) and (seconds > max_all_second))
        ):
            with open(os.path.join(output_dir, "srt_info_badcase.log"), "a", encoding="utf-8") as f:
                f.write(f"{start_time}\n{end_time}\n{seconds}\n{content}\n\n")
        else:
            with open(os.path.join(output_dir, "srt_info.log"), "a", encoding="utf-8") as f:
                f.write(f"{start_time}\n{end_time}\n{seconds}\n{content}\n\n")

        output_video_path = os.path.join(
            output_dir,
            "".join(
                [
                    os.path.splitext(video_name)[0],
                    f"_{str(idx).zfill(6)}",
                    os.path.splitext(video_name)[1],
                ]
            ),
        )
        log_path = os.path.abspath(os.path.join(output_dir, "cut_video.log"))
        command = f'ffmpeg -y -ss {start_time} -to {end_time} -i "{video_path}" -preset veryfast -map_chapters -1 "{output_video_path}"'
        if parallel:
            log_path = f"_{idx}".join(os.path.splitext(log_path))
        command += f' 2>>"{log_path}"'
        commands.append(Command(command, log_path))
    if parallel:
        with ThreadPoolExecutor(max_workers=os.cpu_count()) as executor:
            with tqdm(total=len(commands), desc="Processing") as pbar:
                for _ in executor.map(_parallel_process, commands):
                    pbar.update(1)

        cut_video_logs_folder = os.path.join(output_dir, "cut_video_logs")
        os.mkdir(cut_video_logs_folder)
        for c in commands:
            shutil.move(c.log_path, cut_video_logs_folder)
    else:
        for command in tqdm(commands):
            if if_print:
                print(f"\n{command.command}")
            subprocess.call(command.command, shell=True)
    return output_dir


def _parallel_process(command: Command):
    with open(command.log_path, "w", encoding="utf-8") as f:
        f.write(f"{command.command}\n\n\n")
    subprocess.call(command.command, shell=True)


def cli_run(args):
    video_path = args.video_path
    srt_path = args.srt_path
    max_onomatopoeic_second = args.max_onomatopoeic_second
    max_all_second = args.max_all_second
    delete_assembly_folder = args.delete_assembly_folder
    parallel = args.parallel
    output_dir = cut_video(
        video_path, srt_path, max_onomatopoeic_second=max_onomatopoeic_second, max_all_second=max_all_second, parallel=parallel
    )
    concat_video(output_dir, move_to_upper_folder=True)
    if delete_assembly_folder:
        shutil.rmtree(output_dir)


def invoke_run(video_path, srt_path=None, delete_assembly_folder=True):
    output_dir = cut_video(video_path, srt_path, if_print=False)
    result_file_path = concat_video(output_dir, simple_postfix=True, if_print=False, move_to_upper_folder=True)
    if delete_assembly_folder:
        shutil.rmtree(output_dir)
    print(f"视频合并完毕，开始上传...")
    return result_file_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("video_path", help="视频文件的路径")
    parser.add_argument("-s", "--srt_path", help="字幕文件的路径，如果不提供，则为视频文件路径后缀名改为srt")
    parser.add_argument("-o", "--max_onomatopoeic_second", help="如果指定，则字幕中如存在特定字符，将限制单句时长为此秒", type=float)
    parser.add_argument("-a", "--max_all_second", help="如果指定，将限制字幕所有单句时长为此秒，此选项优先级大于max_onomatopoeic_second", type=float)
    parser.add_argument("-d", "--delete_assembly_folder", help="是否需要删除合并之前的碎片视频文件夹", action="store_true")
    parser.add_argument("-p", "--parallel", help="是否以多线程的方式转换视频", action="store_true")
    args = parser.parse_args()
    cli_run(args)
