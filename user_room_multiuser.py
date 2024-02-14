import os
# import openai
from openai import OpenAI
import random
import re
from airole_creator import airole,summaryTool
from embedding_chroma import chroma_embedding

# set the shared settings
dir_path = os.path.dirname(os.path.realpath(__file__))
openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
# openai.api_key = os.getenv("OPENAI_API_KEY")

try:
    embbeder = chroma_embedding()
except Exception as e:
    print("Error initialize embedding:", e)
    class chroma_null:
        def __init__(self) -> None:
            pass
        def queryEmb(self,text) -> None:
            return text
    embbeder = chroma_null()

#the main room class
class chatRoom:
    def __init__(self,user_sys_name,ai_role_name,username, usergender, user_facelooks, conid, conversation_id, sentiment_pipeline, send_msg_websocket:callable = None) -> None:
        self.send_msg_websocket = send_msg_websocket
        self.user_sys_name = user_sys_name
        self.ai_role_name = ai_role_name
        self.username = username
        self.usergender = usergender
        self.user_facelooks = user_facelooks
        self.conid=conid
        self.conversation_id = conversation_id
        self.ai_role=object()
        self.summary_tool=object()
        self.messages=[]
        self.initialize_msg=[]
        self.ai_lastword=''
        self.G_avatar_url = ''
        self.G_ai_text = ''
        self.G_voice_text = ''
        self.ai_speakers = ''
        self.speaker_tone = ''
        self.ttskey = os.environ.get('SPEECH_KEY')
        self.sentiment_pipeline = sentiment_pipeline
        self.initialization_start = False

    def extract_text(self,text):
        clean_text = re.sub(r'\*[^*]*\*', '', text)
        clean_text = re.sub(r'```[^```]*```', '', clean_text)
        return clean_text    

    def initialize(self):
        self.initialization_start = True
        self.send_msg_websocket({"name":"initialization","msg":"Generate Chat Environment ..."}, self.conversation_id)
        self.ai_role=airole(roleselector=self.ai_role_name,username=self.username,usergender=self.usergender)
        self.summary_tool=summaryTool(self.ai_role)
        self.start_stats()
        self.send_msg_websocket({"name":"initialization","msg":"DONE"}, self.conversation_id)
        self.initialization_start = False
        return True
    
    def start_stats(self):
        self.initialize_msg.clear()
        self.messages.clear()
        self.messages = [
        {"role": "system", "content": self.ai_role.ai_system_role},
        {"role": "user", "content": self.ai_role.initial_scene},
        {"role": "assistant", "content": self.ai_role.initial_assistant_reply+self.ai_role.welcome_text},
        ]
        self.initialize_msg = self.messages.copy()
        self.ai_lastword=''
        self.G_ai_text = self.ai_role.welcome_text
        self.G_voice_text = self.extract_text(self.ai_role.welcome_text)
        self.G_avatar_url = f'/static/images/avatar/{self.ai_role_name}/none.png'
        self.G_userlooks_url = f'/static/images/avatar/user_{self.usergender}.png'
        self.user_bkImg = f'/static/images/avatar/user_{self.usergender}.png'
        self.bkImg = f'/static/images/avatar/{self.ai_role_name}/background.png'
        self.model_list=[]
        self.instr_temp_list=[]
        self.SD_model_list=[]
        self.ai_speakers = self.ai_role.ai_speaker
        self.speaker_tone = 'affectionate'

    def create_envart(self):
        pass



    def is_chinese(self,text):
        clean_text = re.sub(r'[^\u4e00-\u9fa5]', '', text)
        return len(clean_text) > 0
    
    def regen_msg(self,user_msg,embbedswitcher):
        for i in range(2):
            self.messages.pop(1)
        ai_text, voice_text, speaker, speak_tone, avatar_url, conversation_id, dynamic_picture = self.server_reply(user_msg,embbedswitcher)
        return ai_text, voice_text, speaker, speak_tone, avatar_url, conversation_id, dynamic_picture
    
    def server_reply(self,usermsg,embbedswitcher):
        text = usermsg
        embbed = embbedswitcher
        if embbed == "yes":
            text = embbeder.queryEmb(text)
        print(text)
        usertext = {"role": "user", "content": f"{text}"}
        self.messages.append(usertext)
        token_before_response = self.summary_tool.count_tokens(self.messages)
        # print(f'the token before response: {token_before_response}')
        if token_before_response > 4000:
            self.messages = self.summary_tool.summary_message(self.messages, self.ai_lastword, text, "")
            # print(f"the messages after summary is:{self.messages}")
        temperatureNums = [0.7, 0.8, 0.9]
        temprature = random.choice(temperatureNums)
        # print(f"the temprature now is {temprature}")
        # response = openai.ChatCompletion.create(model='gpt-3.5-turbo', messages=self.messages, temperature=temprature, max_tokens=500)
        self.send_msg_websocket({"name":"chatreply","msg":"Generate Response"}, self.conversation_id)
        response = openai_client.chat.completions.create(model='gpt-3.5-turbo', messages=self.messages, temperature=temprature, max_tokens=500)
        tts_text = response.choices[0].message.content
        print(tts_text)
        tts_text_extracted = self.extract_text(tts_text)
        #get tts text and process the emotion and code format
        
        emotion = self.sentiment_pipeline(tts_text_extracted)
        emotion_des = emotion[0]['label']
        #self.speaker_tone = "sad"
        if emotion_des == "none":
            self.speaker_tone = "affectionate"
        elif emotion_des == "happiness":
            self.speaker_tone = "cheerful"
        elif emotion_des == "anger":
            self.speaker_tone = "sad"
        elif emotion_des == "disgust":
            self.speaker_tone = "disgruntled"
        elif emotion_des == "fear":
            self.speaker_tone = "fearful"
        elif emotion_des == "like":
            self.speaker_tone = "gentle"
        elif emotion_des == "sadness":
            self.speaker_tone = "depressed"
        elif emotion_des == "surprise":
            self.speaker_tone = "cheerful"

        avatar_url = f'/static/images/avatar/{self.ai_role_name}/{emotion_des}.png'
        print(avatar_url)

        self.ai_lastword = tts_text
        self.messages.append({"role": "assistant", "content": f"{tts_text}"})

        # print(self.messages)
        token_after_response = self.summary_tool.count_tokens(self.messages)

        if token_after_response > 4000:
            self.messages = self.summary_tool.summary_message(self.messages, "", text, tts_text)
            # print(f"the messages after summary is:{messages}")
            
        if self.is_chinese(tts_text_extracted):
            self.ai_speakers = self.ai_role.ai_speaker
        else:
            self.ai_speakers = self.ai_role.ai_speaker_en
        print(self.ai_speakers)

        self.G_avatar_url = avatar_url
        self.G_ai_text = tts_text
        self.G_voice_text = tts_text_extracted
        self.send_msg_websocket({"name":"chatreply","msg":"DONE"}, self.conversation_id)
        return self.G_ai_text,self.G_voice_text,self.ai_speakers,self.speaker_tone,self.G_avatar_url,self.conversation_id,False