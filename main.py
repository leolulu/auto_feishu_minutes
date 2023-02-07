import argparse
import collections
import os
import re
import shutil
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import List

from cut_dense_video import invoke_run
from feishu_app import FeishuApp
from utils.chrome_controller import UserDirDispatcher
from utils.common_util import mux_video
from utils.locks import global_lock
from utils.sub_util import if_srt_empty


class PostUploader:
    def __init__(
        self,
        video_path: str,
        level_target,
        user_dir_dispatcher: UserDirDispatcher
    ) -> None:
        self.video_path = video_path
        self.level_target = level_target
        self.current_level = 2
        self.all_finish = False
        self.app: FeishuApp = None  # type: ignore
        self.user_dir_dispatcher = user_dir_dispatcher

    def upload_laucher(self, switch_between_post_uploads):
        self.level_upload(switch_between_post_uploads)
        if self.all_finish:
            return
        if self.app.sub_downloaded or (self.current_level == self.level_target):
            self.current_level += 1
            self.app = None  # type: ignore
            if self.current_level > self.level_target:
                self.all_finish = True

    def level_upload(self, switch_between_post_uploads):
        print(f"启动【{self.current_level}】次上传...")
        if self.app is None:
            print("本次上传是视频环节...")
            srt_path = os.path.splitext(self.video_path)[0] + '.srt'
            if if_srt_empty(srt_path):
                print("字幕内容为空，后处理到此为止...")
                self.all_finish = True
                return
            self.video_path = invoke_run(self.video_path, srt_path, delete_assembly_folder=False, lock_=global_lock)
            self.app = FeishuApp(
                self.video_path,
                self.user_dir_dispatcher,
                if_need_sub=False if self.current_level == self.level_target else True
            )
        else:
            print("本次上传是字幕环节...")
        if switch_between_post_uploads:
            self.app.run(delay_process=not self.app.video_uploaded)
        else:
            self.app.run()


class FileWatcher:
    ILLEGAL_CHAR = ['~']

    def __init__(self, file_path, user_dir_dispatcher: UserDirDispatcher) -> None:
        print(f"新增文件进入监视中：{file_path}")
        self.queue_size = 3
        self.file_path = file_path
        self.user_dir_dispatcher = user_dir_dispatcher
        self.size_info = collections.deque(maxlen=self.queue_size)
        self.await_delay_process = False
        self.post_uploader: PostUploader = None  # type: ignore
        self._get_file_level_target()
        self.illegal_char_checked = False

    def _illegal_char_check(self):
        file = os.path.basename(self.file_path)
        file_dir = os.path.dirname(self.file_path)
        if_replaced = False
        for char_ in FileWatcher.ILLEGAL_CHAR:
            if char_ in file:
                file_replaced = file.replace(char_, "")
                print(f"文件名中存在非法字符【{char_}】，进行替换：[{file}] → [{file_replaced}]")
                file = file_replaced
                if_replaced = True
        if if_replaced:
            file_path_replaced = os.path.join(file_dir, file)
            os.rename(self.file_path, file_path_replaced)
            self.file_path = file_path_replaced
        self.illegal_char_checked = True

    def _get_file_level_target(self):
        file_name = os.path.splitext(os.path.basename(self.file_path))[0]
        level_obj = re.findall(r"__l(\d)$", file_name)
        if level_obj:
            self.file_level_target = int(level_obj[0])
        else:
            self.file_level_target = None

    def get_file_level_target(self, default: int) -> int:
        if isinstance(self.file_level_target, int):
            return self.file_level_target
        else:
            return default

    @property
    def _if_level0(self):
        if isinstance(self.file_level_target, int) and self.file_level_target <= 1:
            return True
        else:
            return False

    def _get_latest_size(self):
        self.size_info.append(os.path.getsize(self.file_path))

    def check_size_stable(self, get_info=True):
        if get_info:
            self._get_size_info()
        if (
            (len(self.size_info) == self.queue_size)
            and (len(set(self.size_info)) == 1)
            and (set(self.size_info).pop() != -1)
            and (set(self.size_info).pop() != 0)
        ):
            return True
        else:
            return False

    def _get_size_info(self):
        print(f"\n检查文件状态稳定性：{os.path.basename(self.file_path)}")
        try:
            os.rename(self.file_path, self.file_path)
        except PermissionError:
            print("文件复制粘贴未完成...")
            self.size_info.append(-1)
            return
        except Exception as e:
            raise e
        self._get_latest_size()
        print(f"文件大小状态：{list(self.size_info)}")

    def institute_feishu_process(self, switch_after_noumenon_uploaded):
        if not os.path.exists(self.file_path):
            raise UserWarning(f"{self.file_path}不存在，终止任务！！！")
        if not self.illegal_char_checked:
            self._illegal_char_check()
        self.app = FeishuApp(self.file_path, self.user_dir_dispatcher)
        if switch_after_noumenon_uploaded and (not self.await_delay_process):
            print(f"大小稳定了，启动新飞书任务：{self.file_path}")
            self.app.run(delay_process=True, level0_process=self._if_level0)
            self.await_delay_process = True
        else:
            if switch_after_noumenon_uploaded:
                print(f"获取首次上传的字幕：{self.file_path}")
            else:
                print(f"大小稳定了，启动新飞书任务：{self.file_path}")
            self.app.run(level0_process=self._if_level0)
            self.await_delay_process = False
            self.srt_path = self.app.srt_path
            print("飞书任务处理完毕...")


