import collections
import os
import shutil
import time

from feishu_app import FeishuApp


class FileWatcher:
    def __init__(self, file_path) -> None:
        print(f"新增文件进入监视中：{file_path}")
        self.file_path = file_path
        self.size_info = collections.deque(maxlen=3)

    def get_latest_size(self):
        self.size_info.append(os.path.getsize(self.file_path))

    def check_size_stable(self):
        self.get_latest_size()
        print(f"检查文件大小是否稳定：{list(self.size_info)}")
        if (len(self.size_info) == 3) and (len(set(self.size_info)) == 1):
            return True
        else:
            return False

    def institute_feishu_process(self):
        print(f"大小稳定了，启动新飞书任务：{self.file_path}")
        app = FeishuApp(self.file_path)
        app.run()
        self.srt_path = app.srt_path
        print("飞书任务处理完毕...")


class FileScanner:
    POSTFIX = "_srted"
    SUPPORTED_FORMAT = ['.mp4', '.avi']

    def __init__(self, data_dir) -> None:
        self.files = []
        self.data_dir = data_dir

    def append_file_list(self, file_path):
        if not file_path in [i.file_path for i in self.files]:
            self.files.append(FileWatcher(file_path))

    def _renamed_name(self, file_path):
        return FileScanner.POSTFIX.join(os.path.splitext(file_path))

    def add_finish_mark(self, file_path):
        return shutil.move(file_path, self._renamed_name(file_path))

    def scan_data_dir(self):
        for file in os.listdir(os.path.abspath(self.data_dir)):
            file = file.lower()
            (name, ext) = os.path.splitext(file)
            file_path = os.path.join(self.data_dir, file)
            if ext in FileScanner.SUPPORTED_FORMAT and (not name.endswith(FileScanner.POSTFIX)):
                self.append_file_list(file_path)

    def second_upload(self, file_path):
        print("启用二次上传...")
        app = FeishuApp(file_path, if_need_sub=False)
        app.run()

    def check_and_process_files(self):
        for file in self.files[::-1]:
            if file.check_size_stable():
                file.institute_feishu_process()
                finish_file_path = self.add_finish_mark(file.file_path)
                self.add_finish_mark(file.srt_path)
                self.second_upload(finish_file_path)
                self.files.remove(file)
                print("处理完成，继续监控...")

    def run(self):
        print(f"开始监控文件夹：{self.data_dir}")
        while True:
            self.scan_data_dir()
            self.check_and_process_files()
            time.sleep(10)


if __name__ == '__main__':
    scanner = FileScanner(os.path.abspath('data'))
    scanner.run()
