import logging
import os
import shutil
import sys
import time
import types

from lxml import etree
from selenium import webdriver
from selenium.common.exceptions import TimeoutException, ElementNotInteractableException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.edge.options import Options
from selenium.webdriver.edge.service import Service
from selenium.webdriver.remote.remote_connection import LOGGER as seleniumLogger
from urllib3.connectionpool import log as urllibLogger

from utils.download_util import get_download_path
from utils.load_xpath import *
from utils.upload_util import Uploader, upload_file_pyauto
from utils.webdriver_util import wait_element_clickable, wait_element_presence, wait_element_visible


class FeishuApp:
    LOCAL_ASSETS = "local_assets"
    DATA_DIR = "data"

    def __init__(self, file_path, if_need_sub=True, delete_org_video=False) -> None:
        self.set_log_level()
        self.if_need_sub = if_need_sub
        self.delete_org_video = delete_org_video
        self.file_dir = os.path.dirname(file_path)
        self.file_name = os.path.basename(file_path)
        self.load_user_password()
        edge_options = Options()
        edge_options.add_argument("user-data-dir={}".format(
            os.path.join(
                os.path.abspath(os.getcwd()),
                FeishuApp.LOCAL_ASSETS,
                "user-data-dir"
            )
        ))
        self.edge_browser = webdriver.Edge(
            service=Service("driver/msedgedriver.exe"),
            options=edge_options
        )
        self._enrich_browser()
        self.edge_browser.get('https://rbqqmtbi35.feishu.cn/minutes/me')
        self.edge_browser.maximize_window()

    def set_log_level(self):
        seleniumLogger.setLevel(logging.WARNING)
        urllibLogger.setLevel(logging.WARNING)

    def _enrich_browser(self):
        browser = self.edge_browser
        browser.wait_element_presence = types.MethodType(wait_element_presence, browser)
        browser.wait_element_visible = types.MethodType(wait_element_visible, browser)
        browser.wait_element_clickable = types.MethodType(wait_element_clickable, browser)

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
        self.edge_browser.wait_element_clickable(xpath_switch_icon).click()
        self.edge_browser.wait_element_clickable(xpath_input_mobile_phone).send_keys(self.user)
        self.edge_browser.find_element('xpath', xpath_service_policy).click()
        self.edge_browser.wait_element_clickable(xpath_confirm_phone).click()
        self.edge_browser.wait_element_clickable(xpath_switch_pw_login).click()
        self.edge_browser.wait_element_clickable(xpath_pw_input).send_keys(self.password)
        self.edge_browser.wait_element_clickable(xpath_confirm_pw).click()
        time.sleep(30)

    def open_main_page(self):
        try:
            self.edge_browser.wait_element_visible(xpath_page_title, 10)
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
                actions.click(
                    self.edge_browser.find_element('xpath', xpath_upload_menu_container)
                )
                actions.perform()
                if_open_upload_menu_success = True
            except ElementNotInteractableException:
                time.sleep(2)
        self.edge_browser.wait_element_clickable(xpath_upload_modal_body).click()
        uploader = Uploader("打开")
        uploader.wait_present()
        upload_file_pyauto(self.file_dir, self.file_name, uploader.win)
        self.edge_browser.wait_element_clickable(xpath_upload_submit).click()

    def check_upload_status(self):
        if_find_it = False
        if_finish = False
        num = 0
        while not if_finish:
            html = etree.HTML(self.edge_browser.page_source)
            video_sections = html.xpath(xpath_videos)[:5]
            for video_section in video_sections:
                video_title = video_section.xpath(xpath_video_title)
                detail_page_url = video_section.xpath(xpath_video_url)
                video_duration = video_section.xpath(xpath_video_duration)
                video_transcoding = video_section.xpath(xpath_video_video_transcoding)
                if video_title[0] == os.path.splitext(self.file_name)[0]:
                    if self.if_need_sub:
                        if not if_find_it:
                            print("定位到新视频，当前状态：")
                        if_find_it = True
                        print(video_title, video_duration, video_transcoding)
                    if (not self.if_need_sub) or (not video_transcoding):
                        if_finish = True
                        self.edge_browser.get(detail_page_url[0])
                        break
                else:
                    if num % 10 == 0:
                        if not if_find_it:
                            upload_status_obj = html.xpath(xpath_upload_status)
                            if len(upload_status_obj) > 0:
                                upload_status = upload_status_obj[0]
                            else:
                                upload_status = ""
                            print(f"上传中，进度：{upload_status}...")

                        num = 0
                    num += 1
                    time.sleep(2)

    def download_sub(self):
        hover = ActionChains(self.edge_browser).move_to_element(
            self.edge_browser.find_element('xpath', xpath_detail_option)
        )
        hover.perform()
        time.sleep(2)
        self.edge_browser.wait_element_clickable(xpath_export_miaoji).click()
        self.edge_browser.wait_element_clickable(xpath_format_selector).click()
        self.edge_browser.wait_element_clickable(xpath_srt_option).click()
        self.edge_browser.wait_element_clickable(xpath_button_export).click()

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

    def delete_video(self):
        hover = ActionChains(self.edge_browser).move_to_element(
            self.edge_browser.find_element('xpath', xpath_detail_option)
        )
        hover.perform()
        time.sleep(2)
        self.edge_browser.wait_element_clickable(xpath_delete_miaoji).click()
        self.edge_browser.wait_element_clickable(xpath_button_delete).click()
        time.sleep(2)

    def run(self):
        self.open_main_page()
        self.upload_file()
        self.check_upload_status()
        if self.if_need_sub:
            self.download_sub()
            self.move_srt_file()
            if self.delete_org_video:
                self.delete_video()
        self.edge_browser.quit()


if __name__ == '__main__':
    file_path = sys.argv[1]
    app = FeishuApp(file_path)
    app.run()
