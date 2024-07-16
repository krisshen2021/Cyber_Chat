from fastapimode.sys_path import create_syspath, project_root

create_syspath()
from modules.global_sets_async import (
    getGlobalConfig,
    database,
    conn_ws_mgr,
    logging,
    config_data,
    prompt_params,
)
import uvicorn, uuid, json, markdown, os
from datetime import datetime
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, Depends
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from modules.user_validation import Validation
from modules.PydanticModels import EnterRoom, as_form
from fastapimode.room_uncensor_websocket import chatRoom_unsensor
from fastapimode.tabby_fastapi_websocket import tabby_fastapi
from modules.payload_state import sd_payload, completions_data
from modules.AiRoleOperator import AiRoleOperator as ARO
from modules.ANSI_tool import ansiColor

sd_payload = sd_payload.copy()
config_data = config_data.copy()
completions_data = completions_data.copy()
templates_path = os.path.join(project_root, "templates")
static_path = os.path.join(project_root, "static")
templates = Jinja2Templates(directory=templates_path)
database.create_table()


def clear_screen():
    # 针对不同操作系统的清屏命令
    if os.name == "nt":  # Windows
        _ = os.system("cls")
    else:  # Mac and Linux
        _ = os.system("clear")


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


# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     # Startup code
#     print("Starting up...")
#     # Your startup logic here
#     yield
#     # Shutdown code
#     print("Shutting down...")


app = FastAPI(title="cyberchat")
app.mount("/static", StaticFiles(directory=static_path), name="static")


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
    ai_role_list = []
    roleconf = await getGlobalConfig("roleconf")
    roleconf_reversed = dict(reversed(list(roleconf.items())))
    for key, value in roleconf_reversed.items():
        ai_role_list.append({"aiRoleId": key, "Data": value})
    timestamp = generate_timestamp()
    context = {
        "request": request,
        "timestamp": timestamp,
        "ai_role_list": ai_role_list,
        "cookid_server": cookid_server,
    }
    return non_cache_response("role_selector_websocket.html", context)


# Enter room
@app.post("/enter_room")
async def enter_room(
    request: Request,
    form_data: EnterRoom = Depends(as_form(EnterRoom), use_cache=False),
):
    context = form_data.model_dump()
    suggestions = await getGlobalConfig("suggestions_params")
    context["suggestions"] = suggestions
    ai_role_data = database.get_airole(context["ai_role_name"])
    prologue = ai_role_data["Prologue"]
    username = context["username"]
    ainame = context["ainame"]
    prologue = (
        prologue.replace("\n", "<br>")
        .replace(r"{{user}}", f"<em>{username}</em>")
        .replace(r"{{char}}", f"<em>{ainame}</em>")
    )
    context["Prologue"] = prologue
    context["request"] = request
    timestamp = generate_timestamp()
    context["timestamp"] = timestamp
    return non_cache_response("chatroom_websocket.html", context)


