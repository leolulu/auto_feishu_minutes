import collections
import os
import shutil
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from typing import List

from cut_dense_video import invoke_run
from feishu_app import FeishuApp
from utils.chrome_controller import UserDirDispatcher
from utils.read_srt import if_srt_empty


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
            self.video_path = invoke_run(self.video_path, srt_path, delete_assembly_folder=False)
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
    def __init__(self, file_path, user_dir_dispatcher: UserDirDispatcher) -> None:
        print(f"新增文件进入监视中：{file_path}")
        self.queue_size = 3
        self.file_path = file_path
        self.size_info = collections.deque(maxlen=self.queue_size)
        self.await_delay_process = False
        self.app = FeishuApp(self.file_path, user_dir_dispatcher)
        self.post_uploader: PostUploader = None  # type: ignore

    def _get_latest_size(self):
        self.size_info.append(os.path.getsize(self.file_path))

    def check_size_stable(self, get_info=True):
        if get_info:
            self._get_size_info()
        if (
            (len(self.size_info) == self.queue_size)
            and (len(set(self.size_info)) == 1)
            and (set(self.size_info).pop() != -1)
        ):
            return True
        else:
            return False

    def _get_size_info(self):
        print(f"\n检查文件状态稳定性：{os.path.basename(self.file_path)}")
        try:
            os.rename(self.file_path, self.file_path)
        except:
            print("文件复制粘贴未完成...")
            self.size_info.append(-1)
            return
        self._get_latest_size()
        print(f"文件大小状态：{list(self.size_info)}")

    def institute_feishu_process(self, switch_after_noumenon_uploaded):
        if switch_after_noumenon_uploaded and (not self.await_delay_process):
            print(f"大小稳定了，启动新飞书任务：{self.file_path}")
            self.app.run(delay_process=True)
            self.await_delay_process = True
        else:
            if switch_after_noumenon_uploaded:
                print(f"获取首次上传的字幕：{self.file_path}")
            else:
                print(f"大小稳定了，启动新飞书任务：{self.file_path}")
            self.app.run()
            self.await_delay_process = False
            self.srt_path = self.app.srt_path
            print("飞书任务处理完毕...")


class FileScanner:
    POSTFIX = "_srted"
    NOT_PROCESS_POSTFIX = [POSTFIX, "_cut_dense", "_ccd"]
    SUPPORTED_FORMAT = ['.mp4', '.avi', '.wmv', '.mov', '.m4v', '.mpeg', 'ogg', '.3gp', '.flv']

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
        return shutil.move(file_path, self._renamed_name(file_path))

    def _postfix_check(self, name: str):
        pass_ = True
        for postfix in FileScanner.NOT_PROCESS_POSTFIX:
            if name.lower().endswith(postfix):
                pass_ = False
                break
        return pass_

    def scan_data_dir(self):
        for file in os.listdir(os.path.abspath(self.data_dir)):
            (name, ext) = os.path.splitext(file)
            file_path = os.path.join(self.data_dir, file)
            if ext.lower() in FileScanner.SUPPORTED_FORMAT and (self._postfix_check(name)):
                self.append_file_list(file_path)

    def multi_post_upload(self, finish_file_path, level_target, file: FileWatcher):
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
                self.multi_post_upload(finish_file_path, self.level_target, file)  # type: ignore
                self.submitted_files.remove(file)
                print("异步任务已完成...")
            except Exception as e:
                print("异步任务出问题了！！！！！需要检查！")
                print(e)
                with open('error.log', 'a', encoding='utf-8') as f:
                    f.write("{}\n{}\n{}\n\n\n".format(file.file_path, str(e), traceback.format_exc()))

        for file in self.files[::-1]:
            if file.check_size_stable():
                self.executor.submit(process, file)
                self.submitted_files.append(file)
                self.files.remove(file)
                print("异步任务已提交，继续监控...")
                time.sleep(70)

    def check_and_process_files(self):
        for file in self.files[::-1]:
            if file.check_size_stable():
                if file.post_uploader is None:
                    file.institute_feishu_process(self.switch_after_noumenon_uploaded)
                    if self.switch_after_noumenon_uploaded and file.await_delay_process:
                        continue
                    finish_file_path = self.add_finish_mark(file.file_path)
                    self.add_finish_mark(file.srt_path)
                post_upload_finish = self.multi_post_upload(finish_file_path, self.level_target, file)  # type: ignore
                if self.switch_between_post_uploads and (not post_upload_finish):
                    continue
                self.files.remove(file)
                print("处理完成，继续监控...")

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
    scanner = FileScanner(
        os.path.abspath('data'),
        level_target=3,
        switch_after_noumenon_uploaded=False,
        switch_between_post_uploads=False,
        use_concurrency=True
    )
    scanner.run()
