from gevent import monkey
monkey.patch_all()
from flask import Flask, render_template, request
from flask_socketio import SocketIO
import os, uuid, json, markdown,yaml
from transformers import pipeline
from user_room_multiuser import chatRoom
from user_room_multiuser_uncensor_apiserver import chatRoom_unsensor
from concurrent.futures import ThreadPoolExecutor
from user_validation import Validation
from sqliteclass import SQLiteDB

dir_path = os.path.dirname(os.path.realpath(__file__))
config_path = os.path.join(dir_path, 'config', 'config.yml')
with open(config_path, 'r') as file:
            config_data = yaml.safe_load(file)
sentimodelpath = "touch20032003/xuyuan-trial-sentiment-bert-chinese"
sentiment_pipeline = pipeline('sentiment-analysis', model=sentimodelpath, tokenizer=sentimodelpath)
executor = ThreadPoolExecutor(max_workers=10)

chatRoomList = {} #create a chat room list , with conid and chatroom object that generated from chatRoom class.
database = SQLiteDB()
database.create_table()

app = Flask(__name__)
socketio = SocketIO(app, path="/chat", ping_interval=10, ping_timeout=5, cors_allowed_origins="*", async_mode='gevent')

def send_status(messages,room_id):
    # print(f'send {messages} to {room_id}')
    data_to_send={
        'message': messages
    }
    socketio.emit('status from server',{'data': data_to_send}, room = room_id)

def markdownText(text):
    Mtext = markdown.markdown(text, extensions=['pymdownx.superfences', 'pymdownx.highlight', 'pymdownx.magiclink'])
    return Mtext

@app.route('/')
def index():
    cookid_server = uuid.uuid1()
    dir_path = os.path.dirname(os.path.realpath(__file__))
    roles_path = os.path.join(dir_path, 'config', 'roles.json')
    with open(roles_path, 'r', encoding='utf-8') as f:
        roleconf = json.load(f)
    ainame = []
    ai_is_uncensored = []
    for key, value in roleconf.items():
        ainame.append(value.get("ai_name")) #read the ai_name list
        ai_is_uncensored.append(value.get("if_uncensored")) #read the uncensored flag list
    roleitems = list(roleconf.keys()) #read all the role name list
    return render_template('role_selector.html', cookid_server=cookid_server, roleslist=roleitems, ainamelist=ainame, censoredlist=ai_is_uncensored)
# get role list

@app.route('/enter_room', methods=['GET', 'POST'])
def enter_room():
    if request.method == 'POST':
        userdata = {
        'username': request.form['username'],
        'nickname': request.form['nickname'],
        'gender': request.form['gender'],
        'avatar': request.form['avatar'],
        'facelooks': request.form['facelooks'],
        'credits': request.form['credits'],
        'ai_role_name': request.form['ai_role_name'],
        'ainame': request.form['ainame'],
        'is_uncensored': request.form.get('is_uncensored', "Yes"),  # 使用 .get() 以处理缺失的字段
        'conid': request.form['conid'],
        }

        return render_template('webhook_client_multiuser.html', **userdata)
# after selected role, enter chat room, and bring the connection id to the room, the conid is get from cookie of browser.
     
    
@socketio.on('client_signup')
def client_signup(client_info):
     if client_info["data"]["nickname"] == "":
        client_info["data"]["nickname"] = client_info["data"]["username"]

     username = client_info["data"]["username"]
     nickname = client_info["data"]["nickname"]
     email = client_info["data"]["email"]
     password = client_info["data"]["password"]
     gender = client_info["data"]["gender"]
     facelooks = client_info["data"]["facelooks"]
     conversation_id = client_info["data"]["socket_id"]
     
     vali_result = Validation.vali_data(client_info["data"])
     if vali_result["validated"]:
         avatar = "/static/images/avatar/profile_" + gender + ".png"
         data_op_result = database.create_new_user(username=username,nickname=nickname,gender=gender,password=password,email=email,credits=1000, avatar=avatar, facelooks=facelooks)
         if isinstance(data_op_result, str):
              print(data_op_result)
              send_status({"name":"signup_authorization","msg":{"status":"Fail","data":data_op_result}}, conversation_id)
         else:
              userdata = database.get_user(username,password)
              userdata.pop("unique_id", None)
              userdata.pop("password", None)
              send_status({"name":"signup_authorization","msg":{"status":"Success","data":userdata}}, conversation_id)
     else:
          error = vali_result["data"]
          send_status({"name":"signup_validation","msg":{"status":"Fail","data":error}}, conversation_id)
     pass