async def client_connect(client_info, client_id):
    print("{}".format(ansiColor.color_text(client_id,ansiColor.BG_BRIGHT_BLUE)))
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
            # data_op_result.pop("unique_id", None)
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
            # userdata.pop("unique_id", None)
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
        response = await userCurrentRoom.my_generate.tabby_server.load_model(name=model)
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
    ai_text, voice_text, speaker, speak_tone, avatar_url, dynamic_picture = (
        await userCurrentRoom.server_reply(usermsg)
    )
    user_ai_text = markdownText(ai_text)
    data_to_send = {
        "message": user_ai_text,
        "voice_text": voice_text,
        "avatar": avatar_url,
        "speaker": speaker,
        "speak_tone": speak_tone,
        "ttskey": userCurrentRoom.ttskey,
        "dynamic_picture": dynamic_picture,
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
    ai_text, voice_text, speaker, speak_tone, avatar_url, dynamic_picture = (
        await userCurrentRoom.regen_msg(usermsg)
    )
    user_ai_text = markdownText(ai_text)
    data_to_send = {
        "message": user_ai_text,
        "voice_text": voice_text,
        "avatar": avatar_url,
        "speaker": speaker,
        "speak_tone": speak_tone,
        "ttskey": userCurrentRoom.ttskey,
        "dynamic_picture": dynamic_picture,
    }
    await send_datapackage("Message_data_from_server", data_to_send, client_id)


# Exit room
async def exit_room(client_msg, client_id):
    userCurrentRoom = conn_ws_mgr.get_room(client_id)
    username = userCurrentRoom.username
    data_to_send = {"message": f"{username}, See you later"}
    await send_datapackage("exit_room_success", data_to_send, client_id)


# Xtts audio
async def xtts_audio_generate(client_msg, client_id):
    text = client_msg["data"]["text"]
    speaker_wav = client_msg["data"]["speaker_wav"]
    language = client_msg["data"]["language"]
    voice_uid = client_msg["data"]["voice_uid"]
    url = config_data["openai_api_chat_base"] + "/xtts"
    server_url = config_data["xtts_api_base"]
    audio_data = await tabby_fastapi.xtts_audio(
        url, text, speaker_wav, language, server_url
    )
    data_to_send = {"audio_data": audio_data, "voice_uid": voice_uid}
    if audio_data:
        await send_datapackage("xtts_result", data_to_send, client_id)
    else:
        logging.info("Failed to get audio data")


# preview avatar
async def preview_avatar(client_info, client_id):
    facelooks = client_info["data"]["facelooks"]
    avatar_for = client_info["data"]["avatar_for"]
    if facelooks["hair_color"] != "":
        hair_style = f"({facelooks['hair_color']} {facelooks['hair_style']}:1.13)"
    else:
        hair_style = f"({facelooks['hair_style']}:1.13)"
    ends = ", " if facelooks["beard"] != "" else ""
    facelooks_str = f"(One {facelooks['gender']}:1.15), {facelooks['race']}, {facelooks['age']}, {hair_style}, {facelooks['eye_color']}{ends}{facelooks['beard']}"
    logging.info(facelooks_str)
    prompt_str = (
        prompt_params["prmopt_fixed_prefix"]
        + ", (face portrait:1.12), "
        + facelooks_str
        + ", plain orange-color background, "
        + prompt_params["prmopt_fixed_suffix"]
    )
    sd_payload["negative_prompt"] = prompt_params["nagetive_prompt"]
    sd_payload["hr_negative_prompt"] = prompt_params["nagetive_prompt"]
    sd_payload["hr_prompt"] = prompt_str
    sd_payload["prompt"] = prompt_str
    sd_payload["enable_hr"] = True
    sd_payload["hr_scale"] = 1.25
    sd_payload["steps"] = 20
    sd_payload["width"] = 512
    sd_payload["height"] = 512
    # logging.info(sd_payload)
    avatar_data = await tabby_fastapi.SD_image(payload=sd_payload)
    if avatar_data:
        avatar_data_url = "data:image/png;base64," + avatar_data
        data_to_send = {"avatar_img": avatar_data_url, "avatar_for": avatar_for}
        await send_datapackage("preview_avatar_result", data_to_send, client_id)
    else:
        logging.info("Failed to get avatar image")


# preview createchar
async def preview_createchar(client_info, client_id):
    charprompt = client_info["data"]["prompt"]
    task = client_info["data"]["task"]
    prompt_str = (
        prompt_params["prmopt_fixed_prefix"]
        + ", (body portrait:1.12), "
        + charprompt
        + ", "
        + prompt_params["prmopt_fixed_suffix"]
    )
    logging.info(prompt_str)
    sd_payload["negative_prompt"] = prompt_params["nagetive_prompt"]
    sd_payload["hr_negative_prompt"] = prompt_params["nagetive_prompt"]
    sd_payload["hr_prompt"] = prompt_str
    sd_payload["prompt"] = prompt_str
    sd_payload["enable_hr"] = True
    sd_payload["hr_scale"] = 1.25
    sd_payload["steps"] = 20
    sd_payload["width"] = 768
    sd_payload["height"] = 768
    picture_data = await tabby_fastapi.SD_image(payload=sd_payload)
    if picture_data:
        picture_data_url = "data:image/png;base64," + picture_data
        data_to_send = {"result": picture_data_url, "task": task}
        await send_datapackage("preview_char_result", data_to_send, client_id)
    else:
        logging.info("Failed to get char preview image")


# create chars wizard
async def createchar_wizard(client_info, client_id):
    config_data = await getGlobalConfig("config_data")
    task = client_info["data"]["task"]
    wizardstr = client_info["data"]["wizardstr"]
    result = await getGlobalConfig("prompt_templates")
    wizard_prompt_template = result["Cohere_Rephrase"]
    prompt_params = await getGlobalConfig("prompt_params")

    def char_persona():
        sysinstruct = prompt_params["createchar_wizard_prompt"]["char_persona"]
        userinstruct = f"The given basic information of character are: \n{wizardstr}\n\nThe final output of created character persona will be: "
        return {"sysinstruct": sysinstruct, "userinstruct": userinstruct}

    def char_looks():
        sysinstruct = prompt_params["createchar_wizard_prompt"]["char_looks"]
        userinstruct = f"The given character persona is: \n{wizardstr}\n\nThe final output of created text2img prompt for character looks will be: "
        return {"sysinstruct": sysinstruct, "userinstruct": userinstruct}

    def prologue():
        sysinstruct = prompt_params["createchar_wizard_prompt"]["prologue"]
        userinstruct = f"The given characters' persona are: \n{wizardstr}\n\nThe final output will be: "
        return {"sysinstruct": sysinstruct, "userinstruct": userinstruct}

    def chapters():
        sysinstruct = prompt_params["createchar_wizard_prompt"]["chapters"]
        userinstruct = f"The given prologue of story is: \n{wizardstr}\n\nThe final output(without double quotes) will be: "
        return {"sysinstruct": sysinstruct, "userinstruct": userinstruct}

    def firstwords():
        sysinstruct = prompt_params["createchar_wizard_prompt"]["firstwords"]
        userinstruct = f"The given plot of story and the information of {{{{char}}}}'s speaking tone are: \n{wizardstr}\n\nThe final output(speaking without double quotes)will be: "
        return {"sysinstruct": sysinstruct, "userinstruct": userinstruct}

    def char_outfit():
        sysinstruct = prompt_params["createchar_wizard_prompt"]["char_outfit"]
        userinstruct = f"The given character persona and looks are: \n{wizardstr}\n\nThe final output of created JSON formated strings for character outfit will be: "
        return {"sysinstruct": sysinstruct, "userinstruct": userinstruct}

    def user_persona():
        sysinstruct = prompt_params["createchar_wizard_prompt"]["user_persona"]
        userinstruct = f"The given {{{{char}}}}'s information is: \n{wizardstr}\n\nThe final output will be: "
        return {"sysinstruct": sysinstruct, "userinstruct": userinstruct}

    def chat_bg():
        sysinstruct = prompt_params["createchar_wizard_prompt"]["chat_bg"]
        userinstruct = f"The given plot of story and the guide for generating prompt are: \n{wizardstr}\n\nThe final output of text2img prompt for enviornment background will be: "
        return {"sysinstruct": sysinstruct, "userinstruct": userinstruct}

    def story_intro():
        sysinstruct = prompt_params["createchar_wizard_prompt"]["story_intro"]
        userinstruct = f"The given plot of story and the guideline for generate story intro are: \n{wizardstr}\n\nThe final output will be: "
        return {"sysinstruct": sysinstruct, "userinstruct": userinstruct}

    def default_task():
        return "Invalid task"

    wizardfunc = {
        "char_persona": char_persona,
        "char_looks": char_looks,
        "prologue": prologue,
        "chapters": chapters,
        "firstwords": firstwords,
        "char_outfit": char_outfit,
        "user_persona": user_persona,
        "chat_bg": chat_bg,
        "story_intro": story_intro,
    }

    def switchfunc(task):
        return wizardfunc.get(task, default_task)()

    result = switchfunc(task)
    if result != "Invalid task":
        if config_data["using_remoteapi"] is not True:
            wizard_prompt = wizard_prompt_template.replace(
                r"<|system_prompt|>", result["sysinstruct"]
            ).replace(r"<|user_prompt|>", result["userinstruct"])
        else:
            wizard_prompt = result["sysinstruct"] + "\n" + result["userinstruct"]
        # logging.info(wizard_prompt)
        temperature = 0.8 if task == "prologue" or task == "firstwords" else 0.5
        smoothing_factor = 0.55 if task == "prologue" or task == "firstwords" else 0.1
        max_tokens = 300 if task == "prologue" or task == "char_persona" else 150
        presence_penalty = (
            1.25
            if task == "prologue"
            or task == "firstwords"
            or task == "char_persona"
            or task == "user_persona"
            else 1.05
        )
        repetition_penalty = (
            1.18
            if task == "prologue"
            or task == "firstwords"
            or task == "char_persona"
            or task == "user_persona"
            else 1.05
        )
        completions_data.update(
            {
                "stream": False,
                "stop": ["###"],
                "max_tokens": max_tokens,
                "token_healing": True,
                "temperature": temperature,
                "temperature_last": False,
                "top_k": 50,
                "top_p": 0.8,
                "top_a": 0,
                "typical": 1,
                "min_p": 0.01,
                "tfs": 0.95,
                "frequency_penalty": 0,
                "presence_penalty": presence_penalty,
                "repetition_penalty": repetition_penalty,
                "repetition_decay": 0,
                "mirostat_mode": 0,
                "mirostat_tau": 1.5,
                "mirostat_eta": 0.1,
                "add_bos_token": True,
                "ban_eos_token": False,
                "repetition_range": -1,
                "smoothing_factor": smoothing_factor,
                "prompt": wizard_prompt,
            }
        )
        wizard_result = await tabby_fastapi.pure_inference(payloads=completions_data)
        wizard_result = wizard_result.strip()
        # logging.info(wizard_result)
        data_to_send = {"result": wizard_result, "task": task}
        await send_datapackage("createchar_wizard_result", data_to_send, client_id)
    else:
        logging.info("Invalid task")


# save created character
async def client_save_character(client_info, client_id):
    createchar_data = client_info["data"]["createchar_data"]
    logging.info(createchar_data)
    createchar_data["User_Persona"] = (
        f"Appearance: <|User_Looks|>\n{createchar_data['User_Persona']}"
    )

    createchar_data["json_Chapters"] = json.dumps(
        createchar_data["json_Chapters"], indent=4
    )
    createchar_data["json_Char_outfit"] = json.dumps(
        createchar_data["json_Char_outfit"], indent=4
    )
    createchar_data["json_Completions_data"] = json.dumps(
        createchar_data["json_Completions_data"], indent=4
    )
    createchar_data["json_Story_intro"] = json.dumps(
        createchar_data["json_Story_intro"], indent=4
    )
    result = await ARO.create_role(createchar_data)
    if result[0]:
        msg_to_send = "success"
        logging.info("save character successfuly")
    else:
        msg_to_send = result[1]
    data_to_send = {"result": msg_to_send, "task": "after_char_saved"}
    await send_datapackage("save_character_result", data_to_send, client_id)


# ws event handler
ws_events_dict = {
    "connect to server": client_connect,
    "client_login": client_login,
    "client_signup": client_signup,
    "client_edit_profile": client_edit_profile,
    "initialize_room": initialize_room,
    "restart": restart_room,
    "change_model": change_model,
    "change_instruction": change_instruction,
    "change_SD_Model": change_SD_Model,
    "save_chat_history": save_chat_history,
    "load_chat_history": load_chat_history,
    "send_user_msg": reply_user_query,
    "regen_msg": regen_msg,
    "exit_room": exit_room,
    "xtts_audio_gen": xtts_audio_generate,
    "preview_avatar": preview_avatar,
    "createchar_wizard": createchar_wizard,
    "preview_createchar": preview_createchar,
    "client_save_character": client_save_character,
}


async def execute_function(event_name, *args, **kwargs):
    func = ws_events_dict.get(event_name)
    if func:
        await func(*args, **kwargs)
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
                await execute_function(ws_event_client, client_info, client_id)
        except WebSocketDisconnect:
            print("{}".format(ansiColor.color_text(client_id,ansiColor.BG_BRIGHT_RED)))


if __name__ == "__main__":
    host = config_data["server_address"]
    port = config_data["server_port"]
    try:
        clear_screen()
        ansiColor.color_print("Cyber Chat Ver 1.0 by muffin",ansiColor.BG_BRIGHT_MAGENTA, ansiColor.BOLD)
        uvicorn.run(app, host=host, port=port, access_log=False)   
    except KeyboardInterrupt:
        logging.info("Server has been shut down.")
