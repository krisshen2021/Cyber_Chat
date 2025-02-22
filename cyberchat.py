from fastapimode.sys_path import create_syspath, project_root

create_syspath()
from modules.global_sets_async import (
    getGlobalConfig,
    convert_to_webpbase64,
    database,
    conn_ws_mgr,
    logger,
    config_data,
    prompt_params,
    language_data,
    languageClient,
    model_for_translate,
)
import uvicorn, uuid, json, markdown, os, base64, httpx, asyncio, json5, time
from datetime import datetime
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, Depends
from fastapi.responses import Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from modules.user_validation import Validation
from modules.PydanticModels import EnterRoom, as_form
from fastapimode.room_uncensor_websocket import ChatRoom_Uncensored
from fastapimode.tabby_fastapi_websocket import tabby_fastapi
from modules.payload_state import sd_payload, completions_data
from modules.AiRoleOperator import AiRoleOperator as ARO
from modules.ANSI_tool import ansiColor
from typing import Optional
from google.oauth2 import id_token
from google.auth.transport import requests

sd_payload = sd_payload.copy()
config_data = config_data.copy()
completions_data = completions_data.copy()
templates_path = os.path.join(project_root, "templates")
static_path = os.path.join(project_root, "static")
templates = Jinja2Templates(directory=templates_path)
database.create_table()
siteLanguageData = language_data.copy()
localeLanguage = "English"


def clear_screen():
    if os.name == "nt":  # Windows
        _ = os.system("cls")
    else:  # Mac and Linux
        _ = os.system("clear")


def generate_timestamp():
    timestamp = datetime.now().timestamp()
    return int(timestamp)


async def send_status(messages, client_id, ws_server="status_from_server"):
    send_data = {"wsevent_server": ws_server, "data": {"message": messages}}
    await conn_ws_mgr.send_personal_message(client_id, send_data)
    # logger.info(f"system status: {messages}")


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


def non_cache_response(template_name: str, context: dict) -> Response:
    headers = {
        "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
        "Pragma": "no-cache",
        "Expires": "0",
    }
    return templates.TemplateResponse(template_name, context=context, headers=headers)


# Develop test page
@app.get("/test")
async def test(request: Request):
    context = {"request": request}
    return non_cache_response("develop_test.html", context)


# Admin backend
@app.get("/admin")
async def admin(request: Request):
    is_logged_in = False  # 或者从会话中获取
    ai_role_list = []
    roleconf = await getGlobalConfig("roleconf")
    roleconf_reversed = dict(reversed(list(roleconf.items())))
    for key, value in roleconf_reversed.items():
        ai_role_list.append({"aiRoleId": key, "Data": value})
    return templates.TemplateResponse(
        "admin.html",
        {
            "request": request,
            "is_logged_in": is_logged_in,
            "ai_role_list": ai_role_list,
        },
    )


@app.get("/admin/{Name}")
async def get_role_details(request: Request, Name: str):
    role_details = database.get_airole(Name)
    if role_details:
        role_details.pop("UNIQUE_ID")
        role_details.pop("Name")
        role_details.pop("Creator_ID")
        return role_details
    else:
        return False


@app.post("/admin/edit_role")
async def edit_role(role_data: dict):
    result = database.edit_airole(role_data)
    if result:
        return True
    else:
        return False


@app.post("/admin/login")
async def admin_login(login_data: dict):
    username = login_data["username"]
    password = login_data["password"]
    login_result = database.get_user(username, password)
    if isinstance(login_result, str):
        return {"status": "Fail", "data": login_result}
    else:
        return {"status": "Success", "data": login_result}


