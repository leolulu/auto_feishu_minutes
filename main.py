import collections
import os
import shutil
import time
from typing import List

from cut_dense_video import invoke_run
from feishu_app import FeishuApp


class FileWatcher:
    def __init__(self, file_path) -> None:
        print(f"新增文件进入监视中：{file_path}")
        self.file_path = file_path
        self.size_info = collections.deque(maxlen=3)
        self.await_delay_process = False
        self.app = FeishuApp(self.file_path)

    def get_latest_size(self):
        self.size_info.append(os.path.getsize(self.file_path))

    def check_size_stable(self):
        print(f"\n检查文件状态稳定性：{os.path.basename(self.file_path)}")
        try:
            os.rename(self.file_path, self.file_path)
        except:
            print("文件复制粘贴未完成...")
            return False
        self.get_latest_size()
        print(f"文件大小状态：{list(self.size_info)}")
        if (len(self.size_info) == 3) and (len(set(self.size_info)) == 1):
            return True
        else:
            return False

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
    SUPPORTED_FORMAT = ['.mp4', '.avi']

    def __init__(
        self,
        data_dir,
        level_target=4,
        switch_after_noumenon_uploaded=False
    ) -> None:
        self.files: List[FileWatcher] = []
        self.data_dir = data_dir
        self.level_target = level_target
        self.switch_after_noumenon_uploaded = switch_after_noumenon_uploaded

    def append_file_list(self, file_path):
        if not file_path in [i.file_path for i in self.files]:
            self.files.append(FileWatcher(file_path))

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

    def _level_upload(self, video_file, level, level_target):
        print(f"启动【{level}】次上传...")
        dense_cutted_video_path = invoke_run(video_file, delete_assembly_folder=False)
        app = FeishuApp(
            dense_cutted_video_path,
            if_need_sub=False if level == level_target else True
        )
        app.run()
        if level < level_target:
            self._level_upload(dense_cutted_video_path, level+1, level_target)

    def multi_post_upload(self, finish_file_path, level_target):
        print("启用后处理上传...")
        level = 2
        self._level_upload(finish_file_path, level, level_target)

    def check_and_process_files(self):
        for file in self.files[::-1]:
            if file.check_size_stable():
                file.institute_feishu_process(self.switch_after_noumenon_uploaded)
                if self.switch_after_noumenon_uploaded and file.await_delay_process:
                    continue
                finish_file_path = self.add_finish_mark(file.file_path)
                self.add_finish_mark(file.srt_path)
                self.multi_post_upload(finish_file_path, self.level_target)
                self.files.remove(file)
                print("处理完成，继续监控...")

    def run(self):
        print(f"开始监控文件夹：{self.data_dir}")
        while True:
            self.scan_data_dir()
            self.check_and_process_files()
            time.sleep(10)


if __name__ == '__main__':
    scanner = FileScanner(
        os.path.abspath('data'),
        level_target=4,
        switch_after_noumenon_uploaded=True
    )
    scanner.run()
