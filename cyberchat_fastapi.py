from fastapimode.sys_path import create_syspath, project_root

create_syspath()
from modules.global_sets_async import (
    getGlobalConfig,
    database,
    conn_ws_mgr,
    logging,
    roleconf,
    config_data
)
import uvicorn, uuid, json, markdown, os
from datetime import datetime
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, Depends
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from modules.user_validation import Validation
from modules.PydanticModels import EnterRoom, as_form
from fastapimode.room_uncensor_websocket import chatRoom_unsensor
from fastapimode.tabby_fastapi_websocket import tabby_fastapi

config_data = config_data
roleconf = roleconf
templates_path = os.path.join(project_root, "templates")
static_path = os.path.join(project_root, "static")
templates = Jinja2Templates(directory=templates_path)
database.create_table()


def generate_timestamp():
    # 获取当前时间的时间戳，以秒为单位
    timestamp = datetime.now().timestamp()
    return int(timestamp)


async def send_status(messages, client_id, ws_server="status_from_server"):
    send_data = {"wsevent_server": ws_server, "data": {"message": messages}}
    await conn_ws_mgr.send_personal_message(client_id, send_data)
    # logging.info(f"system status: {messages}")


async def send_datapackage(ws_server, datapackage, client_id):
    send_data = {"wsevent_server": ws_server, "data": datapackage}
    await conn_ws_mgr.send_personal_message(client_id, send_data)


def markdownText(text):
    Mtext = markdown.markdown(
        text,
        extensions=["pymdownx.superfences", "pymdownx.highlight", "pymdownx.magiclink"],
    )
    return Mtext


app = FastAPI(title="cyberchat")
app.mount("/static", StaticFiles(directory=static_path), name="static")


@app.on_event("startup")
async def startup():
    # await initialize()
    # global roleconf, config_data
    # roleconf = getGlobalConfig("roleconf")
    # config_data = getGlobalConfig("config_data")
    pass


def non_cache_response(template_name: str, context: dict) -> Response:
    headers = {
        "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
        "Pragma": "no-cache",
        "Expires": "0",
    }
    return templates.TemplateResponse(template_name, context=context, headers=headers)


# Role selection page
@app.get("/")
async def initpage(request: Request):
    cookid_server = uuid.uuid1()
    ainame = []
    ai_is_uncensored = []
    roleconf = await getGlobalConfig("roleconf")
    for key, value in roleconf.items():
        ainame.append(value.get("ai_name"))
        ai_is_uncensored.append(value.get("if_uncensored"))
    roleitems = list(roleconf.keys())
    timestamp = generate_timestamp()
    context = {
        "request": request,
        "timestamp": timestamp,
        "roleslist": roleitems,
        "ainamelist": ainame,
        "censoredlist": ai_is_uncensored,
        "cookid_server": cookid_server,
    }
    return non_cache_response("role_selector_websocket.html", context)


# Enter room
@app.post("/enter_room")
async def enter_room(
    request: Request,
    form_data: EnterRoom = Depends(as_form(EnterRoom), use_cache=False),
):
    facelooks = json.loads(form_data.facelooks)
    space = " " if facelooks["hair_color"] != "" else ""
    ends = ", " if facelooks["beard"] != "" else ""
    facelooks_str = f"One {facelooks['gender']}, {facelooks['race']}, {facelooks['age']}, {facelooks['hair_color']}{space}{facelooks['hair_style']}, {facelooks['eye_color']}{ends}{facelooks['beard']}"
    context = form_data.dict()
    context["facelooks"] = facelooks_str
    context["request"] = request
    timestamp = generate_timestamp()
    context["timestamp"] = timestamp
    return non_cache_response("chatroom_websocket.html", context)


async def client_connect(client_info, client_id):
    logging.info(f"<< Client >> {client_info['data']['from']} connected")
    send_data = {
        "name": "connect_status",
        "msg": {"status": "Success", "data": "Welcome to CyberChat Server"},
    }
    await send_status(send_data, client_id, ws_server="after_connect")