@socketio.on('client_login')
def client_login(client_info):
     username = client_info["data"]["username"]
     password = client_info["data"]["password"]
     conversation_id = client_info["data"]["socket_id"]
     vali_result = Validation.vali_data(client_info["data"])
     if vali_result["validated"]:
          data_op_result = database.get_user(username, password)
          if isinstance(data_op_result, str):
               send_status({"name":"login_authorization","msg":{"status":"Fail","data":data_op_result}}, conversation_id)
          else:
               data_op_result.pop("unique_id", None)
               data_op_result.pop("password", None)
               send_status({"name":"login_authorization","msg":{"status":"Success","data":data_op_result}}, conversation_id)
     else:
          error = vali_result["data"]
          send_status({"name":"login_validation","msg":{"status":"Fail","data":error}}, conversation_id)
     pass

@socketio.on('connect')
def client_connect():
    print(f'The server has been connected by request id: [{request.sid}]')
    pass

@socketio.on('disconnect')
def client_disconnect():
    user_sid = request.sid
    for conid, room in list(chatRoomList.items()):
        if room.conversation_id == user_sid:
            del chatRoomList[conid]
            break
    print(f'User {user_sid} disconnected, room removed')

  
@socketio.on('initialize_room')
def initializeRoom(client_msg):
    conid = client_msg["data"]["conid"]
    username = client_msg["data"]["username"]
    user_sys_name = client_msg["data"]["user_sys_name"]
    usergender = client_msg["data"]["usergender"]
    user_facelooks = client_msg["data"]["user_facelooks"]
    ai_role_name = client_msg["data"]["ai_role_name"]
    ai_is_uncensored = client_msg["data"]["ai_is_uncensored"]
    windowRatio = round(float(client_msg["data"]["windowRatio"]),2)
    conversation_id = client_msg["data"]["socket_id"]
    for roomid in chatRoomList.keys():
        if roomid == conid:
            userCurrentRoom = chatRoomList[roomid]
            userCurrentRoom.conversation_id = conversation_id
            userCurrentRoom.ai_role_name=ai_role_name
            userCurrentRoom.username = username
            userCurrentRoom.user_sys_name = user_sys_name
            userCurrentRoom.usergender = usergender
            userCurrentRoom.user_facelooks = user_facelooks
            if hasattr(userCurrentRoom, 'windowRatio'):
                userCurrentRoom.windowRatio = windowRatio
            break
    else:    
        if ai_is_uncensored == "No":
            chatRoomList[conid] = chatRoom(user_sys_name=user_sys_name, ai_role_name=ai_role_name, username=username, usergender=usergender, user_facelooks=user_facelooks, conid=conid,
                                        conversation_id=conversation_id, sentiment_pipeline=sentiment_pipeline, send_msg_websocket=send_status) #Generate a unique chatRoom with unique conid for specific user.
            print("a censored room created")
        else:
            chatRoomList[conid] = chatRoom_unsensor(user_sys_name=user_sys_name, ai_role_name=ai_role_name, username=username, usergender=usergender, user_facelooks=user_facelooks, conid=conid,
                                        conversation_id=conversation_id, sentiment_pipeline=sentiment_pipeline, windowRatio=windowRatio, send_msg_websocket=send_status)
            print("a uncensored room created")
        userCurrentRoom = chatRoomList[conid]

    if not userCurrentRoom.initialization_start:
        userCurrentRoom.initialize()
        print(chatRoomList)
        user_ai_text = markdownText(userCurrentRoom.G_ai_text)
        data_to_send = {
            'message': user_ai_text,
            'voice_text': userCurrentRoom.G_voice_text,
            'avatar': userCurrentRoom.G_avatar_url,
            'user_looks': userCurrentRoom.G_userlooks_url,
            'speaker': userCurrentRoom.ai_speakers,
            'speak_tone': userCurrentRoom.speaker_tone,
            'ttskey': userCurrentRoom.ttskey,
            'dynamic_picture':False,
            'bgImg': userCurrentRoom.bkImg,
            'user_bkImg': userCurrentRoom.user_bkImg,
            'model_list': userCurrentRoom.model_list,
            'instruct_list': userCurrentRoom.instr_temp_list,
            'SD_model_list': userCurrentRoom.SD_model_list
        }
        socketio.emit('my response', {'data': data_to_send}, room=userCurrentRoom.conversation_id)
    #send response data to user's current conversation , it ensure the response to the correct chat dialogue.
    #in other words, every user will have a chatroom object during enter the system by conid. meanwhile, user has different dialogue with ai that indicate by conversation id.
    # a chat room object can generate different ai role with all of related elements in terms of welcome message, speakers, etc., 


