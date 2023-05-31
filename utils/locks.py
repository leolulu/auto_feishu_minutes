import threading
import multiprocessing


upload_select_lock = threading.Lock()
global_thread_lock = threading.Lock()
global_multiprocessing_lock = multiprocessing.Lock()