# Login
async def client_login(client_info, client_id):
    send_data = {}
    username = client_info["data"]["username"]
    password = client_info["data"]["password"]

    vali_result = Validation.vali_data(client_info["data"])
    if vali_result["validated"]:
        data_op_result = database.get_user(username, password)
        if isinstance(data_op_result, str):
            send_data = {
                "name": "login_authorization",
                "msg": {"status": "Fail", "data": data_op_result},
            }
        else:
            data_op_result.pop("unique_id", None)
            data_op_result.pop("password", None)
            data_op_result["facelooks"] = json.loads(data_op_result["facelooks"])
            send_data = {
                "name": "login_authorization",
                "msg": {"status": "Success", "data": data_op_result},
            }
    else:
        error = vali_result["data"]
        send_data = {
            "name": "login_validation",
            "msg": {"status": "Fail", "data": error},
        }
    await send_status(send_data, client_id)


# SignUp
async def client_signup(client_info, client_id):
    send_data = {}
    if client_info["data"]["nickname"] == "":
        client_info["data"]["nickname"] = client_info["data"]["username"]

    username = client_info["data"]["username"]
    nickname = client_info["data"]["nickname"]
    email = client_info["data"]["email"]
    password = client_info["data"]["password"]
    gender = client_info["data"]["gender"]
    facelooks = client_info["data"]["facelooks"]
    facelooks = json.dumps(facelooks)

    vali_result = Validation.vali_data(client_info["data"])
    if vali_result["validated"]:
        avatar = "/static/images/avatar/profile_" + gender + ".png"
        data_op_result = database.create_new_user(
            username=username,
            nickname=nickname,
            gender=gender,
            password=password,
            email=email,
            credits=1000,
            avatar=avatar,
            facelooks=facelooks,
        )
        if isinstance(data_op_result, str):
            logging.info(data_op_result)
            send_data = {
                "name": "signup_authorization",
                "msg": {"status": "Fail", "data": data_op_result},
            }
        else:
            userdata = database.get_user(username, password)
            userdata.pop("unique_id", None)
            userdata.pop("password", None)
            userdata["facelooks"] = json.loads(userdata["facelooks"])
            send_data = {
                "name": "signup_authorization",
                "msg": {"status": "Success", "data": userdata},
            }
    else:
        error = vali_result["data"]
        send_data = {
            "name": "signup_validation",
            "msg": {"status": "Fail", "data": error},
        }

    await send_status(send_data, client_id)


# Edit profile
async def client_edit_profile(client_info, client_id):
    send_data = {}
    if client_info["data"]["nickname"] == "":
        client_info["data"]["nickname"] = client_info["data"]["username"]
    username = client_info["data"]["username"]
    nickname = client_info["data"]["nickname"]
    email = client_info["data"]["email"]
    gender = client_info["data"]["gender"]
    facelooks = client_info["data"]["facelooks"]
    facelooks = json.dumps(facelooks)

    vali_result = Validation.vali_data(client_info["data"])
    if vali_result["validated"]:
        avatar = "/static/images/avatar/profile_" + gender + ".png"
        data_op_result = database.edit_user(
            username=username,
            nickname=nickname,
            gender=gender,
            email=email,
            avatar=avatar,
            facelooks=facelooks,
        )
        if isinstance(data_op_result, str):
            logging.info(data_op_result)
            send_data = {
                "name": "edit_authorization",
                "msg": {"status": "Fail", "data": data_op_result},
            }

        else:
            userdata = database.get_user(username=username, needpassword=False)
            userdata.pop("unique_id", None)
            userdata.pop("password", None)
            userdata["facelooks"] = json.loads(userdata["facelooks"])
            send_data = {
                "name": "edit_authorization",
                "msg": {"status": "Success", "data": userdata},
            }
    else:
        error = vali_result["data"]
        send_data = {
            "name": "edit_validation",
            "msg": {"status": "Fail", "data": error},
        }
    await send_status(send_data, client_id)


