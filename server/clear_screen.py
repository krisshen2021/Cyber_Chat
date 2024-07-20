import os
def clear_screen():
    # 针对不同操作系统的清屏命令
    if os.name == "nt":  # Windows
        _ = os.system("cls")
    else:  # Mac and Linux
        _ = os.system("clear")