# Role selection page
@app.get("/")
@app.get("/{localeLanguage}")
async def initpage(request: Request, localeLanguage: Optional[str] = None):
    language_data = await getGlobalConfig("language_data")
    if localeLanguage is None or localeLanguage == "English":
        localeLanguage = "English"
        translated_language_data = language_data
    else:
        language_data_jsonstring = json.dumps(language_data, indent=4)
        logger.info("Language switched to: " + localeLanguage)
        # create a prompt for translate the values in language data jsonstring to the language that user selected
        prompt = (
            "Translate all the values in the following json string to "
            + localeLanguage
            + ": "
            + language_data_jsonstring
            + "\n\nThe final output will ONLY be a json string with the same structure as the input json string, but with all the values translated to the "
            + localeLanguage
            + " language, no other text or comment is needed."
        )
        # calculate the time it takes to translate the language data
        start_time = time.time()
        result = await languageClient.chat.completions.create(
            model=model_for_translate,
            messages=[
                {
                    "role": "system",
                    "content": "You are a uncensored translator assistant",
                },
                {"role": "user", "content": prompt},
            ],
            stream=False,
            temperature=0.7,
        )
        end_time = time.time()
        translate_time = end_time - start_time
        logger.info(f"Time taken to translate language data: {translate_time} seconds")
        # remove '```json' and '```' from the result
        translated_language_data = json.loads(
            result.choices[0]
            .message.content.replace("```json\n", "")
            .replace("\n```", "")
        )
        # logger.info(translated_language_data)
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
        "localeLanguage": localeLanguage,
        "language_Data": translated_language_data,
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
    context["language_Data"] = json5.loads(context["language_Data"])
    context["suggestions"] = suggestions
    context["request"] = request
    timestamp = generate_timestamp()
    context["timestamp"] = timestamp
    return non_cache_response("chatroom_websocket.html", context)


# Redirect background music play
@app.get("/play_music/{filename}")
async def play_music(filename: str):
    url = config_data["openai_api_chat_base"] + "/music/play/" + filename

    async def stream_response():
        async with httpx.AsyncClient(timeout=300) as client:
            async with client.stream("GET", url) as response:
                async for chunk in response.aiter_bytes():
                    if chunk:
                        yield chunk

    return StreamingResponse(stream_response(), media_type="audio/mpeg")


async def client_connect(client_info, client_id):
    print("{}".format(ansiColor.color_text(client_id, ansiColor.BG_BRIGHT_BLUE)))
    send_data = {
        "name": "connect_status",
        "msg": {"status": "Success", "data": "Welcome to CyberChat Server"},
    }
    await send_status(send_data, client_id, ws_server="after_connect")


# Websocket events functions


