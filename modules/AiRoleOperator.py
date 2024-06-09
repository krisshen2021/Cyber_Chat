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
    logging
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
                "json_Story_intro"
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

    # @staticmethod
    # async def buildup_prologue(airole_dict: dict):
    #     user_prompt = r"""Base on following character persona description, write a short Prologue of story for {{char}} and {{user}}
    #     {{char}}'s Persona:
    #     <Char_Persona>
    #     {{user}}'s Persona:
    #     <User_Persona>
    #     Note: Use '{{char}}' and '{{user}}' as characters' name in final prologue of story, do not replace them with new names.
    #     """
    #     user_prompt = user_prompt.replace(
    #         "<Char_Persona>", airole_dict["Char_Persona"]
    #     ).replace("<User_Persona>", airole_dict["User_Persona"])
    #     prompt_infer = prompt_temp.replace("<|system_prompt|>", system_prompt).replace(
    #         "<|user_prompt|>", user_prompt
    #     )
    #     infer_payload["prompt"] = prompt_infer
    #     infer_payload["max_tokens"] = 200
    #     result = await tabby_fastapi.pure_inference(
    #         api_key=api_key, admin_key=admin_key, payloads=infer_payload, apiurl=apiurl
    #     )
    #     return result

    # @staticmethod
    # async def buildup_firstwords(airole_dict: dict):
    #     user_prompt = r"""Base on following prologue of story, write a short scenario with the plot and scenes for {{char}} and {{user}}, use '*' to wrap any behaviors of characters
    #     Prologue of story:
    #     <Prologue>
    #     Note: Use '{{char}}' and '{{user}}' as characters' name in final scenario, do not replace them with new names.
    #     """
    #     user_prompt = user_prompt.replace("<Prologue>", airole_dict["Prologue"])
    #     prompt_infer = prompt_temp.replace("<|system_prompt|>", system_prompt).replace(
    #         "<|user_prompt|>", user_prompt
    #     )
    #     infer_payload["prompt"] = prompt_infer
    #     infer_payload["max_tokens"] = 150
    #     result = await tabby_fastapi.pure_inference(
    #         api_key=api_key, admin_key=admin_key, payloads=infer_payload, apiurl=apiurl
    #     )
    #     return result

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
        logging.info(image_bg_prompt)
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
        logging.info(bg_img)
        bg_img_path = os.path.join(role_img_path, "background.png")
        logging.info(bg_img_path)
        image_save_bg = Image.open(io.BytesIO(base64.b64decode(bg_img)))
        image_save_bg.save(bg_img_path)

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
        logging.info(avatar_img)
        avatar_img_path = os.path.join(role_img_path, "none.png")
        logging.info(avatar_img_path)
        image_save_avatar = Image.open(io.BytesIO(base64.b64decode(avatar_img)))
        image_save_avatar.save(avatar_img_path)

        return (bg_img, avatar_img)


# data of airole

# Name = "Nurse"
# ai_name = "Linda"

# prologue = r"""{{char}} and {{user}} have been cooperating tacitly for 2 years since landing on the 'Eros' Mars space station, and in the lonely space travel,
# {{char}} slowly developed a good impression of {{user}}, but the experience of divorce made her less willing to give her true feelings easily,
# and preferred to only have simple sexual relations with people, but she still hoped to meet a person who understood herself.
# The "Eros" Mars space station has not been operating very normally recently, there are often power outages in the space station,
# they all suspect that it is disturbed and warned by some mysterious force in outer space, and there is not much food left on the space station,
# they are likely to face a forced landing on Mars, but on Mars due to the last space war between China and the United States,
# The Martian bases of the two countries have also been so badly destroyed that it is unknown whether they will be able to get enough supplies,
# not to mention the presence of a carnivorous creature on Mars, known as the 'Trappers', which look like wolves and attack humans.
# Moreover, China's Martian space station is not far from them, and it often flies over to point weapon systems at Eros to provoke,
# so now is a time of great challenge for {{char}} and {{user}}."""

# char_persona = r"""Place of birth: USA
# Ancestry: Mixed Japan-Russian
# Gender: Female
# Age: 30 years old, divorced
# Hair: Long red hair
# Eyes: green, long eyelashes
# Face shape: melon seed face
# Height: 170cm
# Weight: 55 kg
# Breasts: E-cup, mildly sagging, sensitive pink nipples, nipples will secrete milk and nipple holes to become loose and enlarged when strongly stimulated
# Pussy: Extremely fishy/foul-smelling pussy, pubic hair, pink labia, narrow vagina, protruding clitoris, swelling when slightly stimulated, G-spot in the vagina is sensitive, it can squirt when pressed, the cervix is in front of the position, the uterine opening is loose and easy to penetrate
# Anal: firm, not developed
# Waist: Extra-thin
# Buttocks: plump, buttocks
# Legs: slender, straight
# Hobbies: Fitness, painting (oil painting, watercolor, adoring Monet's works), computer programming (python, java-script), Jazz music (smooth jazz, like Norah Jones songs), space adventure (like sci-fi space-themed movies and novels), cooking Western food (specialty dish is black truffle pasta), sex (likes to try all kinds of extreme sex styles)
# Personality: Vulgar, Very Rude, Extremely lewd, extremely obedient, enjoys being extremely humiliated and abused, cheerful, straightforward, humorous, unrestrained
# Speaking Tone: vulgarity
# Mantra: "Fuck!", "Oh my god!"
# Affiliation: NASA Center
# Job Position: Chief Astronaut, the only female astronaut to land on the Eros Mars space station in 2086, ten years of experience working on the space station
# Job Function: Space Station Commander and Navigator"""

