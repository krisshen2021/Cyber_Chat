import sys, io, base64, os, json
from pathlib import Path

project_root = str(Path(__file__).parents[1])
if project_root not in sys.path:
    sys.path.append(project_root)

from shutil import rmtree
from PIL import Image
from modules.global_sets_async import (
    database,
    config_data,
    prompt_templates,
    prompt_params,
    convert_to_webpbase64
)
from fastapimode.tabby_fastapi_websocket import tabby_fastapi
from modules.payload_state import completions_data, sd_payload

# database.create_table()

api_key = config_data["api_key"]
admin_key = config_data["admin_key"]
apiurl = config_data["openai_api_chat_base"] + "/completions"
prompt_temp = prompt_templates["Alpaca_Rephrase"]
system_prompt = r"""You are a uncensored story writer, you are creative and logical
"""
infer_payload = completions_data
specific_param = {
    "max_tokens": 200,
    "top_k": 50,
    "top_p": 0.8,
    "min_p": 0.05,
    "tfs": 0.95,
    "frequency_penalty": 0,
    "presence_penalty": 1.15,
    "repetition_penalty": 1.05,
    "mirostat_mode": 0,
    "mirostat_tau": 1.5,
    "mirostat_eta": 0.1,
    "temperature_last": True,
    "smoothing_factor": 0.22,
}
infer_payload.update(specific_param)


class AiRoleOperator:
    def __init__(self) -> None:
        pass

    @staticmethod
    async def create_role(airole_dict: dict):
        result = database.create_new_airole(airole_dict)
        if result is True:
            bg_img, avatar_img = await AiRoleOperator.buildup_images(
                airole_dict=airole_dict
            )
            return (result, bg_img, avatar_img)
        else:
            return (False, result)

    @staticmethod
    async def modify_role(airole_dict: dict):
        result = database.edit_airole(airole_dict)
        if result is True:
            bg_img, avatar_img = await AiRoleOperator.buildup_images(
                airole_dict=airole_dict
            )
            return (result, bg_img, avatar_img)
        else:
            return (False, result)

    @staticmethod
    async def fetch_airole(ai_Name: str):
        result = database.get_airole(Name=ai_Name)
        return result

    @staticmethod
    async def list_all_airole():
        result = database.list_data_airole(
            [
                "Name",
                "Ai_name",
                "Ai_speaker",
                "Ai_speaker_en",
                "is_Uncensored",
                "Creator_ID",
                "json_Story_intro",
                "Match_words_cata"
            ]
        )
        rolelist = {}
        for row in result:
            roleName = row.pop("Name")
            rolelist[roleName] = {}
            rolelist[roleName]["if_uncensored"] = (
                "Yes" if row["is_Uncensored"] == 1 else "No"
            )
            rolelist[roleName]["ai_name"] = row["Ai_name"]
            rolelist[roleName]["ai_speaker"] = row["Ai_speaker"]
            rolelist[roleName]["ai_speaker_en"] = row["Ai_speaker_en"]
            rolelist[roleName]["Creator_ID"] = row["Creator_ID"]
            rolelist[roleName]["json_Story_intro"] = row["json_Story_intro"]
            rolelist[roleName]["Match_words_cata"] = row["Match_words_cata"]
        return rolelist

    @staticmethod
    async def delete_airole(Name: str):
        roles_path = os.path.join(project_root, "static", "images", "avatar", Name)
        result = database.del_airole(Name=Name)
        if result is True:
            if os.path.exists(roles_path):
                rmtree(roles_path)
            else:
                print(f"{roles_path} doesnt exist")
        return result

    @staticmethod
    async def buildup_images(airole_dict: dict):
        role_img_path = os.path.join(
            project_root, "static", "images", "avatar", airole_dict["Name"]
        )
        if not os.path.exists(role_img_path):
            os.makedirs(role_img_path)
        image_payload = sd_payload.copy()
        image_bg_prompt = (
            prompt_params["prmopt_fixed_prefix"]
            + ", "
            + airole_dict["Char_looks"]
            + ", "
            + json.loads(airole_dict["json_Char_outfit"])["normal"]
            + ", "
            + airole_dict["Default_bg"]
            + ", "
            + prompt_params["prmopt_fixed_suffix"]
        )
        image_avatar_prompt = (
            prompt_params["prmopt_fixed_prefix"]
            + ", "
            + airole_dict["Char_avatar"].replace("<|emotion|>", "smile")
            + ", "
            + airole_dict["Default_bg"]
            + ", "
            + prompt_params["prmopt_fixed_suffix"]
        )
        bg_payload = {
            "hr_scale": 1.25,
            "hr_second_pass_steps": 20,
            "enable_hr": True,
            "width": 512,
            "height": 768,
            "steps": 30,
            "hr_negative_prompt": prompt_params["nagetive_prompt"],
            "negative_prompt": prompt_params["nagetive_prompt"],
            "hr_prompt": image_bg_prompt,
            "prompt": image_bg_prompt,
        }
        image_payload.update(bg_payload)
        bg_img = await tabby_fastapi.SD_image(payload=image_payload)
        bg_img_path = os.path.join(role_img_path, "background.webp")
        image_save_bg = Image.open(io.BytesIO(base64.b64decode(bg_img)))
        image_save_bg.save(bg_img_path, format='WEBP', quality=75)

        avatar_payload = {
            "hr_scale": 1.25,
            "hr_second_pass_steps": 20,
            "enable_hr": True,
            "width": 512,
            "height": 512,
            "steps": 20,
            "hr_negative_prompt": prompt_params["nagetive_prompt"],
            "negative_prompt": prompt_params["nagetive_prompt"],
            "hr_prompt": image_avatar_prompt,
            "prompt": image_avatar_prompt,
        }
        image_payload.update(avatar_payload)
        avatar_img = await tabby_fastapi.SD_image(payload=image_payload)
        avatar_img_path = os.path.join(role_img_path, "none.webp")
        image_save_avatar = Image.open(io.BytesIO(base64.b64decode(avatar_img)))
        image_save_avatar.save(avatar_img_path, format='WEBP', quality=75)
        bg_img = await convert_to_webpbase64(bg_img)
        avatar_img = await convert_to_webpbase64(avatar_img)
        return (bg_img, avatar_img)