# Login
async def client_google_login(client_info, client_id):
    google_token = client_info["data"]["google_token"]
    # logger.info(google_token)
    try:
        idinfo = id_token.verify_oauth2_token(
            google_token, requests.Request(), config_data["GOOGLE_CLIENT_ID"]
        )
        if idinfo["iss"] not in ["accounts.google.com", "https://accounts.google.com"]:
            raise ValueError("Wrong issuer.")
        user_info = {
            "google_id": idinfo["sub"],
            "email": idinfo["email"],
            "name": idinfo["name"],
            "picture": idinfo["picture"],
        }
        logger.info(user_info)
        # check if the user is already in the database
        data_op_result = database.get_user(user_info["email"], "", needpassword=False)
        if isinstance(data_op_result, str):
            if data_op_result == "User is not available":
                result = database.create_new_user(
                    username=user_info["email"],
                    nickname=user_info["name"],
                    gender="male",
                    password="",
                    email=user_info["email"],
                    credits=1000,
                    avatar=user_info["picture"],
                    facelooks=json.dumps(
                        {
                            "gender": "male",
                            "race": "European",
                            "age": "Elderly",
                            "hair_color": "Blond",
                            "hair_style": "Buzz cut",
                            "eye_color": "Brown Eyes",
                            "beard": "Big beard",
                        }
                    ),
                )
                if result:
                    data_op_result = database.get_user(
                        user_info["email"], "", needpassword=False
                    )
                    data_op_result.pop("password", None)
                    data_op_result["facelooks"] = json.loads(
                        data_op_result["facelooks"]
                    )
                    send_data = {
                        "name": "login_authorization",
                        "msg": {"status": "Success", "data": data_op_result},
                    }
                else:
                    data_op_result = result
                    send_data = {
                        "name": "login_authorization",
                        "msg": {"status": "Fail", "data": data_op_result},
                    }
            else:
                data_op_result = data_op_result
                send_data = {
                    "name": "login_authorization",
                    "msg": {"status": "Fail", "data": data_op_result},
                }
        else:
            data_op_result.pop("password", None)
            data_op_result["facelooks"] = json.loads(data_op_result["facelooks"])
            send_data = {
                "name": "login_authorization",
                "msg": {"status": "Success", "data": data_op_result},
            }
        await send_status(send_data, client_id)
    except ValueError:
        send_data = {
            "name": "login_authorization",
            "msg": {"status": "Fail", "data": "Invalid token"},
        }
        await send_status(send_data, client_id)


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
            logger.info(data_op_result)
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
            logger.info(data_op_result)
            send_data = {
                "name": "edit_authorization",
                "msg": {"status": "Fail", "data": data_op_result},
            }

        else:
            userdata = database.get_user(username=username, needpassword=False)
            # userdata.pop("unique_id", None)
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
    using_remoteapi = config_data["using_remoteapi"]
    username = client_msg["data"]["username"]
    user_uid = client_msg["data"]["user_sys_name"]
    usergender = client_msg["data"]["usergender"]
    user_facelooks = client_msg["data"]["user_facelooks"]
    char_uid = client_msg["data"]["ai_role_name"]
    ai_is_uncensored = client_msg["data"]["ai_is_uncensored"]
    ai_is_live_char = client_msg["data"]["ai_is_live_char"]
    ai_is_memory_mode = client_msg["data"]["ai_is_memory_mode"]
    language = client_msg["data"]["language"]
    windowRatio = round(float(client_msg["data"]["windowRatio"]), 2)
    userCurrentRoom = conn_ws_mgr.get_room(client_id)
    if userCurrentRoom:
        userCurrentRoom.conversation_id = client_id
        userCurrentRoom.char_uid = char_uid
        userCurrentRoom.username = username
        userCurrentRoom.user_uid = user_uid
        userCurrentRoom.usergender = usergender
        userCurrentRoom.user_facelooks = user_facelooks
        userCurrentRoom.state["ai_is_live_char"] = ai_is_live_char
        userCurrentRoom.state["ai_is_memory_mode"] = ai_is_memory_mode
        userCurrentRoom.windowRatio = windowRatio
        userCurrentRoom.state["language"] = language
    else:
        conn_ws_mgr.set_room(
            client_id,
            ChatRoom_Uncensored(
                user_uid=user_uid,
                char_uid=char_uid,
                username=username,
                usergender=usergender,
                user_facelooks=user_facelooks,
                conversation_id=client_id,
                windowRatio=windowRatio,
                send_msg_websocket=send_status,
            ),
        )
        logger.info(f"Cyber Chat Room created for: {char_uid} & {username}")
        userCurrentRoom = conn_ws_mgr.get_room(client_id)
        userCurrentRoom.state["ai_is_live_char"] = ai_is_live_char
        userCurrentRoom.state["ai_is_memory_mode"] = ai_is_memory_mode
        userCurrentRoom.state["language"] = language
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
            "model": userCurrentRoom.model,
            "instruct_list": userCurrentRoom.instr_temp_list,
            "SD_model_list": userCurrentRoom.SD_model_list,
            "SD_model": userCurrentRoom.image_payload["override_settings"][
                "sd_model_checkpoint"
            ],
            "iscreatedynimage": userCurrentRoom.iscreatedynimage,
            "using_remoteapi": using_remoteapi,
            "bg_music": userCurrentRoom.bg_music,
            "prologue": userCurrentRoom.prologue_intro,
        }
        await send_datapackage("Message_data_from_server", data_to_send, client_id)


# Restart Room
async def restart_room(client_msg, client_id):
    userCurrentRoom = conn_ws_mgr.get_room(client_id)
    using_remoteapi = config_data["using_remoteapi"]
    windowRatio = client_msg["data"]["windowRatio"]
    userCurrentRoom.conversation_id = client_id
    language = client_msg["data"]["language"]
    userCurrentRoom.state["language"] = language
    userCurrentRoom.windowRatio = round(float(windowRatio), 2)
    await userCurrentRoom.serialize_data()
    user_ai_text = markdownText(userCurrentRoom.G_ai_text)
    logger.info("chat has been reset")
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
        "model": userCurrentRoom.model,
        "instruct_list": userCurrentRoom.instr_temp_list,
        "SD_model_list": userCurrentRoom.SD_model_list,
        "SD_model": userCurrentRoom.image_payload["override_settings"][
            "sd_model_checkpoint"
        ],
        "iscreatedynimage": userCurrentRoom.iscreatedynimage,
        "using_remoteapi": using_remoteapi,
        "bg_music": userCurrentRoom.bg_music,
        "prologue": userCurrentRoom.prologue_intro,
    }
    await send_datapackage("Message_data_from_server", data_to_send, client_id)
    await send_status({"name": "initialization", "msg": "DONE"}, client_id)


