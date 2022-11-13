import logging
import os
import shutil
import sys
import time
import types
from typing import List

from lxml import etree
from selenium import webdriver
from selenium.common.exceptions import ElementNotInteractableException, TimeoutException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.edge.options import Options
from selenium.webdriver.edge.service import Service
from selenium.webdriver.remote.remote_connection import LOGGER as seleniumLogger
from urllib3.connectionpool import log as urllibLogger

from utils.chrome_controller import UserDirDispatcher
from utils.download_util import get_download_path
from utils.load_xpath import *
from utils.upload_util import Uploader, upload_file_pyauto
from utils.webdriver_util import wait_element_clickable, wait_element_presence, wait_element_visible


class VideoInfo:
    def __init__(self) -> None:
        self.finish_upload = False
        self.finish_transcode = False
        self.video_title = []
        self.detail_page_url = []
        self.video_duration = []
        self.video_transcoding = []
        self.upload_status: List[str] = []

    def get_upload_status(self) -> str:
        if len(self.upload_status) > 0:
            return self.upload_status[0]
        else:
            return ""


class FeishuApp:
    LOCAL_ASSETS = "local_assets"
    DATA_DIR = "data"

    def __init__(
        self,
        file_path,
        user_dir_dispatcher: UserDirDispatcher,
        if_need_sub=True,
        if_delete_video=False
    ) -> None:
        self.set_log_level()
        self.user_dir_dispatcher = user_dir_dispatcher
        self.if_need_sub = if_need_sub
        self.if_delete_video = if_delete_video
        self.file_dir = os.path.dirname(file_path)
        self.file_name = os.path.basename(file_path)
        self.load_user_password()
        self._init_process_status()
        self.fail_times = 0

    def _init_process_status(self):
        self.video_uploaded = False
        self.sub_downloaded = False
        self.video_deleted = False

    def _open_browser(self):
        self.user_dir = self.user_dir_dispatcher.get_an_idle_dir()
        edge_options = Options()
        edge_options.add_argument("user-data-dir={}".format(
            os.path.join(
                os.path.abspath(os.getcwd()),
                FeishuApp.LOCAL_ASSETS,
                self.user_dir.dir
            )
        ))
        self.edge_browser = webdriver.Edge(
            service=Service("driver/msedgedriver.exe"),
            options=edge_options
        )
        self._enrich_browser()

    def set_log_level(self):
        seleniumLogger.setLevel(logging.WARNING)
        urllibLogger.setLevel(logging.WARNING)

    def _enrich_browser(self):
        browser = self.edge_browser
        browser.wait_element_presence = types.MethodType(wait_element_presence, browser)  # type: ignore
        browser.wait_element_visible = types.MethodType(wait_element_visible, browser)  # type: ignore
        browser.wait_element_clickable = types.MethodType(wait_element_clickable, browser)  # type: ignore

    def load_user_password(self):
        if not os.path.exists(FeishuApp.LOCAL_ASSETS):
            os.makedirs(FeishuApp.LOCAL_ASSETS)
        pw_file_path = os.path.join(FeishuApp.LOCAL_ASSETS, 'pw.txt')
        if not os.path.exists(pw_file_path):
            user = input("请输入登陆用户名：")
            password = input("请输入登陆密码：")
            with open(pw_file_path, 'w', encoding='utf-8') as f:
                f.write(f"{user}\n{password}")
        else:
            with open(pw_file_path, 'r', encoding='utf-8') as f:
                (user, password) = f.read().strip().split('\n')
        self.user = user
        self.password = password

    def login(self):
        self.edge_browser.wait_element_clickable(xpath_switch_icon).click()  # type: ignore
        self.edge_browser.wait_element_clickable(xpath_input_mobile_phone).send_keys(self.user)  # type: ignore
        self.edge_browser.find_element('xpath', xpath_service_policy).click()
        self.edge_browser.wait_element_clickable(xpath_confirm_phone).click()  # type: ignore
        self.edge_browser.wait_element_clickable(xpath_switch_pw_login).click()  # type: ignore
        self.edge_browser.wait_element_clickable(xpath_pw_input).send_keys(self.password)  # type: ignore
        self.edge_browser.wait_element_clickable(xpath_confirm_pw).click()  # type: ignore
        time.sleep(120)

    def open_main_page(self):
        self._open_browser()
        self.edge_browser.get('https://rbqqmtbi35.feishu.cn/minutes/me')
        self.edge_browser.maximize_window()
        try:
            self.edge_browser.wait_element_visible(xpath_page_title, 10)  # type: ignore
            print("进入主页成功...")
        except TimeoutException:
            print("打开主页失败，进入登陆流程，可能需要手动输入验证码...")
            self.login()

    def upload_file(self):
        if_open_upload_menu_success = False
        while not if_open_upload_menu_success:
            try:
                actions = ActionChains(self.edge_browser)
                actions.move_to_element(
                    self.edge_browser.find_element('xpath', xpath_upload_button)
                )
                time.sleep(1)
                actions.click(
                    self.edge_browser.find_element('xpath', xpath_upload_menu_container)
                )
                actions.perform()
                time.sleep(1)
                self.edge_browser.wait_element_clickable(xpath_upload_modal_body).click()  # type: ignore
                if_open_upload_menu_success = True
            except Exception as e:
                print(e)
                time.sleep(1)
        uploader = Uploader("打开")
        uploader.wait_present()
        upload_file_pyauto(self.file_dir, self.file_name, uploader.win)
        self.edge_browser.wait_element_clickable(xpath_upload_submit).click()  # type: ignore

    def _get_video_status(self, video_info: VideoInfo, need_scroll=False):
        if need_scroll:
            scrolling_element = self.edge_browser.find_element("xpath", xpath_video_list)
            self.edge_browser.execute_script('arguments[0].scrollTop = arguments[0].scrollHeight', scrolling_element)
            self.edge_browser.execute_script('arguments[0].scrollTop = 0', scrolling_element)
        html = etree.HTML(self.edge_browser.page_source)  # type: ignore
        video_info.upload_status = html.xpath(xpath_upload_status)
        video_sections = html.xpath(xpath_videos)
        for video_section in video_sections:
            video_title = video_section.xpath(xpath_video_title)
            detail_page_url = video_section.xpath(xpath_video_url)
            video_duration = video_section.xpath(xpath_video_duration)
            video_transcoding = video_section.xpath(xpath_video_video_transcoding)
            if video_title[0] == os.path.splitext(self.file_name)[0]:
                video_info.finish_upload = True
                video_info.video_title = video_title
                video_info.detail_page_url = detail_page_url
                video_info.video_duration = video_duration
                video_info.video_transcoding = video_transcoding

    def check_transcode_status(self):
        video_info = VideoInfo()
        while not video_info.finish_transcode:
            self._get_video_status(video_info, True)
            if (video_info.finish_upload) and (not video_info.video_transcoding):
                video_info.finish_transcode = True
                self.detail_page_url = video_info.detail_page_url[0]
            else:
                print(video_info.video_title, video_info.video_duration, video_info.video_transcoding)
                time.sleep(10)

    def check_upload_status(self):
        video_info = VideoInfo()
        while not video_info.finish_upload:
            self._get_video_status(video_info)
            if video_info.finish_upload == True:
                self.video_uploaded = True
                print("定位到新视频，上传完毕...")
            else:
                print(f"上传中，进度：{video_info.get_upload_status()}...")
                time.sleep(10)

    def download_sub(self):
        self.edge_browser.get(self.detail_page_url)
        hover = ActionChains(self.edge_browser).move_to_element(
            self.edge_browser.find_element('xpath', xpath_detail_option)
        )
        hover.perform()
        time.sleep(2)
        self.edge_browser.wait_element_clickable(xpath_export_miaoji).click()  # type: ignore
        self.edge_browser.wait_element_clickable(xpath_format_selector).click()  # type: ignore
        self.edge_browser.wait_element_clickable(xpath_srt_option).click()  # type: ignore
        self.edge_browser.wait_element_clickable(xpath_button_export).click()  # type: ignore

    def move_srt_file(self):
        if_find_it = False
        num = 0
        while not if_find_it:
            for scan_file in os.listdir(get_download_path()):
                scan_file = os.path.join(get_download_path(), scan_file)
                (name, ext) = os.path.splitext(os.path.basename(scan_file))
                if name == os.path.splitext(self.file_name)[0] and ext == '.srt':
                    if_find_it = True
                    self.srt_path = os.path.abspath(shutil.move(scan_file, self.file_dir))
                    break
                else:
                    if num % 20 == 0:
                        print("等待字幕下载完毕...")
                        num = 0
                    num += 1
                    time.sleep(0.5)
        self.sub_downloaded = True

    def delete_video(self):
        hover = ActionChains(self.edge_browser).move_to_element(
            self.edge_browser.find_element('xpath', xpath_detail_option)
        )
        hover.perform()
        time.sleep(2)
        self.edge_browser.wait_element_clickable(xpath_delete_miaoji).click()  # type: ignore
        self.edge_browser.wait_element_clickable(xpath_button_delete).click()  # type: ignore
        time.sleep(2)
        self.video_deleted = True

    def dispatch(self, delay_process):
        self.open_main_page()
        if not self.video_uploaded:
            self.upload_file()
            self.check_upload_status()
        if delay_process:
            self.edge_browser.quit()
            time.sleep(1)
            return
        if self.if_need_sub:
            if not self.sub_downloaded:
                self.check_transcode_status()
                self.download_sub()
                self.move_srt_file()
            if self.if_delete_video:
                if not self.video_deleted:
                    self.delete_video()
        self.edge_browser.quit()
        time.sleep(1)

    def run(self, delay_process=False):
        task_success = False
        while not task_success:
            try:
                self.dispatch(delay_process)
                task_success = True
            except Exception as e:
                self.edge_browser.quit()
                print(f"出错了，重新调度任务：{e}")
                time.sleep(self.fail_times * self.user_dir.id * 10)
                self.fail_times += 1
            finally:
                self.user_dir.free()


if __name__ == '__main__':
    file_path = sys.argv[1]
    app = FeishuApp(file_path, UserDirDispatcher(1))
    app.run()
