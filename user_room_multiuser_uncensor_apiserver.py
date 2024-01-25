import os, random, re, io, base64, yaml, copy
from airole_creator_uncensor import airole
from googlecloudtrans import googletransClass
# from azure_translator import azuretransClass
# from deepltrans import deepltransClass
from tabbyAPI_class_pd import tabbyAPI
from PIL import Image
from yeelight import discover_bulbs, Bulb
try:
    bulb = Bulb(config_data["yeelight_url"], auto_on=True, effect="smooth", duration=1000)
    print(f"Bulb Power: {bulb.get_properties()['power']}")
except Exception as e:
            print(f"Error during turn on Bulb: {e}")
            class bulb_null:
                def __init__(self) -> None:
                    pass
                def set_hsv(self,r,g,b)-> None:
                    pass
            bulb = bulb_null()

image_payload = {
            "hr_scale" : 1.5,
            "hr_second_pass_steps" : 10,
            "seed" :-1,
            "enable_hr" : False,
            "width" : 256,
            "height" : 256,
            "hr_upscaler" : config_data["hr_upscaler"],
            # "sampler_name" : "DPM++ 2M Karras",
            "sampler_name": config_data["sampler_name"],
            "cfg_scale" :7,
            "denoising_strength" : 0.5,
            "steps" : 30,
            "override_settings" :{
                "sd_vae" : "Automatic",
                "sd_model_checkpoint":  config_data["sd_model_checkpoint"]
                },
            "override_settings_restore_afterwards" : False
        }

state = {
    # "openai_api_chat_base": "https://glorious-alpaca-genuinely.ngrok-free.app/v1",
    "openai_api_chat_base": config_data["openai_api_chat_base"],
    "openai_api_funcall_base": config_data["openai_api_funcall_base"],
    "openai_api_rephase_base": config_data["openai_api_rephase_base"],
    "SDAPI_url": config_data["SDAPI_url"],
    "prompt_template": "Alpaca_RP",
    "max_seq_len":4096,
    "max_new_tokens": 300,
    "frequency_penalty": 0,
    "presence_penalty": 0.4,
    "repetition_penalty": 1.1,
    "temperature_last": True,
    "mirostat_mode": 0,
    "min_p":0.05,
    "tfs":0.95,
    "ban_eos_token": False,
    "custom_stop_string": ["\nInput:", "\n[", "\n(", "\n### Input:"],
    "temperature": 1,  
    "top_k":50,
    "top_p":1,
    "translate":True,
    "char_looks":"",
    "char_avatar":"",
    "env_setting":"",
    "conversation_id":"",
    "generate_dynamic_picture": True
}

#Read prompt template
dir_path = os.path.dirname(os.path.realpath(__file__))
prompt_template_path = os.path.join(dir_path, "config", "prompts", "prompt_template.yaml")
with open(prompt_template_path, 'r') as file:
    prompts_templates = yaml.safe_load(file)
    instr_temp_list=[]
    for templates in prompts_templates.keys():
        instr_temp_list.append(templates)
    print(f'>>>The instruction templates list: {instr_temp_list}')
    # context_template = prompts_templates["Alpaca_RP"]
    # context_template = prompts_templates[state["prompt_template"]]

myTrans = googletransClass()