# Change Model
async def change_model(client_msg, client_id):
    userCurrentRoom = conn_ws_mgr.get_room(client_id)
    model = client_msg["data"]["model"]
    userCurrentRoom.conversation_id = client_id
    userCurrentRoom.model = model
    if not config_data["using_remoteapi"]:
        unloadresp = await userCurrentRoom.my_generate.tabby_server.unload_model()
        if unloadresp:
            response = await userCurrentRoom.my_generate.tabby_server.load_model(
                name=model
            )
            if response == "Success":
                await send_status({"name": "initialization", "msg": "DONE"}, client_id)
                await send_datapackage(
                    "model_change_result", {"message": response}, client_id
                )
    else:
        await send_datapackage("model_change_result", {"message": "Success"}, client_id)


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
    userCurrentRoom.image_payload["override_settings"]["sd_model_checkpoint"] = SD_Model
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
    using_remoteapi = config_data["using_remoteapi"]
    usermsg = client_msg["data"]["message"]
    language = client_msg["data"]["language"]
    windowRatio = client_msg["data"]["windowRatio"]
    iscreatedynimage = client_msg["data"]["iscreatedynimage"]
    userCurrentRoom.conversation_id = client_id
    userCurrentRoom.windowRatio = round(float(windowRatio), 2)
    userCurrentRoom.iscreatedynimage = iscreatedynimage
    userCurrentRoom.state["language"] = language
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
        "using_remoteapi": using_remoteapi,
    }
    await send_datapackage("Message_data_from_server", data_to_send, client_id)


# Regen message
async def regen_msg(client_msg, client_id):
    userCurrentRoom = conn_ws_mgr.get_room(client_id)
    using_remoteapi = config_data["using_remoteapi"]
    usermsg = client_msg["data"]["message"]
    windowRatio = client_msg["data"]["windowRatio"]
    iscreatedynimage = client_msg["data"]["iscreatedynimage"]
    language = client_msg["data"]["language"]
    userCurrentRoom.conversation_id = client_id
    userCurrentRoom.windowRatio = round(float(windowRatio), 2)
    userCurrentRoom.iscreatedynimage = iscreatedynimage
    userCurrentRoom.state["language"] = language
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
        "using_remoteapi": using_remoteapi,
    }
    await send_datapackage("Message_data_from_server", data_to_send, client_id)


# Exit room
async def exit_room(client_msg, client_id):
    userCurrentRoom = conn_ws_mgr.get_room(client_id)
    username = userCurrentRoom.username
    data_to_send = {"message": f"{username}, See you later"}
    await send_datapackage("exit_room_success", data_to_send, client_id)


# Sentence completion
async def sentence_completion(client_msg, client_id):
    userCurrentRoom = conn_ws_mgr.get_room(client_id)
    sentence_result = await userCurrentRoom.sentence_completion(
        client_msg["data"]["message"]
    )
    if sentence_result:
        await send_datapackage(
            "sentence_completion_result",
            {"sentence": sentence_result},
            client_id,
        )
    else:
        await send_datapackage(
            "sentence_completion_result",
            {"sentence": None},
            client_id,
        )


