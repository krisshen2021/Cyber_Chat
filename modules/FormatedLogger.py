import logging
import colorlog

# 创建日志记录器
logging.getLogger("httpx").setLevel(logging.CRITICAL)
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# 创建处理器，并设置级别为INFO
handler = logging.StreamHandler()
handler.setLevel(logging.INFO)

# 定义日志输出格式
log_format = "%(log_color)s%(levelname)s: \033[94m%(message)s\033[0m"
formatter = colorlog.ColoredFormatter(log_format, log_colors={'INFO': 'red'})

# 将格式器设置到处理器上
handler.setFormatter(formatter)

# 将处理器添加到日志记录器上
logger.addHandler(handler)

# 测试日志
# logger.info("这是一个info级别的日志，颜色为红色。")
