# 配置基本的日志格式和级别
import logging, sys
from pathlib import Path

project_root = str(Path(__file__).parents[1])
if project_root not in sys.path:
    sys.path.append(project_root)
    
from modules.ANSI_tool import ansiColor
# logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
YELLOW = ansiColor.YELLOW
BLUE = ansiColor.BLUE
RESET = ansiColor.RESET

class ColorFormatter(logging.Formatter):
    def format(self, record):
        levelname = f"{YELLOW}{record.levelname}{RESET}"
        message = f"{BLUE}{record.getMessage()}{RESET}"
        return f"{levelname} - {message}"

logger = logging.getLogger()
logger.setLevel(logging.INFO)
httpx_logger = logging.getLogger("httpx")
httpx_logger.setLevel(logging.WARNING)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = ColorFormatter()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)