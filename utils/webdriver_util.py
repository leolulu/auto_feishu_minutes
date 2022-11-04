from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


def wait_element_presence(self, xpath, timeout=30, poll_frequency=1):
    return WebDriverWait(self, timeout, poll_frequency).until(
        EC.presence_of_element_located((By.XPATH, xpath))
    )


def wait_element_visible(self, xpath, timeout=30, poll_frequency=1):
    return WebDriverWait(self, timeout, poll_frequency).until(
        EC.visibility_of_element_located((By.XPATH, xpath))
    )


def wait_element_clickable(self, xpath, timeout=30, poll_frequency=1):
    return WebDriverWait(self, timeout, poll_frequency).until(
        EC.element_to_be_clickable((By.XPATH, xpath))
    )


JS_DROP_FILE = """
    var target = arguments[0],
        offsetX = arguments[1],
        offsetY = arguments[2],
        document = target.ownerDocument || document,
        window = document.defaultView || window;

    var input = document.createElement('INPUT');
    input.type = 'file';
    input.onchange = function () {
      var rect = target.getBoundingClientRect(),
          x = rect.left + (offsetX || (rect.width >> 1)),
          y = rect.top + (offsetY || (rect.height >> 1)),
          dataTransfer = { files: this.files };

      ['dragenter', 'dragover', 'drop'].forEach(function (name) {
        var evt = document.createEvent('MouseEvent');
        evt.initMouseEvent(name, !0, !0, window, 0, 0, 0, x, y, !1, !1, !1, !1, 0, null);
        evt.dataTransfer = dataTransfer;
        target.dispatchEvent(evt);
      });

      setTimeout(function () { document.body.removeChild(input); }, 25);
    };
    document.body.appendChild(input);
    return input;
"""


def drag_and_drop_file(drop_target, path):
    driver = drop_target.parent
    file_input = driver.execute_script(JS_DROP_FILE, drop_target, 0, 0)
    file_input.send_keys(path)
