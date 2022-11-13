from typing import List


class UserDirDispatcher:

    def __init__(self, user_data_number) -> None:
        self.user_data_number = user_data_number
        self.init_workers()

    def init_workers(self):
        self.dirs: List[UserDir] = []
        for i in range(self.user_data_number):
            self.dirs.append(UserDir(i+1))

    def get_an_idle_dir(self):
        dir_ = [d for d in self.dirs if d.is_idle][0]
        dir_.occupy()
        return dir_


class UserDir:
    IDLE = 'idle'
    BUSY = 'busy'

    def __init__(self, id_) -> None:
        self.dir = f"user-data-dir-{id_}"
        self.id = id_
        self.status = UserDir.IDLE

    @property
    def is_idle(self):
        return self.status == UserDir.IDLE

    def occupy(self):
        self.status = UserDir.BUSY

    def free(self):
        self.status = UserDir.IDLE
