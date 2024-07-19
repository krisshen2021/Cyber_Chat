from modules.ANSI_tool import ansiColor
BLUE = ansiColor.BLUE
YELLOW = ansiColor.YELLOW
RESET = ansiColor.RESET
CUSTOM_BAR_FORMAT=f"{BLUE}{{l_bar}}{RESET}{YELLOW}{{bar}}{RESET}| {BLUE}{{rate_fmt}}{RESET}"

class Pbar:
    BarColorer = ansiColor
    def __init__(self) -> None:
        self.customBar = CUSTOM_BAR_FORMAT     
    @classmethod
    def setBar(cls,lbarColor,barColor,ratefmtColor):
        MYBARFORMAT = f"{lbarColor}{{l_bar}}{RESET}{barColor}{{bar}}{RESET}| {ratefmtColor}{{rate_fmt}}{RESET}"
        return MYBARFORMAT
    