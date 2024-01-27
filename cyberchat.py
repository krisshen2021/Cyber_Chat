from gevent import monkey
monkey.patch_all()
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
import os, uuid, json, markdown,yaml
from transformers import pipeline
from user_room_multiuser import chatRoom
from user_room_multiuser_uncensor_apiserver import chatRoom_unsensor
from concurrent.futures import ThreadPoolExecutor

dir_path = os.path.dirname(os.path.realpath(__file__))
config_path = os.path.join(dir_path, 'config', 'config.yml')
with open(config_path, 'r') as file:
            config_data = yaml.safe_load(file)
sentimodelpath = "touch20032003/xuyuan-trial-sentiment-bert-chinese"
sentiment_pipeline = pipeline('sentiment-analysis', model=sentimodelpath, tokenizer=sentimodelpath)
executor = ThreadPoolExecutor(max_workers=10)

chatRoomList = {} #create a chat room list , with conid and chatroom object that generated from chatRoom class.

app = Flask(__name__)
socketio = SocketIO(app, path="/chat", ping_interval=10, cors_allowed_origins="*", async_mode='gevent')

def send_status(messages,room_id):
    print(f'send {messages} to {room_id}')
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
        selected_username = request.form['username']
        selected_usergender = request.form['usergender']
        selected_ai_role_name = request.form['ai_role_name']
        selected_ainame = request.form['ainame']
        selected_is_uncensored = request.form['is_uncensored']
        conid = request.form['conid']
        return render_template('webhook_client_multiuser.html', conid=conid, selected_username=selected_username,
                               selected_usergender=selected_usergender, selected_ai_role_name=selected_ai_role_name,
                               selected_ainame=selected_ainame,selected_is_uncensored=selected_is_uncensored)
# after selected role, enter chat room, and bring the connection id to the room, the conid is get from cookie of browser.

# socket actions

@socketio.on('connect')
def client_connect():
    query_args = request.args
    conid = query_args.get('conid')
    username = query_args.get('username')
    usergender = query_args.get('usergender')
    ai_role_name = query_args.get('ai_role_name')
    ai_is_uncensored = query_args.get('ai_is_uncensored')
    conversation_id = request.sid #every time a client connect to server , it will generate a request sid, we use it to define a new conversation.
    print(
        f'server has been connected by conid: {conid}, SID is: {conversation_id},  {username} who gender is {usergender} has came in with role: {ai_role_name} selected, which uncensored is: {ai_is_uncensored}')
    #as we know, conid to define the same user in a chat period between different roles, and SID to define user's different conversation with ai role.
    #once user enter the system, and connect to server, user will get a consistent conid that created by uid and cookie in client side, it will not change until user close the browser
    
    # if conid in chatRoomList: 
    # create new user chat room if conid not existed
@socketio.on('initialize room')
def initializeRoom(client_msg):
    conid = client_msg["data"]["conid"]
    username = client_msg["data"]["username"]
    usergender = client_msg["data"]["usergender"]
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
            userCurrentRoom.usergender = usergender
            if hasattr(userCurrentRoom, 'windowRatio'):
                userCurrentRoom.windowRatio = windowRatio
            break
    else:    
        if ai_is_uncensored == "No":
            chatRoomList[conid] = chatRoom(ai_role_name=ai_role_name, username=username, usergender=usergender, conid=conid,
                                        conversation_id=conversation_id, sentiment_pipeline=sentiment_pipeline, send_msg_websocket=send_status) #Generate a unique chatRoom with unique conid for specific user.
            print("a censored room created")
        else:
            chatRoomList[conid] = chatRoom_unsensor(ai_role_name=ai_role_name, username=username, usergender=usergender, conid=conid,
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
            'speaker': userCurrentRoom.ai_speakers,
            'speak_tone': userCurrentRoom.speaker_tone,
            'ttskey': userCurrentRoom.ttskey,
            'dynamic_picture':False,
            'bgImg': userCurrentRoom.bkImg,
            'model_list': userCurrentRoom.model_list,
            'instruct_list': userCurrentRoom.instr_temp_list
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
    user_ai_text = markdownText(userCurrentRoom.G_ai_text)
    print('chat has been reset')
    data_to_send = {
        'message': user_ai_text,
        'voice_text': userCurrentRoom.G_voice_text,
        'avatar': userCurrentRoom.G_avatar_url,
        'speaker': userCurrentRoom.ai_speakers,
        'speak_tone': userCurrentRoom.speaker_tone,
        'ttskey': userCurrentRoom.ttskey,
        'dynamic_picture': False,
        'bgImg': userCurrentRoom.bkImg,
        'model_list': userCurrentRoom.model_list,
        'instruct_list': userCurrentRoom.instr_temp_list
    }
    socketio.emit('my response', {'data': data_to_send}, room=userCurrentRoom.conversation_id)

@socketio.on('regen_msg')
#user ask for regenerate message
def regen_msg(client_msg):
    conid = client_msg['data']['conid']
    usermsg = client_msg['data']['message']
    embbedswitcher = client_msg['data']['isembbed']
    transswitcher = client_msg['data']['istranslated']
    userCurrentRoom = chatRoomList[conid]
    if hasattr(userCurrentRoom,'state'):
        userCurrentRoom.state["translate"] = True if transswitcher else False
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
                print(response)
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

@socketio.on('send_user_msg')
#when user send message , send it to user's chatroom
def reply_user_query(client_msg):
    conid = client_msg['data']['conid']
    usermsg = client_msg['data']['message']
    embbedswitcher = client_msg['data']['isembbed']
    transswitcher = client_msg['data']['istranslated']
    userCurrentRoom = chatRoomList[conid]
    if hasattr(userCurrentRoom, 'state'):
        userCurrentRoom.state["translate"] = True if transswitcher else False

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
    
