from selenium import webdriver
from selenium.webdriver.edge.service import Service
from load_xpath import *
import os


class FeishuApp:
    def __init__(self) -> None:
        self.load_user_password()
        self.edge_browser = webdriver.Edge(service=Service("driver/msedgedriver.exe"))
    
    def load_user_password(self):
        pw_file = 'pw.txt'
        if not os.path.exists(pw_file):
            user = input("请输入登陆用户名：")
            password = input("请输入登陆密码：")
            with open(pw_file,'w',encoding='utf-8') as f:
                f.write(f"{user}\n{password}")
        else:
            with open(pw_file,'r',encoding='utf-8') as f:
                (user,password) = f.read().strip().split('\n')
        self.user = user
        self.password = password



    def login(self):
        self.edge_browser.get('https://rbqqmtbi35.feishu.cn/minutes/me')
        self.edge_browser.maximize_window()
        switch_icon = self.edge_browser.find_element_by_xpath(xpath_switch_icon)
        switch_icon.click()

    def run(self):
        self.login()


if __name__ == '__main__':
    app = FeishuApp()
    app.run()
