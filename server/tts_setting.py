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
unrealspeech_api_key = os.getenv("unrealspeech_api_key")

endpoint_list = [
    {
        "name": "openai",
        "server_url": "https://api.xiaoai.plus/v1/audio/speech",
        "headers": {
            "Authorization": f"Bearer {openai_api_key}",
            "Content-Type": "application/json",
        },
        "payload_tts": {
            "model": "tts-1",
            "input": "",
            "voice": "nova",
            "response_format": "wav"
        },
    },
    {
        "name": "unrealspeech",
        "server_url": "https://api.v7.unrealspeech.com/stream",
        "headers": {
            "Authorization": f"Bearer {unrealspeech_api_key}",
            "Content-Type": "application/json",
        },
        "payload_tts": {
            "Text": "",
            "VoiceId": "Liv",
            "Bitrate": "192k",
            "Speed": "0",
            "Pitch": "1.08",
            "Codec": "pcm_s16le",
            "Temperature": 0.45
        }
    }
]

def select_endpoint():
    clear_screen()
    print(f"{BOLD}{YELLOW}Available Rest API of tts endpoints:{RESET}")
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