from database.sqliteclass import SQLiteDB
from transformers import pipeline
import os, yaml, json, asyncio, aiofiles, base64
from yeelight import Bulb
from pathlib import Path
from modules.ConnectionManager import ConnectionManager
from httpx import Timeout
from modules.FormatedLogger import logger

timeout = Timeout(60.0)
logging = logger
dir_path = Path(__file__).parents[1]
config_path = os.path.join(dir_path, "config", "config.yml")
database_path = os.path.join(dir_path, "database", "cyberchat.db")
prompt_temp_path = os.path.join(dir_path, "config","prompts","prompt_template.yaml")
prompt_param_path = os.path.join(dir_path, "config","prompts","prompts.yaml")
suggestions_path = os.path.join(dir_path, "config", "prompts", "suggestions.yaml")
roles_path = os.path.join(dir_path, "config", "roles_LLM.json")

conn_ws_mgr = ConnectionManager()
database = SQLiteDB(database_path)
chatRoomList = {}
Remove_pending_roomlist = {}
prompt_templates = None
prompt_params = None
suggestions_params = None
config_data = None
roleconf = None
sentiment_pipeline = None
bulb = None


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
        if 'svg' in value:
            value['svg'] = base64.b64encode(value['svg'].encode('utf-8')).decode('utf-8')
    
async def load_roles():
    result = database.list_data_airole(
        ["Name", "Ai_name", "Ai_speaker", "Ai_speaker_en", "is_Uncensored", "Creator_ID", "json_Story_intro", "Match_words_cata"]
    )
    rolelist = {}
    for row in result:
        roleName = row.pop("Name")
        rolelist[roleName] = {}
        rolelist[roleName]['if_uncensored'] = "Yes" if row["is_Uncensored"] == 1 else "No"
        rolelist[roleName]['ai_name'] = row['Ai_name']
        rolelist[roleName]['ai_speaker'] = row['Ai_speaker']
        rolelist[roleName]['ai_speaker_en'] = row['Ai_speaker_en']
        rolelist[roleName]['Creator_ID'] = row['Creator_ID']
        rolelist[roleName]['json_Story_intro'] = row['json_Story_intro']
        rolelist[roleName]['Match_words_cata'] = row['Match_words_cata']
    global roleconf
    roleconf = rolelist.copy()


async def gen_sentimodel(model_path):
    global sentiment_pipeline
    sentiment_pipeline = pipeline(
        "sentiment-analysis", model=model_path, tokenizer=model_path
    )


async def conn_bulb(yeelight_url):
    global bulb
    try:
        bulb = Bulb(yeelight_url, auto_on=True, effect="smooth", duration=2000)
        bulb.toggle()
        logging.info(f"Bulb Power: {bulb.get_properties()['power']}") 
    except Exception as e:
        # logging.info(f"Error during turn on Bulb: {e}")

        class bulb_null:
            def __init__(self) -> None:
                pass

            def set_hsv(self, r, g, b) -> None:
                pass

        bulb = bulb_null()

async def multitask():
    roles = asyncio.create_task(load_roles())
    func_prompt_temp = asyncio.create_task(load_prompts_template())
    func_prompt_param = asyncio.create_task(load_prompts_params())
    func_suggestions = asyncio.create_task(load_suggestions())
    sentiment = asyncio.create_task(gen_sentimodel(config_data["sentimodelpath"]))
    bulbstatus = asyncio.create_task(conn_bulb(config_data["yeelight_url"]))
    await asyncio.gather(roles,func_prompt_temp,func_prompt_param, func_suggestions, sentiment, bulbstatus)
    
async def initialize():
    await load_config()
    await multitask()
    
async def getGlobalConfig(data:str):
    """
    get global config for app start,
    type of data:
    'config_data','roleconf','sentiment_pipeline','bulb','prompt_templates','prompt_params'
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
    if data == "sentiment_pipeline":
        return sentiment_pipeline
    if data == "bulb":
        return bulb

asyncio.run(initialize())