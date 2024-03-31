from database.sqliteclass import SQLiteDB
from transformers import pipeline
import os,yaml,json,logging
from yeelight import Bulb
from pathlib import Path
from modules.ConnectionManager import ConnectionManager
logging.basicConfig(level=logging.INFO)
dir_path = Path(__file__).parents[1]
# dir_path = os.path.dirname(os.path.realpath(__file__))
# Get Config yaml data
config_path = os.path.join(dir_path, 'config', 'config.yml')
database_path = os.path.join(dir_path, 'database', 'cyberchat.db')
with open(config_path, 'r') as file:
    config_data = yaml.safe_load(file)
# Get sentiment model
sentimodelpath = config_data["sentimodelpath"]
sentiment_pipeline = pipeline('sentiment-analysis', model=sentimodelpath, tokenizer=sentimodelpath)
# Get roles data
roles_path = os.path.join(dir_path, 'config', 'roles.json')
with open(roles_path, 'r', encoding='utf-8') as f:
    roleconf = json.load(f)

chatRoomList = {} 
Remove_pending_roomlist={}

# initiate database
database = SQLiteDB(database_path)

# initiate bulb
try:
    bulb = Bulb(config_data["yeelight_url"], auto_on=True, effect="smooth", duration=1000)
    logging.info(f"Bulb Power: {bulb.get_properties()['power']}")
except Exception as e:
            logging.info(f"Error during turn on Bulb: {e}")
            class bulb_null:
                def __init__(self) -> None:
                    pass
                def set_hsv(self,r,g,b)-> None:
                    pass
            bulb = bulb_null()
# initiate connection manager
conn_ws_mgr = ConnectionManager()