@socketio.on('restart')
def reset(client_msg):
    conid = client_msg['data']['conid']
    windowRatio = client_msg['data']['windowRatio']
    userCurrentRoom = chatRoomList[conid]
    embbedswitcher = client_msg['data']['isembbed']
    transswitcher = client_msg['data']['istranslated']
    if hasattr(userCurrentRoom,'state'):
        userCurrentRoom.state['translate'] = True if transswitcher else False
    if hasattr(userCurrentRoom, 'windowRatio'):
        userCurrentRoom.windowRatio = round(float(windowRatio),2)
    userCurrentRoom.start_stats()
    userCurrentRoom.create_envart()
    user_ai_text = markdownText(userCurrentRoom.G_ai_text)
    print('chat has been reset')
    data_to_send = {
        'message': user_ai_text,
        'voice_text': userCurrentRoom.G_voice_text,
        'avatar': userCurrentRoom.G_avatar_url,
        'user_looks': userCurrentRoom.G_userlooks_url,
        'speaker': userCurrentRoom.ai_speakers,
        'speak_tone': userCurrentRoom.speaker_tone,
        'ttskey': userCurrentRoom.ttskey,
        'dynamic_picture': False,
        'bgImg': userCurrentRoom.bkImg,
        'user_bkImg': userCurrentRoom.user_bkImg,
        'model_list': userCurrentRoom.model_list,
        'instruct_list': userCurrentRoom.instr_temp_list,
        'SD_model_list': userCurrentRoom.SD_model_list
    }
    socketio.emit('my response', {'data': data_to_send}, room=userCurrentRoom.conversation_id)
    send_status({"name":"initialization","msg":"DONE"}, userCurrentRoom.conversation_id)

@socketio.on('regen_msg')
#user ask for regenerate message
def regen_msg(client_msg):
    conid = client_msg['data']['conid']
    usermsg = client_msg['data']['message']
    embbedswitcher = client_msg['data']['isembbed']
    transswitcher = client_msg['data']['istranslated']
    windowRatio = client_msg['data']['windowRatio']
    userCurrentRoom = chatRoomList[conid]
    if hasattr(userCurrentRoom,'state'):
        userCurrentRoom.state["translate"] = True if transswitcher else False
    if hasattr(userCurrentRoom, 'windowRatio'):
        userCurrentRoom.windowRatio = round(float(windowRatio),2)
    def callback_regen(future):
        ai_text, voice_text, speaker, speak_tone, avatar_url, conversation_id, dynamic_picture = future.result()
        user_ai_text = markdownText(ai_text)
        data_to_send = {
            'message': user_ai_text,
            'voice_text': voice_text,
            'avatar': avatar_url,
            'speaker': speaker,
            'speak_tone': speak_tone,
            'ttskey': userCurrentRoom.ttskey,
            'dynamic_picture': dynamic_picture
        }
        socketio.emit('my response', {'data': data_to_send}, room=conversation_id)
    future = executor.submit(userCurrentRoom.regen_msg, usermsg, embbedswitcher)
    future.add_done_callback(callback_regen)

@socketio.on('exit_room')
def exit_user_current_room(client_msg):
    conid = client_msg['data']['conid']
    try:
        if conid in chatRoomList:
            room = chatRoomList[conid].conversation_id
            username = chatRoomList[conid].username
            del chatRoomList[conid]
            print(f'Room:[ {conid} ]has been deleted')
            result = f'Hey {username}\nSee you later!'
    except Exception as e:
            print('Delete chatroom Error', e)
            result = f'Error:{e}'
    data_to_send = {
        'message': result
    }
    socketio.emit('exit_room_success',{'data': data_to_send}, room=room)