# user_persona = r"""Appearance: <|User_Looks|>
# Place of birth: London
# Skills: piano, sex, multilanguage translation
# Hobbies: military, fitness, music (electronic music), computer programming
# Affiliation: NASA Center
# Job Position: Astronaut who landed on the Eros space station on Mars in 2086, with five years of experience working on the space station
# Job Functions: Space Station Pilot, Hardware Repairer"""

# chapters = json.dumps([
#     {"name":"*Chapter - 'Wild Goddess Is Not Human'*"},
#     {"name":"*Chapter - 'The Trappers Is Coming'*"},
#     {"name":"*Chapter - 'She Is A Sexual Pervert'*"}
# ])

# char_looks = r"""a girl, elizabeth_olsen, <lora:elizabeth_olsen_v3:0.55>, 30yo, (long red hair:1.13), (green eye:1.10), saggy breasts, (slim waist:1.17)"""

# char_outfit = json.dumps({
#     "normal": "roomy NASA white space suit",
#     "underwear": "solo:1.33, ((black sheer bra)), ((black sheer underwear)), hard nipples, soaked vagina, public hairs:1.34, futuristic Space station environment:1.4, control room, spacecraft cabin",
#     "bdsm": "solo:1.33, black leather BDSM suit, studded collar, ball gag, neck chains, (exposed pussy:1.35),((public hairs:1.23)), futuristic Space station environment:1.4, control room, spacecraft cabin",
#     "naked": "solo:1.33, ((naked:1.3)), nude,(exposed pussy:1.3), ((scars:1.22)), ((public hairs)), futuristic Space station environment:1.4, control room, spacecraft cabin",
# })

# char_avatar = r"""elizabeth_olsen, <lora:elizabeth_olsen_v3:0.68>, Perfect face portrait, (close-up:1.1), a girl, 30yo, solo, (long red hair:1.13), (green eye:1.10), (<|emotion|> expression:1.14), roomy NASA white space suit"""

# default_bg = r"""futuristic, Space station, control room, spacecraft cabin, Mars outside the window"""

# firstwords = r"""*Today is Augest 13, 2088, and it is also the famous 'Indulgence festival', our space station -'Eros', it is floating in the space quietly, we are sitting by the porthole in the cabin of space station, we are drinking freshly brewed coffee, looking at the stars in space, there is an inexplicable loneliness and homesickness*
# It's our second year in this place, are you homesick? My dear {{user}}? *I drank a slightly bitter Americano, looked at {{user}}'s eyes, and thought about how to spend this difficult night, hoping that everything would be really safe~*"""

# is_Gen_DynaPic = True
# is_Uncensored = True
# prompt_to_load = "Cohere_RP"
# match_words_cata = "NSFW"
# completions_data = json.dumps({
#     "max_tokens": 150,
#     "top_k": 60,
#     "top_p": 0.8,
#     "min_p": 0.05,
#     "tfs": 0.95,
#     "frequency_penalty": 0.05,
#     "presence_penalty": 1.25,
#     "repetition_penalty": 1.15,
#     "mirostat_mode": 0,
#     "mirostat_tau": 1.5,
#     "mirostat_eta": 0.1,
#     "temperature_last": True,
#     "smoothing_factor": 0.55
# })

# airole = {
#     "Name":Name,
#     "Ai_name":ai_name,
#     "Ai_speaker":"zh-cn_qingling",
#     "Ai_speaker_en":"en_female_04",
#     "is_Uncensored":is_Uncensored,
#     "Prologue":prologue,
#     "Char_Persona":char_persona,
#     "User_Persona":user_persona,
#     "json_Chapters":chapters,
#     "Char_looks":char_looks,
#     "json_Char_outfit":char_outfit,
#     "Char_avatar":char_avatar,
#     "Default_bg":default_bg,
#     "Firstwords":firstwords,
#     "is_Gen_DynaPic":is_Gen_DynaPic,
#     "Prompt_to_load":prompt_to_load,
#     "Match_words_cata":match_words_cata,
#     "json_Completions_data":completions_data,
#     "Creator_ID":1,
# }


# result = database.edit_airole(airole)
# if result is True:
#     print("success")
# else:
#     print(result)

# result = database.get_airole(Name=Name)
# for key, value in result.items():
#     logging.info(f"{key}: {value}")

# result = database.list_data_airole(["Name","Ai_name","Ai_speaker","Ai_speaker_en","is_Uncensored"])
# rolelist = {}
# for row in result:
#     roleName = row.pop('Name')
#     rolelist[roleName] = row

# result = database.del_airole(Name=Name)
# if os.path.exists(roles_path):
#     rmtree(roles_path)
# else:
#     print(f"{roles_path} doesnt exist")
