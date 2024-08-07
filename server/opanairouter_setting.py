import sys, os, math, yaml, requests, json, re
from pathlib import Path
from httpx import Timeout
from ruamel.yaml import YAML

project_root = str(Path(__file__).parents[1])
if project_root not in sys.path:
    sys.path.append(project_root)
from modules.ANSI_tool import ansiColor
from clear_screen import clear_screen
from remote_api_hub import openairouter_sync_client, openairouter_client

config_path = os.path.join(project_root, "config", "config.yml")
with open(config_path, "r") as file:
    config_data = yaml.safe_load(file)
from dotenv import load_dotenv

load_dotenv()
picked_routers = [
    {
        "name": "openairouter",
        "url": "https://openrouter.ai/api/v1",
        "api_key": os.environ.get("openairouter_api_key"),
    },
    {
        "name": "groq",
        "url": "https://api.groq.com/openai/v1",
        "api_key": os.environ.get("groq_api_key"),
    },
    {
        "name": "togetherAI",
        "url": "https://api.together.xyz/v1",
        "api_key": os.environ.get("togetherai_api_key"),
    },
]

### Model selector
BLUE = ansiColor.BLUE
CYAN = ansiColor.CYAN
RED = ansiColor.RED
RESET = ansiColor.RESET
BOLD = ansiColor.BOLD
YELLOW = ansiColor.YELLOW

timeout = Timeout(180.0)


def display_models(models, page, items_per_page=10):
    clear_screen()
    print(f"{BOLD}{YELLOW}<< Available models from opanai router >>{RESET}\n")
    start = (page - 1) * items_per_page
    end = start + items_per_page
    for index, model in enumerate(models[start:end], start=start):
        print(f"{RED}{index+1}{RESET}: {BOLD}{CYAN}{model['id']}{RESET}\t")
    print(
        "\n{}Page{} {}{}/{}{}".format(
            YELLOW, RESET, BLUE, page, math.ceil(len(models) / items_per_page), RESET
        )
    )
    print(
        f"{BOLD}{BLUE}Enter a number to select a model, 'n' for next page, 'p' for previous page, or 'q' to quit.{RESET}"
    )


def update_config(endpoint):
    yaml = YAML()
    yaml.preserve_quotes = True  # 保留引号
    yaml.indent(mapping=2, sequence=4, offset=2)  # 设置缩进
    yaml.width = 4096  # 设置很大的行宽，防止自动换行
    yaml.preserve_comments = True  # 保留注释
    with open(config_path, "r") as file:
        config = yaml.load(file)

    config["remoteapi_endpoint"] = endpoint

    with open(config_path, "w") as file:
        yaml.dump(config, file)


def select_model():
    clear_screen()
    print(f"{BOLD}{YELLOW}Select an option for the endpoint:{RESET}")
    print(f"{RED}1{RESET}: Use 'Editor Picked openai liked router' endpoint")
    print(f"{RED}2{RESET}: Keep settings in config.yml file")
    print(f"{RED}3{RESET}: Input another name of endpoint")

    choice = input("Enter your choice (1/2/3): ")

    if choice == "1":
        clear_screen()
        print(f"{BOLD}{YELLOW}Available routers points: {RESET}\n")
        for i, router in enumerate(picked_routers):
            print(f"{RED}{i+1}{RESET}: {BOLD}{CYAN}{router['name']}{RESET}")
        # print(f"{RED}1{RESET}: {BOLD}{CYAN}Openrouter{RESET}")
        # print(f"{RED}2{RESET}: {BOLD}{CYAN}Groq{RESET}")
        selected_index = input("Enter the number of your chosen router: ")
        config_data["using_remoteapi"] = True
        config_data["remoteapi_endpoint"] = "openairouter"
        update_config("openairouter")
        clear_screen()
    elif choice == "2":
        clear_screen()
        return "openai/gpt-3.5-turbo"
    elif choice == "3":
        endpoints = ["deepseek", "xiaoai", "cohere", "nvidia", "mistral", "togetherai"]
        print(f"\n{BOLD}{YELLOW}Available endpoints:{RESET}")
        for i, endpoint in enumerate(endpoints, 1):
            print(f"{RED}{i}{RESET}: {CYAN}{endpoint}{RESET}")

        endpoint_choice = int(input("Enter the number of your chosen endpoint: "))
        if 1 <= endpoint_choice <= len(endpoints):
            chosen_endpoint = endpoints[endpoint_choice - 1]
            update_config(chosen_endpoint)
            clear_screen()
            return "openai/gpt-3.5-turbo"
        else:
            print(f"{RED}Invalid choice. Using default settings.{RESET}")
            clear_screen()
            return "openai/gpt-3.5-turbo"
    else:
        print(f"{RED}Invalid choice. Using default settings.{RESET}")
        return "openai/gpt-3.5-turbo"

    if (
        config_data["using_remoteapi"]
        and config_data["remoteapi_endpoint"] == "openairouter"
    ):
        openairouter_sync_client.base_url = picked_routers[int(selected_index) - 1].get("url")
        openairouter_sync_client.api_key = picked_routers[int(selected_index) - 1].get("api_key")
        openairouter_client.base_url = picked_routers[int(selected_index) - 1].get("url")
        openairouter_client.api_key = picked_routers[int(selected_index) - 1].get("api_key")
        # openairouter_modellist = openairouter_sync_client.models.list(timeout=timeout)
        headers = {
            "accept": "application/json",
            "Authorization": f"Bearer {openairouter_sync_client.api_key}",
        }
        response = requests.get(url=(str(openairouter_sync_client.base_url)+"/models"),headers=headers)
        openairouter_modellist = response.json()
        if "data" in openairouter_modellist:
            openairouter_modellist = openairouter_modellist["data"]
        # 对模型列表按id进行排序
        sorted_models = sorted(openairouter_modellist, key=lambda x: x['id'].lower())
        openairouter_model: str = ""
        current_page = 1
        items_per_page = 20
        total_pages = math.ceil(len(sorted_models) / items_per_page)

        while True:
            display_models(sorted_models, current_page, items_per_page)
            user_input = input(">>> ").lower()

            if user_input == "q":
                print("Exiting...")
                break
            elif user_input == "n":
                if current_page < total_pages:
                    current_page += 1
                else:
                    input("Already on the last page. Press Enter to continue...")
            elif user_input == "p":
                if current_page > 1:
                    current_page -= 1
                else:
                    input("Already on the first page. Press Enter to continue...")
            elif user_input.isdigit():
                selected_index = int(user_input)
                if 0 <= selected_index < len(sorted_models):
                    openairouter_model = sorted_models[selected_index-1]['id']
                    break
                else:
                    input(
                        "Invalid input. Please enter a valid index number. Press Enter to continue..."
                    )
            else:
                input(
                    "Invalid input. Please enter a valid command. Press Enter to continue..."
                )

        clear_screen()  # 最后清屏
        if openairouter_model:
            print(
                f"{BLUE}Selected model:{RESET} {BOLD}{RED}{openairouter_model}{RESET}"
            )
            return openairouter_model
        else:
            openairouter_model = "openai/gpt-3.5-turbo"
            print(
                f"{BLUE}No model selected. set the model to default:{RESET} {BOLD}{RED}{openairouter_model}{RESET}"
            )
            return openairouter_model
    else:
        clear_screen()
        return "openai/gpt-3.5-turbo"