# Initialize room
async def initialize_room(client_msg, client_id):
    username = client_msg["data"]["username"]
    user_sys_name = client_msg["data"]["user_sys_name"]
    usergender = client_msg["data"]["usergender"]
    user_facelooks = client_msg["data"]["user_facelooks"]
    ai_role_name = client_msg["data"]["ai_role_name"]
    transswitcher = client_msg["data"]["istranslated"]
    windowRatio = round(float(client_msg["data"]["windowRatio"]), 2)
    userCurrentRoom = conn_ws_mgr.get_room(client_id)
    if userCurrentRoom:
        userCurrentRoom.conversation_id = client_id
        userCurrentRoom.ai_role_name = ai_role_name
        userCurrentRoom.username = username
        userCurrentRoom.user_sys_name = user_sys_name
        userCurrentRoom.usergender = usergender
        userCurrentRoom.user_facelooks = user_facelooks
        userCurrentRoom.state["translate"] = True if transswitcher else False
        userCurrentRoom.windowRatio = windowRatio
    else:
        conn_ws_mgr.set_room(
            client_id,
            chatRoom_unsensor(
                user_sys_name=user_sys_name,
                ai_role_name=ai_role_name,
                username=username,
                usergender=usergender,
                user_facelooks=user_facelooks,
                conversation_id=client_id,
                windowRatio=windowRatio,
                send_msg_websocket=send_status,
            ),
        )
        logging.info(f"Cyber Chat Room created for: {ai_role_name} & {username}")
        userCurrentRoom = conn_ws_mgr.get_room(client_id)
        userCurrentRoom.state["translate"] = True if transswitcher else False

    if not userCurrentRoom.initialization_start:
        await userCurrentRoom.initialize()
        user_ai_text = markdownText(userCurrentRoom.G_ai_text)
        data_to_send = {
            "message": user_ai_text,
            "voice_text": userCurrentRoom.G_voice_text,
            "avatar": userCurrentRoom.G_avatar_url,
            "user_looks": userCurrentRoom.G_userlooks_url,
            "speaker": userCurrentRoom.ai_speakers,
            "speak_tone": userCurrentRoom.speaker_tone,
            "ttskey": userCurrentRoom.ttskey,
            "dynamic_picture": False,
            "bgImg": userCurrentRoom.bkImg,
            "user_bkImg": userCurrentRoom.user_bkImg,
            "model_list": userCurrentRoom.model_list,
            "instruct_list": userCurrentRoom.instr_temp_list,
            "SD_model_list": userCurrentRoom.SD_model_list,
            "iscreatedynimage": userCurrentRoom.iscreatedynimage,
        }
        await send_datapackage("Message_data_from_server", data_to_send, client_id)


# Restart Room
async def restart_room(client_msg, client_id):
    userCurrentRoom = conn_ws_mgr.get_room(client_id)
    windowRatio = client_msg["data"]["windowRatio"]
    userCurrentRoom.conversation_id = client_id
    transswitcher = client_msg["data"]["istranslated"]
    userCurrentRoom.state["translate"] = True if transswitcher else False
    userCurrentRoom.windowRatio = round(float(windowRatio), 2)
    await userCurrentRoom.serialize_data()
    user_ai_text = markdownText(userCurrentRoom.G_ai_text)
    logging.info("chat has been reset")
    data_to_send = {
        "message": user_ai_text,
        "voice_text": userCurrentRoom.G_voice_text,
        "avatar": userCurrentRoom.G_avatar_url,
        "user_looks": userCurrentRoom.G_userlooks_url,
        "speaker": userCurrentRoom.ai_speakers,
        "speak_tone": userCurrentRoom.speaker_tone,
        "ttskey": userCurrentRoom.ttskey,
        "dynamic_picture": False,
        "bgImg": userCurrentRoom.bkImg,
        "user_bkImg": userCurrentRoom.user_bkImg,
        "model_list": userCurrentRoom.model_list,
        "instruct_list": userCurrentRoom.instr_temp_list,
        "SD_model_list": userCurrentRoom.SD_model_list,
        "iscreatedynimage": userCurrentRoom.iscreatedynimage,
    }
    await send_datapackage("Message_data_from_server", data_to_send, client_id)
    await send_status({"name": "initialization", "msg": "DONE"}, client_id)


