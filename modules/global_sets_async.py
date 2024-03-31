from database.sqliteclass import SQLiteDB
from transformers import pipeline
import os, yaml, json, asyncio, aiofiles
from yeelight import Bulb
from pathlib import Path
from modules.ConnectionManager import ConnectionManager
from httpx import Timeout
from modules.FormatedLogger import logger
timeout = Timeout(300.0)
logging = logger
dir_path = Path(__file__).parents[1]
config_path = os.path.join(dir_path, "config", "config.yml")
database_path = os.path.join(dir_path, "database", "cyberchat.db")
roles_path = os.path.join(dir_path, "config", "roles_LLM.json")

conn_ws_mgr = ConnectionManager()
database = SQLiteDB(database_path)
chatRoomList = {}
Remove_pending_roomlist = {}
config_data = None
roleconf = None
sentiment_pipeline = None
bulb = None


async def load_config():
    async with aiofiles.open(config_path, mode="r") as f:
        contents = await f.read()
    global config_data
    config_data = yaml.safe_load(contents)


async def load_roles():
    async with aiofiles.open(roles_path, mode="r", encoding="utf-8") as f:
        contents = await f.read()
    global roleconf
    roleconf = json.loads(contents)


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
        logging.info(f"Error during turn on Bulb: {e}")

        class bulb_null:
            def __init__(self) -> None:
                pass

            def set_hsv(self, r, g, b) -> None:
                pass

        bulb = bulb_null()

async def multitask():
    roles = asyncio.create_task(load_roles())
    sentiment = asyncio.create_task(gen_sentimodel(config_data["sentimodelpath"]))
    bulbstatus = asyncio.create_task(conn_bulb(config_data["yeelight_url"]))
    await asyncio.gather(roles,sentiment,bulbstatus)
    
async def initialize():
    await load_config()
    await multitask()
    
def getGlobalConfig(data:str):
    """
    get global config for app start,
    type of data:
    'config_data','roleconf','sentiment_pipeline','bulb'
    """
    if data == "config_data":
        return config_data
    if data == "roleconf":
        return roleconf
    if data == "sentiment_pipeline":
        return sentiment_pipeline
    if data == "bulb":
        return bulb

asyncio.run(initialize())