import re
import time

import pyautogui
import pyperclip
import win32gui

from pywintypes import error


class Uploader:
    def __init__(self, title) -> None:
        self.win = WindowFinder()
        self.wildcard = f".*{title}.*"

    def wait_present(self):
        if_present = False
        for i in range(20)[::-1]:
            try:
                self.win.find_window_wildcard(self.wildcard)
                self.win.set_foreground()
                if_present = True
                break
            except:
                print(f"对话框置顶剩余重试次数：{i}...")
                time.sleep(1)

        if not if_present:
            raise UserWarning("文件上传框没有正确出现/选取...")


def write(text_content):
    pyperclip.copy(text_content)
    time.sleep(0.5)
    pyautogui.hotkey('ctrl', 'v')


def upload_file_pyauto(data_path, data_name, win):
    time.sleep(2)
    win.set_foreground()
    pyautogui.hotkey('ctrl', 'l')
    time.sleep(1)
    win.set_foreground()
    write(data_path)
    win.set_foreground()
    pyautogui.press('enter')
    time.sleep(2)
    win.set_foreground()
    pyautogui.hotkey('alt', 'n')
    time.sleep(1)
    win.set_foreground()
    write(data_name)
    win.set_foreground()
    pyautogui.press('enter')


class WindowFinder:
    """Class to find and make focus on a particular Native OS dialog/Window """

    def __init__(self):
        self._handle = None

    def find_window(self, class_name, window_name=None):
        """Pass a window class name & window name directly if known to get the window """
        self._handle = win32gui.FindWindow(class_name, window_name)

    def _window_enum_callback(self, hwnd, wildcard):
        '''Call back func which checks each open window and matches the name of window using reg ex'''
        if re.match(wildcard, str(win32gui.GetWindowText(hwnd))) != None:
            self._handle = hwnd

    def find_window_wildcard(self, wildcard):
        """ This function takes a string as input and calls EnumWindows to enumerate through all open windows """
        self._handle = None
        win32gui.EnumWindows(self._window_enum_callback, wildcard)

    def set_foreground(self):
        """Get the focus on the desired open window"""
        win32gui.SetForegroundWindow(self._handle)


if __name__ == '__main__':
    win = WindowFinder()
    win.find_window_wildcard(".*打开222.*")

    out_e = None

    try:
        win.set_foreground()
    except Exception as e:
        out_e = e

    print(e)