# Change Model
async def change_model(client_msg, client_id):
    userCurrentRoom = conn_ws_mgr.get_room(client_id)
    model = client_msg["data"]["model"]
    userCurrentRoom.conversation_id = client_id
    unloadresp = await userCurrentRoom.my_generate.tabby_server.unload_model()
    if unloadresp:
        response = await userCurrentRoom.my_generate.tabby_server.load_model(
            name=model
        )
        if response == "Success":
            await send_status({"name": "initialization", "msg": "DONE"}, client_id)
        data_to_send = {"message": response}
        await send_datapackage("model_change_result", data_to_send, client_id)


# Change Instruction
async def change_instruction(client_msg, client_id):
    userCurrentRoom = conn_ws_mgr.get_room(client_id)
    instruction = client_msg["data"]["instruction"]
    userCurrentRoom.conversation_id = client_id
    userCurrentRoom.state["prompt_template"] = instruction
    data_to_send = {"message": "Success"}
    await send_datapackage("instruction_change_result", data_to_send, client_id)


# Change SD Model
async def change_SD_Model(client_msg, client_id):
    userCurrentRoom = conn_ws_mgr.get_room(client_id)
    SD_Model = client_msg["data"]["SD_Model"]
    userCurrentRoom.conversation_id = client_id
    userCurrentRoom.my_generate.image_payload["override_settings"][
        "sd_model_checkpoint"
    ] = SD_Model
    data_to_send = {"message": "Success"}
    await send_datapackage("SD_Model_change_result", data_to_send, client_id)


# Save chat history
async def save_chat_history(client_msg, client_id):
    userCurrentRoom = conn_ws_mgr.get_room(client_id)
    userCurrentRoom.conversation_id = client_id
    result = userCurrentRoom.chat_history_op("save")
    if result:
        await send_status(
            {
                "name": "chat_history_op",
                "msg": {"operation": "save", "result": "Success"},
            },
            client_id,
        )
    else:
        await send_status(
            {"name": "chat_history_op", "msg": {"operation": "save", "result": "Fail"}},
            client_id,
        )


# Load chat history
async def load_chat_history(client_msg, client_id):
    userCurrentRoom = conn_ws_mgr.get_room(client_id)
    userCurrentRoom.conversation_id = client_id
    result = userCurrentRoom.chat_history_op("load")
    if result:
        await send_status(
            {"name": "chat_history_op", "msg": {"operation": "load", "result": result}},
            client_id,
        )
    else:
        await send_status(
            {"name": "chat_history_op", "msg": {"operation": "load", "result": "Fail"}},
            client_id,
        )


# LLM inference message
async def reply_user_query(client_msg, client_id):
    userCurrentRoom = conn_ws_mgr.get_room(client_id)
    usermsg = client_msg["data"]["message"]
    transswitcher = client_msg["data"]["istranslated"]
    windowRatio = client_msg["data"]["windowRatio"]
    iscreatedynimage = client_msg["data"]["iscreatedynimage"]
    userCurrentRoom.conversation_id = client_id
    userCurrentRoom.state["translate"] = True if transswitcher else False
    userCurrentRoom.windowRatio = round(float(windowRatio), 2)
    userCurrentRoom.iscreatedynimage = iscreatedynimage
    ai_text,voice_text,speaker,speak_tone,avatar_url,dynamic_picture = await userCurrentRoom.server_reply(usermsg)
    user_ai_text = markdownText(ai_text)
    data_to_send = {
        "message": user_ai_text,
        "voice_text": voice_text,
        "avatar": avatar_url,
        "speaker": speaker,
        "speak_tone": speak_tone,
        "ttskey": userCurrentRoom.ttskey,
        "dynamic_picture": dynamic_picture
    }
    await send_datapackage("Message_data_from_server", data_to_send, client_id)