@socketio.on('change_model')
#change chat model
def change_model(client_msg):
    conid = client_msg['data']['conid']
    model = client_msg['data']['model']
    userCurrentRoom = chatRoomList[conid]
    def callback_unload(future):
        unloadresp = future.result()
        if unloadresp.status_code == 200:
            def callback_load(future):
                response = future.result()
                # print(response)
                if response == "Success":
                     send_status({"name":"initialization","msg":"DONE"}, userCurrentRoom.conversation_id)
                     pass
                data_to_send = {
                    'message': response
                }
                socketio.emit('model_change_result', {
                            'data': data_to_send}, room=userCurrentRoom.conversation_id)
            future = executor.submit(userCurrentRoom.my_generate.tabby_server.load_model, name=model, send_msg_websocket=send_status)
            future.add_done_callback(callback_load)
            
    future = executor.submit(userCurrentRoom.my_generate.tabby_server.unload_model)
    future.add_done_callback(callback_unload)

@socketio.on("change_instruction")
def change_instruction(client_msg):
    conid = client_msg['data']['conid']
    instruction = client_msg['data']['instruction']
    userCurrentRoom = chatRoomList[conid]
    userCurrentRoom.state["prompt_template"]=instruction
    data_to_send = {
                    'message': "Success"
                    }
    socketio.emit('instruction_change_result', {'data': data_to_send}, room=userCurrentRoom.conversation_id)

@socketio.on("change_SD_Model")
def change_SD_Model(client_msg):
    conid = client_msg['data']['conid']
    SD_Model = client_msg['data']['SD_Model']
    userCurrentRoom = chatRoomList[conid]
    userCurrentRoom.my_generate.image_payload["override_settings"]["sd_model_checkpoint"] = SD_Model
    data_to_send = {
                    'message': "Success"
                    }
    socketio.emit('SD_Model_change_result', {'data': data_to_send}, room=userCurrentRoom.conversation_id)

@socketio.on("save_chat_history")
def save_chat_history(client_msg):
    conid = client_msg['data']['conid']
    userCurrentRoom = chatRoomList[conid]
    result = userCurrentRoom.chat_history_op("save")
    if result:
        send_status({"name":"chat_history_op","msg":{"operation":"save","result":"Success"}}, userCurrentRoom.conversation_id)
    else:
        send_status({"name":"chat_history_op","msg":{"operation":"save","result":"Fail"}}, userCurrentRoom.conversation_id)
    pass

@socketio.on("load_chat_history")
def save_chat_history(client_msg):
    conid = client_msg['data']['conid']
    userCurrentRoom = chatRoomList[conid]
    result = userCurrentRoom.chat_history_op("load")
    if result:
        send_status({"name":"chat_history_op","msg":{"operation":"load","result":result}}, userCurrentRoom.conversation_id)
    else:
        send_status({"name":"chat_history_op","msg":{"operation":"load","result":"Fail"}}, userCurrentRoom.conversation_id)
    pass

@socketio.on('send_user_msg')
#when user send message , send it to user's chatroom
def reply_user_query(client_msg):
    conid = client_msg['data']['conid']
    usermsg = client_msg['data']['message']
    embbedswitcher = client_msg['data']['isembbed']
    transswitcher = client_msg['data']['istranslated']
    windowRatio = client_msg['data']['windowRatio']
    userCurrentRoom = chatRoomList[conid]
    if hasattr(userCurrentRoom, 'state'):
        userCurrentRoom.state["translate"] = True if transswitcher else False
    if hasattr(userCurrentRoom, 'windowRatio'):
        userCurrentRoom.windowRatio = round(float(windowRatio),2)

    def callback(future):
        ai_text, voice_text, speaker, speak_tone, avatar_url, conversation_id, dynamic_picture = future.result()
        user_ai_text = markdownText(ai_text)
        data_to_send = {
            'message': user_ai_text,
            'voice_text': voice_text,
            'avatar': avatar_url,
            'speaker': speaker,
            'speak_tone': speak_tone,
            'ttskey': userCurrentRoom.ttskey,
            'dynamic_picture': dynamic_picture
        }
        socketio.emit('my response', {'data': data_to_send}, room=conversation_id)

    future = executor.submit(userCurrentRoom.server_reply, usermsg, embbedswitcher)
    future.add_done_callback(callback)


if __name__ == '__main__':
    host = config_data["server_address"]
    port = config_data["server_port"]
    debug = config_data["debug_mode"]
    print(f"Cyber Chat Server is running on http://{host}:{port} , debug mode is {debug}")
    socketio.run(app, host=host, port=port, debug=debug)
    