# Xtts audio
async def xtts_audio_generate(client_msg, client_id):
    text = client_msg["data"]["text"]
    speaker_wav = client_msg["data"]["speaker_wav"]
    language = client_msg["data"]["language"]
    voice_uid = client_msg["data"]["voice_uid"]
    remote_api = await getGlobalConfig("config_data")
    if remote_api.get("using_remoteapi"):
        endpoint = "/tts_remote_stream"
        url = config_data["openai_api_chat_base"] + endpoint
        async with httpx.AsyncClient(timeout=300) as client:
            async with client.stream(
                "POST", url, json={"text": text, "speaker": speaker_wav}
            ) as response:
                logger.info("Transfer audio to clients")
                async for chunk in response.aiter_bytes(chunk_size=16384):
                    if chunk:
                        logger.info(f"Streaming chunk: {len(chunk)} bytes")
                        audio_data_base64 = base64.b64encode(chunk).decode("utf-8")
                        data_to_send = {
                            "audio_data": audio_data_base64,
                            "voice_uid": voice_uid,
                            "mode": "stream",
                            "status": "transfer",
                        }
                        await send_datapackage("xtts_result", data_to_send, client_id)
                        # await asyncio.sleep(0.01)
                    else:
                        logger.info("Failed to get audio data")
                logger.info("Transfer ends")
                await send_datapackage(
                    "xtts_result",
                    {"audio_data": None, "voice_uid": voice_uid, "mode": "stream", "status": "end"},
                    client_id,
                )
    else:
        endpoint = "/xtts"
        url = config_data["openai_api_chat_base"] + endpoint
        server_url = config_data["xtts_api_base"]
        audio_data = await tabby_fastapi.xtts_audio(
            url, text, speaker_wav, language, server_url
        )
        data_to_send = {
            "audio_data": audio_data,
            "voice_uid": voice_uid,
            "mode": "normal",
        }
        if audio_data:
            await send_datapackage("xtts_result", data_to_send, client_id)
        else:
            logger.info("Failed to get audio data")


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
    logger.info(facelooks_str)
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
    sd_payload["enable_hr"] = False
    sd_payload["hr_scale"] = 1.25
    sd_payload["steps"] = 15
    sd_payload["width"] = 512
    sd_payload["height"] = 512
    # logger.info(sd_payload)
    avatar_data = await tabby_fastapi.SD_image(
        payload=sd_payload,
        task_flag="preview_avatar",
        send_msg_websocket=send_status,
        client_id=client_id,
    )
    if avatar_data:
        avatar_data = await convert_to_webpbase64(avatar_data)
        avatar_data_url = "data:image/webp;base64," + avatar_data
        data_to_send = {"avatar_img": avatar_data_url, "avatar_for": avatar_for}
        await send_datapackage("preview_avatar_result", data_to_send, client_id)
    else:
        logger.info("Failed to get avatar image")


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
    logger.info(prompt_str)
    sd_payload["negative_prompt"] = prompt_params["nagetive_prompt"]
    sd_payload["hr_negative_prompt"] = prompt_params["nagetive_prompt"]
    sd_payload["hr_prompt"] = prompt_str
    sd_payload["prompt"] = prompt_str
    sd_payload["enable_hr"] = False
    sd_payload["hr_scale"] = 1.25
    sd_payload["steps"] = 15
    sd_payload["width"] = 768
    sd_payload["height"] = 768
    picture_data = await tabby_fastapi.SD_image(payload=sd_payload)
    if picture_data:
        picture_data = await convert_to_webpbase64(picture_data)
        picture_data_url = "data:image/webp;base64," + picture_data
        data_to_send = {"result": picture_data_url, "task": task}
        await send_datapackage("preview_char_result", data_to_send, client_id)
    else:
        logger.info("Failed to get char preview image")


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
            # wizard_prompt = result["sysinstruct"] + "\n" + result["userinstruct"]
            system_prompt = result["sysinstruct"]
            messages = result["userinstruct"]
        # logger.info(wizard_prompt)
        temperature = 0.8 if task == "prologue" or task == "firstwords" else 0.5
        smoothing_factor = 0.55 if task == "prologue" or task == "firstwords" else 0.1
        max_tokens = (
            400
            if task == "prologue" or task == "char_persona" or task == "char_outfit"
            else 150
        )
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
            }
        )
        if config_data["using_remoteapi"]:
            completions_data["system_prompt"] = system_prompt
            completions_data["messages"] = messages
            if "prompt" in completions_data:
                del completions_data["prompt"]
        else:
            completions_data["prompt"] = wizard_prompt
            if "system_prompt" in completions_data:
                del completions_data["system_prompt"]
            if "messages" in completions_data:
                del completions_data["messages"]
        wizard_result = await tabby_fastapi.pure_inference(payloads=completions_data)
        wizard_result = wizard_result.strip()
        # logger.info(wizard_result)
        data_to_send = {"result": wizard_result, "task": task}
        await send_datapackage("createchar_wizard_result", data_to_send, client_id)
    else:
        logger.info("Invalid task")


# save created character
async def client_save_character(client_info, client_id):
    createchar_data = client_info["data"]["createchar_data"]
    logger.info(createchar_data)
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
        logger.info("save character successfuly")
    else:
        msg_to_send = result[1]
    data_to_send = {"result": msg_to_send, "task": "after_char_saved"}
    await send_datapackage("save_character_result", data_to_send, client_id)


# transcribe audio
async def transcribe_audio(client_info, client_id):
    audio_data = client_info["data"]["audio_data"]
    if "," in audio_data:
        audio_data = audio_data.split(",")[1]
    # audio_data = base64.b64decode(audio_data)
    transcripted_text = await tabby_fastapi.transcribe_audio(audio_data=audio_data)
    logger.info("Transripted Text: " + transcripted_text)
    data_to_send = {"transcripted_text": transcripted_text, "task": "transcript_audio"}
    await send_datapackage("transcript_audio_result", data_to_send, client_id)