#the main room class
class chatRoom_unsensor:
    def __init__(self,ai_role_name,username, usergender, conid, conversation_id, sentiment_pipeline, windowRatio, send_msg_websocket) -> None:
        self.send_msg_websocket = send_msg_websocket
        self.ai_role_name = ai_role_name
        self.username = username
        self.usergender = usergender
        self.conid=conid
        self.conversation_id = conversation_id
        self.ai_role=object()
        self.summary_tool=object()
        self.messages=""
        self.chathistory=[]
        self.ai_lastword=''
        self.G_avatar_url = ''
        self.G_ai_text = ''
        self.G_voice_text = ''
        self.ai_speakers = ''
        self.speaker_tone = ''
        self.ttskey = os.environ.get('SPEECH_KEY')
        self.sentiment_pipeline = sentiment_pipeline
        self.dynamic_picture = ''
        self.windowRatio = windowRatio
        self.initialization_start = False

    def extract_text(self,text):
        clean_text = re.sub(r'\*[^*]*\*', '', text)
        clean_text = re.sub(r'```[^```]*```', '', clean_text)
        return clean_text    
    def create_instruct_template(self, ainame,username):
        template = prompts_templates[self.state["prompt_template"]]
        pt=template.replace(r"<|character|>",ainame).replace(r"<|user|>", username)
        return pt

    def initialize(self):
        self.initialization_start = True
        self.state = copy.deepcopy(state)
        self.ai_role=airole(roleselector=self.ai_role_name,username=self.username,usergender=self.usergender)
        self.start_stats()
        #customize state
        self.state["conversation_id"] = self.conversation_id
        self.state['custom_stop_string']=state['custom_stop_string']+[f'{self.username}:',f'{self.ainame}:','###']
        self.state['char_looks'] = self.ai_role.char_looks
        self.state['env_setting'] = self.ai_role.backgroundImg
        self.state['char_avatar'] = self.ai_role.char_avatar
        self.state['max_new_tokens'] = self.ai_role.max_new_tokens
        self.state['generate_dynamic_picture'] = self.ai_role.generate_dynamic_picture
        print(f'>>>Generate Dynamic Picture: {self.state["generate_dynamic_picture"]}')
        print(f'>>>The max new token: {self.state["max_new_tokens"]}')
        self.my_generate = tabbyAPI(state=self.state, image_payload=image_payload, send_msg_websocket=self.send_msg_websocket)
        self.send_msg_websocket({"name":"initialization","msg":"Get Model List ..."}, self.conversation_id)
        self.current_model = self.my_generate.tabby_server.get_model()
        self.model_list = self.my_generate.tabby_server.get_model_list()
        self.instr_temp_list = instr_temp_list
        self.send_msg_websocket({"name":"initialization","msg":"Generate Chat Environment ..."}, self.conversation_id)
        self.bkImg = 'data:image/png;base64,' + self.gen_bgImg(self.my_generate, self.state['char_looks'], self.state['env_setting'])
        self.send_msg_websocket({"name":"initialization","msg":"Generate Avatar ..."}, self.conversation_id)
        self.G_avatar_url = 'data:image/png;base64,' + self.gen_avatar(self.my_generate,self.state['char_avatar'], "smile")
        if self.ai_role.model_to_load is not False:
            self.my_generate.tabby_server.unload_model()
            self.my_generate.tabby_server.load_model(name=self.ai_role.model_to_load, send_msg_websocket=self.send_msg_websocket)
        if self.ai_role.prompt_to_load is not False:
            self.state['prompt_template'] = self.ai_role.prompt_to_load
        self.send_msg_websocket({"name":"initialization","msg":"DONE"}, self.conversation_id)
        self.initialization_start = False
        return True
    
    def start_stats(self):
        self.ainame = self.ai_role.ai_role_name
        self.chathistory.clear()
        self.messages=""
        self.char_desc_system = self.ai_role.ai_system_role.replace(r'<|Current Chapter|>',self.ai_role.chapters[0]['name'])
        self.messages = f"{self.char_desc_system}{self.ainame}: {self.ai_role.welcome_text_dec}"
        self.messages = self.messages.replace(r"{{char}}",self.ainame).replace(r"{{user}}",self.username)
        self.chathistory.append(self.messages)
        self.ai_lastword=''
        self.G_ai_text = self.ai_role.welcome_text_dec.replace(r"{{user}}",self.username).replace(r"{{char}}",self.ainame)
        self.G_ai_text = myTrans.translate_text("zh-cn",self.G_ai_text) if self.state['translate'] else self.G_ai_text
        self.G_voice_text = self.extract_text(self.G_ai_text)
        self.ai_speakers = self.ai_role.ai_speaker
        self.speaker_tone = 'affectionate'
        pass

    def gen_bgImg(self,tabbyGen,char_looks,bgImgstr):
        print(f'>>>The window ratio[w/h]: {self.windowRatio}')
        tabbyGen.image_payload['enable_hr'] = True
        tabbyGen.image_payload['width'] = 1024 if self.windowRatio >= 1 else 512
        tabbyGen.image_payload['height'] = int(tabbyGen.image_payload['width'] / self.windowRatio)
        tabbyGen.image_payload['steps'] = 50
        print(">>>Generate Background\n")
        bkImg = tabbyGen.generate_image(prompt_prefix=tabbyGen.prmopt_fixed_prefix, char_looks=char_looks, env_setting=bgImgstr, prompt_suffix=tabbyGen.prmopt_fixed_suffix)
        image_save = Image.open(io.BytesIO(base64.b64decode(bkImg)))
        image_save.save(os.path.join(dir_path, "static",
                        "images", "avatar", self.ai_role_name, "background.png"))
        return bkImg
    
    def gen_avatar(self,tabbyGen,char_avatar,emotion):
        tabbyGen.image_payload['enable_hr'] = False
        tabbyGen.image_payload['width'] = 256
        tabbyGen.image_payload['height'] = 256
        tabbyGen.image_payload['steps'] = 25
        char_avatar = char_avatar.replace('<|emotion|>',emotion)
        print(">>>Generate avatar\n")
        avatarImg = tabbyGen.generate_image(prompt_prefix=tabbyGen.prmopt_fixed_prefix, char_looks=char_avatar, env_setting=self.state['env_setting'], prompt_suffix=tabbyGen.prmopt_fixed_suffix)
        image_save = Image.open(io.BytesIO(base64.b64decode(avatarImg)))
        image_save.save(os.path.join(dir_path, "static",
                        "images", "avatar", self.ai_role_name, "none.png"))
        return avatarImg
    
    def is_chinese(self,text):
        clean_text = re.sub(r'[^\u4e00-\u9fa5]', '', text)
        return len(clean_text) > 0
    
    def regen_msg(self,user_msg,embbedswitcher):
        for i in range(2):
            del self.chathistory[-1]
        ai_text, voice_text, speaker, speak_tone, avatar_url, conversation_id, dynamic_picture = self.server_reply(user_msg,embbedswitcher)
        return ai_text, voice_text, speaker, speak_tone, avatar_url, conversation_id, dynamic_picture
    
    def server_reply(self,usermsg,embbedswitcher):
        input_text = myTrans.translate_text("en",usermsg)
        self.chathistory.append(f'{self.username}: {input_text}')       
        print(">>> Generate Response:")
        instruct_template = self.create_instruct_template(self.ainame,self.username)
        prompt = "\n".join(self.chathistory)
        prompt = instruct_template.replace(r"<|prompt|>",prompt)
        token_limition = int(self.my_generate.tabby_server.model_load_data["max_seq_len"]-self.state["max_new_tokens"]-200)
        while self.my_generate.count_token_numbers(prompt) >= token_limition:
            for i in range(2):
                self.chathistory.pop(1)
            prompt = "\n".join(self.chathistory)
            prompt = instruct_template.replace(r"<|prompt|>",prompt)
        print(
            f'>>> The number tokens: {self.my_generate.count_token_numbers(prompt)} \n The limitation token is: {token_limition}')
        # print(f'>>> The final prompt is :{prompt}') #test the prompt output
        #llm request
        self.my_generate.image_payload['width'] = 512
        self.my_generate.image_payload['height'] = 512
        self.my_generate.image_payload['enable_hr'] = True
        self.my_generate.image_payload['steps'] = 40
        self.my_generate.state['temperature'] = random.choice([0.71, 0.72, 0.73])
        self.send_msg_websocket({"name":"chatreply","msg":"Generate Response"}, self.conversation_id)
        result_text, picture = self.my_generate.fetch_results(prompt,input_text)
        if result_text == None:
            result_text = "*Silent*"
        print(f'>>> The Response:\n {result_text}')
        if picture:
            # image_save = Image.open(io.BytesIO(base64.b64decode(picture)))
            # image_save.save('Sdimg.png')
            self.dynamic_picture = picture
        elif not picture:
            self.dynamic_picture = False
        result_text_cn = myTrans.translate_text("zh",result_text) if self.state["translate"] == True else result_text
        tts_text_extracted = self.extract_text(result_text_cn)
        
        #get tts text and process the emotion and code format
        try:
            emotion = self.sentiment_pipeline(tts_text_extracted)
            emotion_des = emotion[0]['label']
            if emotion_des == "none":
                self.speaker_tone = "affectionate"
                bulb.set_hsv(50, 100, 100)
            elif emotion_des == "happiness":
                self.speaker_tone = "cheerful"
                bulb.set_hsv(34, 100, 100)
            elif emotion_des == "anger":
                self.speaker_tone = "sad"
                bulb.set_hsv(12, 100, 100)
            elif emotion_des == "disgust":
                self.speaker_tone = "disgruntled"
                bulb.set_hsv(188, 100, 100)
            elif emotion_des == "fear":
                self.speaker_tone = "fearful"
                bulb.set_hsv(220, 100, 100)
            elif emotion_des == "like":
                self.speaker_tone = "gentle"
                bulb.set_hsv(313, 100, 100)
            elif emotion_des == "sadness":
                self.speaker_tone = "depressed"
                bulb.set_hsv(270, 100, 100)
            elif emotion_des == "surprise":
                self.speaker_tone = "cheerful"
                bulb.set_hsv(337, 100, 100)
        except Exception as e:
            print("Error get emotion: ", e)
            emotion_des = "none"

        print(f'The emotion is: {emotion_des}')
        avatar_url = 'data:image/png;base64,' + self.gen_avatar(self.my_generate,self.state['char_avatar'], emotion_des)

        self.ai_lastword = result_text
        self.chathistory.append(f'{self.ainame}: {result_text}')

        if self.is_chinese(tts_text_extracted):
            self.ai_speakers = self.ai_role.ai_speaker
        else:
            self.ai_speakers = self.ai_role.ai_speaker_en
        print(self.ai_speakers)

        self.G_avatar_url = avatar_url
        self.G_ai_text = result_text_cn
        self.G_voice_text = tts_text_extracted
        self.send_msg_websocket({"name":"chatreply","msg":"DONE"}, self.conversation_id)
        return self.G_ai_text,self.G_voice_text,self.ai_speakers,self.speaker_tone,self.G_avatar_url,self.conversation_id,self.dynamic_picture