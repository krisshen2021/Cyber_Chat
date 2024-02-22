from sqliteclass import SQLiteDB
from transformers import pipeline
import os,yaml,json

dir_path = os.path.dirname(os.path.realpath(__file__))

config_path = os.path.join(dir_path, 'config', 'config.yml')
with open(config_path, 'r') as file:
    config_data = yaml.safe_load(file)

sentimodelpath = config_data["sentimodelpath"]
sentiment_pipeline = pipeline('sentiment-analysis', model=sentimodelpath, tokenizer=sentimodelpath)

roles_path = os.path.join(dir_path, 'config', 'roles.json')
with open(roles_path, 'r', encoding='utf-8') as f:
    roleconf = json.load(f)

chatRoomList = {} 
Remove_pending_roomlist={}

database = SQLiteDB()
