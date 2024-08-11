import sys, os, math, yaml, requests
from pathlib import Path
from httpx import Timeout
from ruamel.yaml import YAML

project_root = str(Path(__file__).parents[1])
if project_root not in sys.path:
    sys.path.append(project_root)
from modules.ANSI_tool import ansiColor
from clear_screen import clear_screen
from remote_api_hub import openairouter_sync_client, openairouter_client, remote_OAI_config

config_path = os.path.join(project_root, "config", "config.yml")
with open(config_path, "r") as file:
    config_data = yaml.safe_load(file)
from dotenv import load_dotenv

load_dotenv()
picked_routers = remote_OAI_config

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
        f"{BOLD}{BLUE}Enter a number to select a model, 'n' for next page, 'p' for previous page, 'b' to go back.{RESET}"
    )


def update_config(endpoint):
    yaml = YAML()
    yaml.preserve_quotes = True  # 保留引号
    yaml.indent(mapping=2, sequence=4, offset=2)  # 设置缩进
    yaml.width = 4096  # 设置很大的行宽，防止自动换行
    yaml.preserve_comments = True  # 保留注释
    with open(config_path, "r") as file:
        config = yaml.load(file)
    if endpoint != "tabby":
        config["remoteapi_endpoint"] = endpoint
        config["using_remoteapi"] = True
    else:
        local_tabby_server_port = input("enter tabby server port(default-5555):")
        if local_tabby_server_port == "":
            print("use default port 5555")
            local_tabby_server_base = f"http://localhost:5555/v1"
        elif local_tabby_server_port.isdigit():
            local_tabby_server_base = f"http://localhost:{local_tabby_server_port}/v1"
        else:
            print("invalid port, use default port 5555")
            local_tabby_server_base = f"http://localhost:5555/v1"
        config["local_tabby_server_base"] = local_tabby_server_base
        config["using_remoteapi"] = False
    with open(config_path, "w") as file:
        yaml.dump(config, file)
        
        


def sub_select_options():
    clear_screen()
    print(f"{BOLD}{YELLOW}Select an option:{RESET}")
    print(f"{RED}1{RESET}: Use OAI endpoint")
    print(f"{RED}2{RESET}: Use None OAI endpoint")
    print(f"{RED}3{RESET}: Use local Tabby server(not recommanded)")
    choice = input("Enter your choice (1/2/3): ")
    return choice
def sub_select_openai_routers():
    clear_screen()
    print(f"{BOLD}{YELLOW}Available routers points: {RESET}\n")
    for i, router in enumerate(picked_routers):
        print(f"{RED}{i+1}{RESET}: {BOLD}{CYAN}{router}{RESET}")
    selected_index = input("Enter the number of your chosen router, enter 'b' to back: ")
    return selected_index


def select_model():
    choice = None
    OAI_model_list = None
    while True:
        if choice is None:
            choice = sub_select_options()
        if choice == "1": 
            selected_index = sub_select_openai_routers()
            # config_data["using_remoteapi"] = True
            # config_data["remoteapi_endpoint"] = "openairouter"
            if selected_index =='b':
                choice = None
                continue
            elif selected_index.isdigit() and 1 <= int(selected_index) <= len(list(picked_routers.keys())):
                submenu = True
                while True:
                    if submenu:
                        index = int(selected_index) - 1
                        router_names = list(picked_routers.keys())
                        if 0 <= index < len(router_names):
                            selected_router = router_names[index]
                            router_details = picked_routers[selected_router]
                            api_key = router_details["api_key"]
                            base_url = router_details["url"]
                        openairouter_sync_client.base_url = base_url
                        openairouter_sync_client.api_key = api_key
                        openairouter_client.base_url = base_url
                        openairouter_client.api_key = api_key
                        # openairouter_modellist = openairouter_sync_client.models.list(timeout=timeout)
                        headers = {
                            "accept": "application/json",
                            "Authorization": f"Bearer {openairouter_sync_client.api_key}",
                        }
                        url = base_url+"/models"
                        print(url)
                        response = requests.get(url=url,headers=headers,timeout=300)
                        response.raise_for_status()
                        openairouter_modellist = response.json()
                        OAI_model_list = openairouter_modellist
                        if "data" in openairouter_modellist:
                            openairouter_modellist = openairouter_modellist["data"]
                        # 对模型列表按id进行排序
                        sorted_models = sorted(openairouter_modellist, key=lambda x: x['id'].lower())
                        OAI_model_list['data'] = sorted_models
                        openairouter_model: str = ""
                        current_page = 1
                        items_per_page = 20
                        total_pages = math.ceil(len(sorted_models) / items_per_page)
                        while True:
                            display_models(sorted_models, current_page, items_per_page)
                            user_input = input(">>> ").lower()
                            if user_input == "b":
                                submenu = False
                                choice = "1"
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
                                if 0 <= selected_index <= len(sorted_models):
                                    openairouter_model = sorted_models[selected_index-1]['id']
                                    confirm=input("You have selected the model: "+f"{BOLD}{YELLOW}{openairouter_model}{RESET}"+". confirm? (y/n)")
                                    if confirm == "y":
                                        update_config("openairouter")
                                        return openairouter_model, OAI_model_list
                                    else:
                                        continue
                                else:
                                    input(
                                        "Invalid input. Please enter a valid index number. Press Enter to continue..."
                                    )
                            else:
                                input(
                                    "Invalid input. Please enter a valid command. Press Enter to continue..."
                                )              
                    else:
                        break
            else:
                input("Invalid input. Please enter a valid index number. Press Enter to continue...")
                continue
        elif choice == "2":
            while True:
                clear_screen()
                endpoints = ["claude", "cohere"]
                print(f"\n{BOLD}{YELLOW}Available endpoints:{RESET}")
                for i, endpoint in enumerate(endpoints, 1):
                    print(f"{RED}{i}{RESET}: {CYAN}{endpoint}{RESET}")

                endpoint_choice = input("Enter the number of your chosen endpoint, 'b' to back: ").lower()
                if endpoint_choice.isdigit():
                    if 1 <= int(endpoint_choice) <= len(endpoints):
                        chosen_endpoint = endpoints[int(endpoint_choice) - 1]
                        update_config(chosen_endpoint)
                        clear_screen()
                        return "openai/gpt-3.5-turbo", None
                    else:
                        input(f"{RED}Invalid choice. Enter to retry{RESET}")
                        clear_screen()
                        continue
                elif endpoint_choice == "b":
                    choice = None
                    break
                else:
                    input(f"{RED}Invalid choice. Enter to retry{RESET}")
                    clear_screen()
                    continue
        elif choice == "3":
            update_config("tabby")
            clear_screen()
            return "openai/gpt-3.5-turbo", None
        else:
            input(f"{RED}Invalid choice. Enter to retry{RESET}")
            choice = None
            continue
        
