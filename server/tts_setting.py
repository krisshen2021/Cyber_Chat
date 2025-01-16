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
playHT_api_key = os.getenv("playHT_api_key")

endpoint_list = [
    {
        "name": "Openai",
        "server_url": "https://api.xiaoai.plus/v1/audio/speech",
        "headers": {
            "Authorization": f"Bearer {openai_api_key}",
            "Content-Type": "application/json",
        },
        "payload_tts": {
            "model": "tts-1",
            "input": "",
            "voice": {"male": "echo", "female": "nova"},
            "response_format": "mp3",
        },
    },
    {
        "name": "Unrealspeech",
        "server_url": "https://api.v7.unrealspeech.com/stream",
        "headers": {
            "Authorization": f"Bearer {unrealspeech_api_key}",
            "Content-Type": "application/json",
        },
        "payload_tts": {
            "Text": "",
            "VoiceId": {"male": "Dan", "female": "Liv"},
            "Bitrate": "192k",
            "Speed": "0",
            "Pitch": "1.08",
            "Codec": "libmp3lame",
            "Temperature": 0.45,
        },
    },
    {
        "name": "PlayHT",
        "server_url": "https://api.play.ht/api/v2/tts/stream",
        "headers": {
            "content-type": "application/json",
            "AUTHORIZATION": f"{playHT_api_key}",
            "X-USER-ID": "tmCm6IqLHePxtaz8BMu9f4BwSfp1",
            "accpet": "audio/mpeg",
        },
        "payload_tts": {
            "text": "",
            "voice": {
                "male": "s3://voice-cloning-zero-shot/d99d35e6-e625-4fa4-925a-d65172d358e1/adriansaad/manifest.json",
                "female": "s3://voice-cloning-zero-shot/ff414883-0e32-4a92-a688-d7875922120d/original/manifest.json",
            },
            "output_format": "mp3",
            "voice_engine": "PlayHT2.0-turbo",
            "quality": "medium",
            "sample_rate": 16000,
            "speed": 1.0,
            "temperature": 0.75,
        },
    },
]


def tts_select_endpoint():
    clear_screen()
    print(f"{BOLD}{YELLOW}Available Rest API of TTS endpoints:{RESET}")
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
