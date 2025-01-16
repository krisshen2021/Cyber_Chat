import os
from dotenv import load_dotenv
from clear_screen import clear_screen
from modules.ANSI_tool import ansiColor
BLUE = ansiColor.BLUE
CYAN = ansiColor.CYAN
RED = ansiColor.RED
RESET = ansiColor.RESET
BOLD = ansiColor.BOLD
YELLOW = ansiColor.YELLOW
load_dotenv()

openai_api_key = os.getenv("xiaoai_api_key")
groq_api_key = os.getenv("groq_api_key")

endpoint_list = [
    {
        "name": "openai",
        "server_url": "https://api.xiaoai.plus/v1/audio/transcriptions",
        "headers": {
            "Authorization": f"Bearer {openai_api_key}"
        },
        "data":{
            "model": "whisper-1"
        }
    },
    {
        "name": "groq",
        "server_url": "https://api.groq.com/openai/v1/audio/transcriptions",
        "headers": {
            "Authorization": f"Bearer {groq_api_key}"
        },
        "data":{
            "model": "whisper-large-v3-turbo"
        }
    }
]

def stt_select_endpoint():
    clear_screen()
    print(f"{BOLD}{YELLOW}Available Rest API of STT endpoints:{RESET}")
    for i, endpoint in enumerate(endpoint_list, 1):
        print(f"{RED}{i}{RESET}. {CYAN}{endpoint['name']}{RESET}")
    
    while True:
        try:
            choice = int(input("Select an endpoint (enter the number): "))
            if 1 <= choice <= len(endpoint_list):
                clear_screen()
                return endpoint_list[choice - 1]
            else:
                print("Invalid choice. Please try again.")
        except ValueError:
            print("Invalid input. Please enter a number.")