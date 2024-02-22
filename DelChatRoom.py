import threading
from global_sets import chatRoomList

class DelRoom:
    def __init__(self, conid):
        self.conid = conid
        self.timer = threading.Timer(300, self.del_room)
        self.timer.start()
        print(f">>> Room {self.conid} Timer Starts")

    def del_room(self):
        if self.conid in chatRoomList:
            del chatRoomList[self.conid]
            print(f">>> Room {self.conid} was removed")

    def cancel_timer(self):
        self.timer.cancel()
        print(f">>> Room {self.conid} Timer Canceled")