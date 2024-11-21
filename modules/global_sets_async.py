from database.sqliteclass import SQLiteDB
from memory.qdrant_memory import Memory as qdrant_memory_class
from qdrant_client import models as qdrant_models
import os, yaml, asyncio, aiofiles, base64, io, json
from dotenv import load_dotenv
from PIL import Image
from openai import AsyncOpenAI

# from yeelight import Bulb
from pathlib import Path
from modules.ConnectionManager import ConnectionManager
from httpx import Timeout
from modules.colorlogger import logger

# from modules.sentiment import SentiAna


timeout = Timeout(60.0)
# sentiment_anlyzer = SentiAna
dir_path = Path(__file__).parents[1]
env_path = os.path.join(dir_path, "server", ".env")
load_dotenv(env_path)
config_path = os.path.join(dir_path, "config", "config.yml")
database_path = os.path.join(dir_path, "database", "cyberchat.db")
prompt_temp_path = os.path.join(dir_path, "config", "prompts", "prompt_template.yaml")
prompt_param_path = os.path.join(dir_path, "config", "prompts", "prompts.yaml")
suggestions_path = os.path.join(dir_path, "config", "prompts", "suggestions.yaml")
language_path = os.path.join(dir_path, "config", "language", "lang.json")
api_key_for_translate = None
base_url_for_translate = None
model_for_translate = None
api_key_for_qdrant = os.getenv("openrouter_api_key", default="None")
languageClient = None
conn_ws_mgr = ConnectionManager()
database = SQLiteDB(database_path)
# cyberchat_memory = None
chatRoomList = {}
Remove_pending_roomlist = {}
prompt_templates = None
prompt_params = None
suggestions_params = None
config_data = None
roleconf = None
language_data = None

# bulb = None


async def init_memory():
    cyberchat_memory = qdrant_memory_class(
        qdrant_url=config_data["qdrant_server_url"],
        embedding_model=config_data["qdrant_embedding_model"],
        collection_name=config_data["qdrant_collection_name"],
        oai_api_key=api_key_for_qdrant,
        oai_base_url=config_data["qdrant_oai_base_url"],
        oai_model=config_data["qdrant_oai_model"],
    )
    await cyberchat_memory.upsert_collection(
        vectors={"memory_vector": (384, qdrant_models.Distance.COSINE)}
    )
    return cyberchat_memory


async def load_config():
    async with aiofiles.open(config_path, mode="r") as f:
        contents = await f.read()
    global config_data
    config_data = yaml.safe_load(contents)


async def load_prompts_template():
    async with aiofiles.open(prompt_temp_path, mode="r") as f:
        contents = await f.read()
    global prompt_templates
    prompt_templates = yaml.safe_load(contents)


async def load_prompts_params():
    async with aiofiles.open(prompt_param_path, mode="r") as f:
        contents = await f.read()
    global prompt_params
    prompt_params = yaml.safe_load(contents)


async def load_suggestions():
    async with aiofiles.open(suggestions_path, mode="r") as f:
        contents = await f.read()
    global suggestions_params
    suggestions_params = yaml.safe_load(contents)
    for key, value in suggestions_params.items():
        if "svg" in value:
            value["svg"] = base64.b64encode(value["svg"].encode("utf-8")).decode(
                "utf-8"
            )


async def load_roles():
    result = database.list_data_airole(
        [
            "Name",
            "Ai_name",
            "Ai_speaker",
            "Ai_speaker_en",
            "is_Uncensored",
            "Creator_ID",
            "json_Story_intro",
            "Match_words_cata",
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
    global roleconf
    roleconf = rolelist.copy()


async def load_language():
    async with aiofiles.open(language_path, mode="r") as f:
        contents = await f.read()
    global language_data
    language_data = json.loads(contents)


async def load_language_client():
    global languageClient
    global api_key_for_translate
    global base_url_for_translate
    global model_for_translate
    api_key_for_translate = os.getenv(config_data["translate_api_key"], default="None")
    base_url_for_translate = config_data["translate_base_url"]
    model_for_translate = config_data["translate_model"]
    languageClient = AsyncOpenAI(
        api_key=api_key_for_translate, base_url=base_url_for_translate, timeout=120
    )


# async def conn_bulb(yeelight_url):
#     global bulb
#     try:
#         bulb = Bulb(yeelight_url, auto_on=True, effect="smooth", duration=2000)
#         bulb.toggle()
#         logger.info(f"Bulb Power: {bulb.get_properties()['power']}")
#     except Exception as e:
#         logger.info(f"Error during turn on Bulb: {e}")

#         class bulb_null:
#             def __init__(self) -> None:
#                 pass

#             def set_hsv(self, r, g, b) -> None:
#                 pass

#         bulb = bulb_null()


async def multitask():
    roles = asyncio.create_task(load_roles())
    func_prompt_temp = asyncio.create_task(load_prompts_template())
    func_prompt_param = asyncio.create_task(load_prompts_params())
    func_suggestions = asyncio.create_task(load_suggestions())
    func_language = asyncio.create_task(load_language())
    func_language_client = asyncio.create_task(load_language_client())
    # bulbstatus = asyncio.create_task(conn_bulb(config_data["yeelight_url"]))
    await asyncio.gather(
        roles,
        func_prompt_temp,
        func_prompt_param,
        func_suggestions,
        func_language,
        func_language_client,
    )


async def initialize():
    await load_config()
    await multitask()
    await asyncio.sleep(0.5)


async def getGlobalConfig(data: str):
    """
    get global config for app start,
    type of data:
    'config_data','roleconf','bulb','prompt_templates','prompt_params'
    """
    if data == "config_data":
        await load_config()
        return config_data
    if data == "roleconf":
        await load_roles()
        return roleconf
    if data == "prompt_templates":
        await load_prompts_template()
        return prompt_templates
    if data == "prompt_params":
        await load_prompts_params()
        return prompt_params
    if data == "suggestions_params":
        await load_suggestions()
        return suggestions_params
    if data == "language_data":
        await load_language()
        return language_data
    # if data == "bulb":
    #     return bulb


async def convert_to_webpbase64(png_base64, quality=75):
    png_image = Image.open(io.BytesIO(base64.b64decode(png_base64)))
    webp_bytes_io = io.BytesIO()
    png_image.save(webp_bytes_io, format="WEBP", quality=quality)
    webp_data = webp_bytes_io.getvalue()
    webp_base64 = base64.b64encode(webp_data).decode("utf-8")
    return webp_base64


asyncio.run(initialize())