class FileScanner:
    POSTFIX = "_srted"
    NOT_PROCESS_POSTFIX = [POSTFIX, "_cut_dense", "_ccd", "_remuxed"]
    SUPPORTED_FORMAT = ['.mp4', '.avi', '.wmv', '.mov', '.m4v', '.mpeg', 'ogg', '.3gp', '.flv']
    REMUX_FORMAT = ['.mkv', '.webm']

    def __init__(
        self,
        data_dir,
        level_target=4,
        switch_after_noumenon_uploaded=False,
        switch_between_post_uploads=False,
        use_concurrency=False
    ) -> None:
        self.files: List[FileWatcher] = []
        self.submitted_files: List[FileWatcher] = []
        self.data_dir = data_dir
        self.level_target = level_target
        self.switch_after_noumenon_uploaded = switch_after_noumenon_uploaded
        self.switch_between_post_uploads = switch_between_post_uploads
        self.use_concurrency = use_concurrency
        self.user_dir_dispatcher = UserDirDispatcher(1)
        if self.use_concurrency:
            self.exe_num = 3
            self.user_dir_dispatcher = UserDirDispatcher(self.exe_num)
            self.executor = ThreadPoolExecutor(self.exe_num)
            self.switch_after_noumenon_uploaded = False
            self.switch_between_post_uploads = False

    def append_file_list(self, file_path):
        if not file_path in [i.file_path for i in (self.files+self.submitted_files)]:
            self.files.append(FileWatcher(file_path, self.user_dir_dispatcher))

    def _renamed_name(self, file_path):
        return FileScanner.POSTFIX.join(os.path.splitext(file_path))

    def add_finish_mark(self, file_path):
        if os.path.exists(file_path):
            return shutil.move(file_path, self._renamed_name(file_path))

    def _postfix_check(self, name: str):
        pass_ = True
        for postfix in FileScanner.NOT_PROCESS_POSTFIX:
            if name.lower().endswith(postfix):
                pass_ = False
                break
        return pass_

    def scan_data_dir(self):
        while True:
            try:
                files = os.listdir(os.path.abspath(self.data_dir))
                break
            except Exception as e:
                print(f"[{datetime.now().strftime('%F %X')}] {e}")
                time.sleep(5)

        for file in files:
            (name, ext) = os.path.splitext(file)
            file_path = os.path.join(self.data_dir, file)
            if self._postfix_check(name):
                if ext.lower() in FileScanner.SUPPORTED_FORMAT:
                    self.append_file_list(file_path)
                if ext.lower() in FileScanner.REMUX_FORMAT:
                    try:
                        os.rename(file_path, file_path)
                    except PermissionError:
                        continue
                    print(f"重封装文件：{file_path}")
                    mux_video(file_path)

    def multi_post_upload(self, finish_file_path, level_target, file: FileWatcher):
        if level_target <= 1:
            print(f"此文件level_target为【{level_target}】，无需进入后处理环节")
            return True
        print("进入后处理上传环节...")
        if file.post_uploader is None:
            file.post_uploader = PostUploader(finish_file_path, level_target, self.user_dir_dispatcher)
        if self.switch_between_post_uploads:
            file.post_uploader.upload_laucher(self.switch_between_post_uploads)
        else:
            while not file.post_uploader.all_finish:
                file.post_uploader.upload_laucher(self.switch_between_post_uploads)
        return file.post_uploader.all_finish

    def check_and_process_files_concurrent(self):
        def process(file: FileWatcher):
            try:
                file.institute_feishu_process(self.switch_after_noumenon_uploaded)
                finish_file_path = self.add_finish_mark(file.file_path)
                self.add_finish_mark(file.srt_path)
                self.multi_post_upload(finish_file_path, file.get_file_level_target(self.level_target), file)
                self.submitted_files.remove(file)
                print("异步任务已完成...")
            except Exception as e:
                print("异步任务出问题了！！！！！需要检查！")
                print(e)
                traceback.print_exc()
                with open('error.log', 'a', encoding='utf-8') as f:
                    f.write("{}\n{}\n{}\n\n\n".format(file.file_path, str(e), traceback.format_exc()))

        for file in self.files[::-1]:
            if self._check_size_stable_wrapper(file):
                self.executor.submit(process, file)
                self.submitted_files.append(file)
                self.files.remove(file)
                print("异步任务已提交，继续监控...")
                time.sleep(60)

    def check_and_process_files(self):
        for file in self.files[::-1]:
            if self._check_size_stable_wrapper(file):
                if file.post_uploader is None:
                    file.institute_feishu_process(self.switch_after_noumenon_uploaded)
                    if self.switch_after_noumenon_uploaded and file.await_delay_process:
                        continue
                    finish_file_path = self.add_finish_mark(file.file_path)
                    self.add_finish_mark(file.srt_path)
                post_upload_finish = self.multi_post_upload(finish_file_path, file.get_file_level_target(self.level_target), file)  # type: ignore
                if self.switch_between_post_uploads and (not post_upload_finish):
                    continue
                self.files.remove(file)
                print("处理完成，继续监控...")

    def _check_size_stable_wrapper(self, file: FileWatcher):
        try:
            return file.check_size_stable()
        except FileNotFoundError:
            print(f"文件[{file.file_path}]不存在，移出监控列表...")
            self.files.remove(file)

    def _check_need_to_wait(self):
        if_files_empty = len(self.files) == 0
        sizes = set([i.check_size_stable(False) for i in self.files])
        if_all_size_stable = ((len(sizes) == 1) and sizes.pop())
        return if_files_empty or (not if_all_size_stable)

    def run(self):
        print(f"开始监控文件夹：{self.data_dir}")
        while True:
            self.scan_data_dir()
            if self.use_concurrency:
                self.check_and_process_files_concurrent()
            else:
                self.check_and_process_files()
            if self._check_need_to_wait():
                time.sleep(10)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--data_dir', help='监控目录的路径，可以使用相对路径，默认为当前目录的data文件夹', default='data')
    parser.add_argument('-l', '--level_target', help='需要进行的N次处理层数，默认为2', default=2, type=int)
    parser.add_argument('--switch_after_noumenon_uploaded', help='单线程处理模式专用，是否在原始文件上传后立刻切换上传下一个原始文件，默认关闭', action='store_true')
    parser.add_argument('--switch_between_post_uploads', help='单线程处理模式专用，是否在上传后处理文件时进行轮番上传，默认关闭', action='store_true')
    parser.add_argument('--not_use_concurrency', help='是否禁用多线程处理模式，默认开启多线程处理模式。多线程处理模式开启时，单线程处理模式的上两个选项会被关闭', action='store_false')
    args = parser.parse_args()
    scanner = FileScanner(
        os.path.abspath(args.data_dir),
        level_target=args.level_target,
        switch_after_noumenon_uploaded=args.switch_after_noumenon_uploaded,
        switch_between_post_uploads=args.switch_between_post_uploads,
        use_concurrency=args.not_use_concurrency
    )
    scanner.run()
