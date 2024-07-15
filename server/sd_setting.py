import httpx,os,sys
from ruamel.yaml import YAML
from pathlib import Path
project_root = str(Path(__file__).parents[1])
if project_root not in sys.path:
    sys.path.append(project_root)
from modules.ANSI_tool import ansiColor

RED = ansiColor.RED
BLUE = ansiColor.BLUE
RESET = ansiColor.RESET
CYAN = ansiColor.CYAN
BOLD = ansiColor.BOLD

yaml = YAML()
yaml.preserve_quotes = True  # 保留引号
yaml.indent(mapping=2, sequence=4, offset=2)  # 设置缩进
yaml.width = 4096  # 设置很大的行宽，防止自动换行
yaml.preserve_comments = True  # 保留注释

def clear_screen():
    # 跨平台清屏
    os.system('cls' if os.name == 'nt' else 'clear')
    
def get_valid_url():
    while True:
        SDAPI_url = input(f"{BLUE}Please enter the API URL: {RESET}")
        try:
            # 尝试连接
            response = httpx.get(f"{SDAPI_url}/sdapi/v1/samplers", timeout=10)
            response.raise_for_status()  # 如果状态码不是200，将引发异常
            return SDAPI_url
        except (httpx.ConnectError, httpx.HTTPStatusError) as e:
            print(f"{RED}Error connecting to the API: {e}{RESET}")
            retry = input(f"{CYAN}Do you want to try again? (yes/no): {RESET}")
            if retry.lower() != 'yes':
                sys.exit("Exiting the program.")
        except Exception as e:
            print(f"{RED}An unexpected error occurred: {e}{RESET}")
            retry = input(f"{CYAN}Do you want to try again? (yes/no): {RESET}")
            if retry.lower() != 'yes':
                sys.exit("Exiting the program.")

def update_SDAPI_config():
    update = input(f"{BOLD}{CYAN}Do you want to update stable diffusion api parameters? (yes/no): {RESET}")
    if update.lower() != 'yes':
        return

    clear_screen()
    SDAPI_url = get_valid_url()

    # Get samplers list
    clear_screen()
    response = httpx.get(f"{SDAPI_url}/sdapi/v1/samplers")
    samplers = response.json()
    print(f"{BOLD}{CYAN}Available samplers:{RESET}")
    for i, sampler in enumerate(samplers):
        print(f"{RED}{i + 1}.{RESET} {sampler['name']}")
    sampler_index = int(input(f"{BLUE}Select a sampler (enter number): {RESET}")) - 1
    sampler_name = samplers[sampler_index]['name']

    # Get models list
    clear_screen()
    response = httpx.get(f"{SDAPI_url}/sdapi/v1/sd-models")
    models = response.json()
    print(f"{BOLD}{CYAN}Available models:{RESET}")
    for i, model in enumerate(models):
        print(f"{RED}{i + 1}.{RESET} {model['model_name']}")
    model_index = int(input(f"{BLUE}Select a model (enter number): {RESET}")) - 1
    sd_model_checkpoint = models[model_index]['model_name']

    # Get upscale modes list
    clear_screen()
    response = httpx.get(f"{SDAPI_url}/sdapi/v1/latent-upscale-modes")
    upscalers = response.json()
    print(f"{BOLD}{CYAN}Available upscale modes:{RESET}")
    for i, upscaler in enumerate(upscalers):
        print(f"{RED}{i + 1}.{RESET} {upscaler['name']}")
    upscaler_index = int(input(f"{BLUE}Select an upscale mode (enter number): {RESET}")) - 1
    hr_upscaler = upscalers[upscaler_index]['name']

    # Confirm selections
    clear_screen()
    print(f"\n{BOLD}{CYAN}Your selections:")
    print(f"{BOLD}{CYAN}API URL:{RESET} {SDAPI_url}")
    print(f"{BOLD}{CYAN}Sampler:{RESET} {sampler_name}")
    print(f"{BOLD}{CYAN}Model:{RESET} {sd_model_checkpoint}")
    print(f"{BOLD}{CYAN}Upscale mode:{RESET} {hr_upscaler}")

    confirm = input(f"{BOLD}{CYAN}Confirm these selections? (yes/no): {RESET}")
    if confirm.lower() != 'yes':
        clear_screen()
        return update_SDAPI_config()

    # Update configuration file
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'config.yml')
    with open(config_path, 'r') as f:
        config = yaml.load(f)

    config['SDAPI_url'] = SDAPI_url
    config['sampler_name'] = sampler_name
    config['sd_model_checkpoint'] = sd_model_checkpoint
    config['hr_upscaler'] = hr_upscaler

    with open(config_path, 'w') as f:
        yaml.dump(config, f)

    clear_screen()
    print(f"{BOLD}{CYAN}Configuration updated{RESET}")

if __name__ == "__main__":
    update_SDAPI_config()