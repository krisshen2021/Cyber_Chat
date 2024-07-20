#!/bin/bash

# 获取脚本所在目录的绝对路径
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# 检查是否安装了 tmux
if ! command -v tmux &> /dev/null
then
    # 如果没有安装 tmux，则尝试安装
    sudo apt-get update
    sudo apt-get install -y tmux
fi

# 启动一个名为 cyberchat 的 tmux 会话
tmux new-session -d -s cyberchat

# 在第一个窗格中激活虚拟环境并运行 cyberchat.py
tmux send-keys -t cyberchat "cd $SCRIPT_DIR && source venv/bin/activate && python cyberchat.py" C-m

# 创建垂直分割的第二个窗格，激活虚拟环境并运行 server/remote_server.py
tmux split-window -h -t cyberchat
tmux send-keys -t cyberchat "cd $SCRIPT_DIR && source venv/bin/activate && python server/start_server.py" C-m

# 选择左侧窗格
tmux select-pane -t cyberchat:0.0

# 附加到 tmux 会话
tmux attach-session -t cyberchat