# play background music
async def play_bg_music(client_info, client_id):
    music_name = client_info["data"]["music_name"]
    url = config_data["openai_api_chat_base"] + "/music/play/" + music_name
    async with httpx.AsyncClient(timeout=300) as client:
        async with client.stream("GET", url) as response:
            async for chunk in response.aiter_bytes():
                if chunk:
                    audio_data_base64 = base64.b64encode(chunk).decode("utf-8")
                    data_to_send = {
                        "audio_data": audio_data_base64,
                        "mode": "stream",
                        "status": "transfer",
                    }
                    await send_datapackage(
                        "play_bg_music_result", data_to_send, client_id
                    )
                    await asyncio.sleep(0.01)
                else:
                    logger.info("Failed to get audio data")
    logger.info("Transfer ends")
    await send_datapackage(
        "play_bg_music_result",
        {"mode": "stream", "status": "end"},
        client_id,
    )


async def language_switch(client_info, client_id):
    language = client_info["data"]["language"]
    language_data = await getGlobalConfig("language_data")
    language_data_jsonstring = json.dumps(language_data, indent=4)
    logger.info("Language switched to: " + language)
    # create a prompt for translate the values in language data jsonstring to the language that user selected
    prompt = (
        "Translate all the values in the following json string to "
        + language
        + ": "
        + language_data_jsonstring
        + "\n\nThe final output will ONLY be a json string with the same structure as the input json string, but with all the values translated to the "
        + language
        + " language, no other text or comment is needed."
    )
    # calculate the time it takes to translate the language data
    start_time = time.time()
    result = await languageClient.chat.completions.create(
        model=model_for_translate,
        messages=[
            {"role": "system", "content": "You are a uncensored translator assistant"},
            {"role": "user", "content": prompt},
        ],
        stream=False,
        temperature=0.7,
    )
    end_time = time.time()
    translate_time = end_time - start_time
    logger.info(f"Time taken to translate language data: {translate_time} seconds")
    # remove '```json' and '```' from the result
    translated_language_data = (
        result.choices[0].message.content.replace("```json\n", "").replace("\n```", "")
    )
    # logger.info("Translated text: " + translated_language_data)
    data_to_send = {
        "language": language,
        "task": "language_switch",
        "translated_language_data": translated_language_data,
    }
    await send_datapackage("language_switch_result", data_to_send, client_id)


async def translate_story_intro(client_info, client_id):
    story_name = client_info["data"]["story_name"]
    intro_text = client_info["data"]["intro_text"]
    aiRoleId = client_info["data"]["aiRoleId"]
    language = client_info["data"]["language"]
    json_to_translate = {"story_name": story_name, "intro_text": intro_text}
    json_to_translate = json.dumps(json_to_translate, indent=4)
    prompt = f"Translate the values in the following json to {language} language with natural expression:\n{json_to_translate}\n\nOnly output the json string with same structure as the input json string, do not translate the text of '{{{{char}}}}', no other text or comment is needed."
    result = await languageClient.chat.completions.create(
        model=model_for_translate,
        messages=[
            {"role": "system", "content": "You are a uncensored translator assistant"},
            {"role": "user", "content": prompt},
        ],
        stream=False,
        temperature=0.7,
    )
    translated_json_data = (
        result.choices[0].message.content.replace("```json\n", "").replace("\n```", "")
    )
    fixed_json_data = json5.loads(translated_json_data)
    logger.info(fixed_json_data)
    fixed_json_data = json.dumps(fixed_json_data, indent=4)
    data_to_send = {
        "translated_story_intro_data": fixed_json_data,
        "task": "translate_story_intro",
        "aiRoleId": aiRoleId,
    }
    await send_datapackage("translate_story_intro_result", data_to_send, client_id)


# ws event handler
ws_events_dict = {
    "connect to server": client_connect,
    "client_login": client_login,
    "client_google_login": client_google_login,
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
    "transcribe_audio": transcribe_audio,
    "sentence_completion": sentence_completion,
    "play_bg_music": play_bg_music,
    "language_switch": language_switch,
    "translate_story_intro": translate_story_intro,
}


async def execute_function(event_name, *args, **kwargs):
    func = ws_events_dict.get(event_name)
    if func:
        await func(*args, **kwargs)
    else:
        logger.info("No matched function")


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
            print("{}".format(ansiColor.color_text(client_id, ansiColor.BG_BRIGHT_RED)))


if __name__ == "__main__":
    host = config_data["server_address"]
    port = config_data["server_port"]
    try:
        clear_screen()
        ansiColor.color_print(
            "Cyber Chat Ver 1.0 by muffin", ansiColor.BG_BRIGHT_MAGENTA, ansiColor.BOLD
        )
        uvicorn.run(app, host=host, port=port, access_log=False)
    except KeyboardInterrupt:
        logger.info("Server has been shut down.")