# Regen message
async def regen_msg(client_msg, client_id):
    userCurrentRoom = conn_ws_mgr.get_room(client_id)
    usermsg = client_msg["data"]["message"]
    transswitcher = client_msg["data"]["istranslated"]
    windowRatio = client_msg["data"]["windowRatio"]
    iscreatedynimage = client_msg["data"]["iscreatedynimage"]
    userCurrentRoom.conversation_id = client_id
    userCurrentRoom.state["translate"] = True if transswitcher else False
    userCurrentRoom.windowRatio = round(float(windowRatio), 2)
    userCurrentRoom.iscreatedynimage = iscreatedynimage
    ai_text,voice_text,speaker,speak_tone,avatar_url,dynamic_picture = await userCurrentRoom.regen_msg(usermsg)
    user_ai_text = markdownText(ai_text)
    data_to_send = {
        "message": user_ai_text,
        "voice_text": voice_text,
        "avatar": avatar_url,
        "speaker": speaker,
        "speak_tone": speak_tone,
        "ttskey": userCurrentRoom.ttskey,
        "dynamic_picture": dynamic_picture
    }
    await send_datapackage("Message_data_from_server", data_to_send, client_id)

# Exit room
async def exit_room(client_msg,client_id):
    userCurrentRoom = conn_ws_mgr.get_room(client_id)
    username = userCurrentRoom.username
    data_to_send = {"message": f"{username}, See you later"}
    await send_datapackage("exit_room_success", data_to_send, client_id)

async def xtts_audio_generate(client_msg, client_id):
    text = client_msg["data"]["text"]
    speaker_wav = client_msg["data"]["speaker_wav"]
    language = client_msg["data"]["language"]
    voice_uid = client_msg["data"]["voice_uid"]
    url = config_data["openai_api_chat_base"] + "/xtts"
    server_url = config_data["xtts_api_base"]
    audio_data = await tabby_fastapi.xtts_audio(url,text,speaker_wav,language,server_url)
    data_to_send = {"audio_data": audio_data, "voice_uid": voice_uid}
    if audio_data:
        await send_datapackage("xtts_result", data_to_send, client_id)
    else:
        logging.info("Failed to get audio data")

ws_events_dict = {
    "connect to server": client_connect,
    "client_login":client_login,
    "client_signup":client_signup,
    "client_edit_profile":client_edit_profile,
    "initialize_room":initialize_room,
    "restart":restart_room,
    "change_model":change_model,
    "change_instruction":change_instruction,
    "change_SD_Model":change_SD_Model,
    "save_chat_history":save_chat_history,
    "load_chat_history":load_chat_history,
    "send_user_msg":reply_user_query,
    "regen_msg":regen_msg,
    "exit_room":exit_room,
    "xtts_audio_gen": xtts_audio_generate
}
async def execute_function(event_name, *args,**kwargs ):
    func = ws_events_dict.get(event_name)
    if func:
        await func(*args,**kwargs)
    else:
        logging.info("No matched function")
        
# Websocket connection process
@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    async with conn_ws_mgr.connect(client_id, websocket):
        try:
            while True:
                client_info = await conn_ws_mgr.getdata(client_id)
                ws_event_client = client_info["wsevent_client"]
                await execute_function(ws_event_client,client_info,client_id)
        except WebSocketDisconnect:
            logging.info(f"<< Client >> {client_id} disconnected")

if __name__ == "__main__":
    host = "127.0.0.1"
    port = 5500
    uvicorn.run(app, host=host, port=port, access_log=False)
