from modules.global_sets_async import database, sentiment_pipeline, bulb, logging
import os, random, re, io, base64, yaml, copy, markdown, asyncio, aiofiles
from fastapimode.airole_creator_uncensor_websocket import airole
from modules.TranslateAsync import AsyncTranslator
from fastapimode.Generator_websocket import CoreGenerator
from PIL import Image
from modules.payload_state import sd_payload, room_state
from fastapimode.sys_path import project_root


# dir_path = os.path.dirname(os.path.realpath(__file__))
dir_path = project_root
image_payload = sd_payload
state = room_state

# Read prompt template
async def get_instr_temp_list():
    prompt_template_path = os.path.join(
    dir_path, "config", "prompts", "prompt_template.yaml"
    )
    async with aiofiles.open(prompt_template_path, mode="r") as f:
        contents = await f.read()
        prompts_templates = yaml.safe_load(contents)
        instr_temp_list = []
        for templates in prompts_templates.keys():
            instr_temp_list.append(templates)
        return prompts_templates, instr_temp_list

myTrans = AsyncTranslator()


def markdownText(text):
    Mtext = markdown.markdown(
        text,
        extensions=["pymdownx.superfences", "pymdownx.highlight", "pymdownx.magiclink"],
    )
    return Mtext


# the main room class
class chatRoom_unsensor:
    def __init__(
        self,
        user_sys_name: str = None,
        ai_role_name: str = None,
        username: str = None,
        usergender: str = None,
        user_facelooks: str = None,
        conversation_id: str = None,
        windowRatio: float = None,
        send_msg_websocket: callable = None,
    ) -> None:
        self.send_msg_websocket = send_msg_websocket
        self.user_sys_name = user_sys_name
        self.ai_role_name = ai_role_name
        self.username = username
        self.usergender = usergender
        self.user_facelooks = user_facelooks
        self.windowRatio = windowRatio
        self.iscreatedynimage = False
        self.conversation_id = conversation_id
        self.ai_role = None
        self.messages = ""
        self.chathistory = []
        self.ai_lastword = ""
        self.G_avatar_url = ""
        self.G_ai_text = ""
        self.G_voice_text = ""
        self.ai_speakers = ""
        self.speaker_tone = ""
        self.ttskey = os.environ.get("SPEECH_KEY")
        self.sentiment_pipeline = sentiment_pipeline
        self.dynamic_picture = ""
        self.state = copy.deepcopy(state)
        self.ai_role = airole(
            roleselector=self.ai_role_name,
            username=self.username,
            usergender=self.usergender,
        )
        self.my_generate = CoreGenerator()
        self.initialization_start = False
    

    async def initialize(self):
        self.initialization_start = True
        await self.serialize_data()
        await self.send_msg_websocket(
            {"name": "initialization", "msg": "DONE"}, self.conversation_id
        )
        self.initialization_start = False
        return True
    
    async def serialize_data(self):
        # ai role data
        await self.ai_role.async_init()
        # prepare state data
        await self.preparation()
        # Other stats value data
        await self.start_stats()
        # customize completions data
        await self.create_custom_comp_data()
        # char settings
        await self.create_chat_generator()
        # char enviroment arts
        await self.create_envart()
        
    async def preparation(self):
        self.prompts_templates, self.instr_temp_list = await get_instr_temp_list()
        self.iscreatedynimage = self.ai_role.generate_dynamic_picture
        self.state["prompts_templates"] = self.prompts_templates
        self.state["conversation_id"] = self.conversation_id
        self.state["char_looks"] = self.ai_role.char_looks
        self.state["env_setting"] = self.ai_role.backgroundImg
        self.state["char_avatar"] = self.ai_role.char_avatar
        self.state["generate_dynamic_picture"] = self.ai_role.generate_dynamic_picture
        self.state["match_words_cata"] = self.ai_role.match_words_cata
        self.state["char_outfit"] = self.ai_role.char_outfit
        
    async def start_stats(self):
        self.chathistory.clear()
        self.messages = ""
        self.state["user_name"] = self.username
        self.state["char_name"] = self.ai_role.ai_role_name
        self.ainame = self.ai_role.ai_role_name
        await self.create_role_desc_msg(self.state["translate"])
        self.ai_lastword = ""
        self.G_ai_text = self.welcome_text
        self.G_voice_text = self.extract_text(self.G_ai_text)
        self.ai_speakers = self.ai_role.ai_speaker
        self.speaker_tone = "affectionate"
        
    async def create_custom_comp_data(self):
        self.state["custom_stop_string"] = state["custom_stop_string"] + [
            f"{self.username}:",
            f"{self.ainame}:",
            "###",
        ]
        if self.ai_role.custom_comp_data is not False:
            self.state["max_tokens"] = self.ai_role.custom_comp_data["max_tokens"]
            self.state["top_k"] = self.ai_role.custom_comp_data["top_k"]
            self.state["top_p"] = self.ai_role.custom_comp_data["top_p"]
            self.state["min_p"] = self.ai_role.custom_comp_data["min_p"]
            self.state["tfs"] = self.ai_role.custom_comp_data["tfs"]
            self.state["frequency_penalty"] = self.ai_role.custom_comp_data[
                "frequency_penalty"
            ]
            self.state["presence_penalty"] = self.ai_role.custom_comp_data[
                "presence_penalty"
            ]
            self.state["repetition_penalty"] = self.ai_role.custom_comp_data[
                "repetition_penalty"
            ]
            self.state["mirostat_mode"] = self.ai_role.custom_comp_data["mirostat_mode"]
            self.state["mirostat_tau"] = self.ai_role.custom_comp_data["mirostat_tau"]
            self.state["mirostat_eta"] = self.ai_role.custom_comp_data["mirostat_eta"]
            self.state["temperature_last"] = self.ai_role.custom_comp_data[
                "temperature_last"
            ]
            self.state["smoothing_factor"] = self.ai_role.custom_comp_data["smoothing_factor"]
    
        
    async def create_chat_generator(self):
        await self.my_generate.async_init(
            state=self.state,
            image_payload=image_payload,
            send_msg_websocket=self.send_msg_websocket,
        )
        self.model_list = await self.my_generate.tabby_server.get_model_list()
        self.SD_model_list = await self.my_generate.tabby_server.get_sd_model_list()
        self.current_model = await self.my_generate.tabby_server.get_model()
        if self.ai_role.model_to_load is not False:
            await self.my_generate.tabby_server.unload_model()
            await self.my_generate.tabby_server.load_model(
                name=self.ai_role.model_to_load
            )
        if self.ai_role.prompt_to_load is not False:
            self.state["prompt_template"] = self.ai_role.prompt_to_load
            self.my_generate.state["prompt_template"] = self.ai_role.prompt_to_load
            self.my_generate.get_rephrase_template()
        
    async def create_envart(self):
        await self.send_msg_websocket(
            {"name": "initialization", "msg": "Preparing A.I Role..."},
            self.conversation_id,
        )
        bgimg_base64 = await self.gen_bgImg(
            self.my_generate, self.state["char_looks"], self.state["env_setting"], char_outfit=self.state["char_outfit"]
        )
        self.bkImg = "data:image/png;base64," + bgimg_base64
        await self.send_msg_websocket(
            {"name": "initialization", "msg": "Preparing Your Role..."},
            self.conversation_id,
        )
        bgimg_base64 = await self.gen_bgImg(
            self.my_generate,
            self.user_facelooks,
            self.state["env_setting"],
            False,
            True,
        )
        self.user_bkImg = "data:image/png;base64," + bgimg_base64

        await self.send_msg_websocket(
            {"name": "initialization", "msg": "Generate A.I Avatar ..."},
            self.conversation_id,
        )
        avatarimg_base64 = await self.gen_avatar(
            self.my_generate, self.state["char_avatar"], "smile", True
        )
        self.G_avatar_url = "data:image/png;base64," + avatarimg_base64
        await self.send_msg_websocket(
            {"name": "initialization", "msg": "Generate Your Avatar..."},
            self.conversation_id,
        )
        userlooksprefix = ", Perfect face portrait, (close-up:0.8)"
        avatarimg_base64 = await self.gen_avatar(
            self.my_generate, self.user_facelooks + userlooksprefix, "smile", False
        )
        self.G_userlooks_url = "data:image/png;base64," + avatarimg_base64
        return True
    
    # assistant functions
    async def create_role_desc_msg(self, istranslated: bool = True):
        self.char_desc_system = (
            self.ai_role.ai_system_role.replace(
                r"<|Current Chapter|>", self.ai_role.chapters[0]["name"]
            )
            .replace(r"<|User_Looks|>", self.user_facelooks)
            .replace(r"{{char}}", self.ainame)
            .replace(r"{{user}}", self.username)
        )

        self.first_message = self.ai_role.welcome_text_dec.replace(
            r"{{user}}", self.username
        ).replace(r"{{char}}", self.ainame)
        self.welcome_text = (
            await myTrans.translate_text("zh", self.first_message)
            if istranslated
            else self.first_message
        )
        self.messages = f"{self.char_desc_system}{self.ainame}: {self.first_message}"

        if len(self.chathistory) == 0:
            self.chathistory.append(self.messages)
        else:
            self.chathistory[0] = self.messages


    @staticmethod
    def save_image_sync(image_data, file_path):
        image_save = Image.open(io.BytesIO(base64.b64decode(image_data)))
        image_save.save(file_path)

    async def save_image_async(self, image_data, file_path):
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,  # 使用默认的线程池
            self.save_image_sync,
            image_data,
            file_path,
        )

    async def gen_bgImg(
        self, tabbyGen, char_looks, bgImgstr, is_save=True, is_user=False, char_outfit=None
    ):
        logging.info(f">>>The window ratio[w/h]: {self.windowRatio}")
        tabbyGen.image_payload["enable_hr"] = True

        if not is_user:
            if char_outfit is not None:
                char_looks = f"{char_looks},{char_outfit['normal']}"
                
            tabbyGen.image_payload["hr_scale"] = 1.5
            tabbyGen.image_payload["width"] = 1024 if self.windowRatio >= 1 else 512
            tabbyGen.image_payload["height"] = int(
                tabbyGen.image_payload["width"] / self.windowRatio
            )
            tabbyGen.image_payload["steps"] = 20
            portraitprefix = ", body portrait, looking directly at the camera, front view"
            logging.info(
                f"{tabbyGen.image_payload['width']} / {tabbyGen.image_payload['height']}"
            )
            logging.info(">>>Generate Character Background\n")
        elif is_user:
            tabbyGen.image_payload["hr_scale"] = 1.25
            tabbyGen.image_payload["width"] = 768 if self.windowRatio >= 1 else 512
            tabbyGen.image_payload["height"] = (
                512
                if self.windowRatio >= 1
                else int((tabbyGen.image_payload["width"] / self.windowRatio) * 0.5)
            )
            tabbyGen.image_payload["steps"] = 20
            portraitprefix = ", Upper body portrait, front view"
            logging.info(
                f"{tabbyGen.image_payload['width']} / {tabbyGen.image_payload['height']}"
            )
            logging.info(">>>Generate User Background\n")

        bkImg = await tabbyGen.generate_image(
            prompt_prefix=tabbyGen.prmopt_fixed_prefix,
            char_looks=f'({char_looks})' + portraitprefix,
            env_setting=bgImgstr,
            prompt_suffix=tabbyGen.prmopt_fixed_suffix,
        )
        if is_save:
            img_path = os.path.join(
                dir_path,
                "static",
                "images",
                "avatar",
                self.ai_role_name,
                "background.png",
            )
            await self.save_image_async(bkImg, img_path)

        return bkImg

    async def gen_avatar(self, tabbyGen, char_avatar, emotion, is_save=True):
        tabbyGen.image_payload["enable_hr"] = True
        tabbyGen.image_payload["hr_scale"] = 1.25
        tabbyGen.image_payload["width"] = 256
        tabbyGen.image_payload["height"] = 256
        tabbyGen.image_payload["steps"] = 15
        char_avatar = char_avatar.replace("<|emotion|>", emotion)
        logging.info(">>>Generate avatar\n")
        avatarImg = await tabbyGen.generate_image(
            prompt_prefix=tabbyGen.prmopt_fixed_prefix,
            char_looks=char_avatar,
            env_setting=self.state["env_setting"],
            prompt_suffix=tabbyGen.prmopt_fixed_suffix,
        )

        if is_save:
            img_path = os.path.join(
                dir_path,
                "static",
                "images",
                "avatar",
                self.ai_role_name,
                "none.png",
            )
            await self.save_image_async(avatarImg, img_path)

        return avatarImg
    
    
    # Main Server Reply Blocks
    async def server_reply(self, usermsg):
        input_text = (
            await myTrans.translate_text("en", usermsg)
            if self.state["translate"] is True
            else usermsg
        )
        self.chathistory.append(f"{self.username}: {input_text}")
        logging.info(">>> Generate Response:")
        instruct_template = self.create_instruct_template(self.ainame, self.username)
        prompt = "\n".join(self.chathistory)
        prompt = instruct_template.replace(r"<|prompt|>", prompt)
        token_limition = int(
            self.my_generate.tabby_server.model_load_data["max_seq_len"]
            - self.state["max_tokens"]
            - 200
        )
        while self.my_generate.count_token_numbers(prompt) >= token_limition:
            for i in range(2):
                self.chathistory.pop(1)
            prompt = "\n".join(self.chathistory)
            prompt = instruct_template.replace(r"<|prompt|>", prompt)
        logging.info(
            f">>> The number tokens: {self.my_generate.count_token_numbers(prompt)} \n The limitation token is: {token_limition}"
        )
        # logging.info(f'>>> The final prompt is :{prompt}') #test the prompt output
        # llm request
        self.my_generate.image_payload["width"] = 512 if self.windowRatio <= 1 else 768
        self.my_generate.image_payload["height"] = 768 if self.windowRatio <= 1 else 512
        self.my_generate.image_payload["enable_hr"] = True
        self.my_generate.image_payload["steps"] = 20
        self.my_generate.image_payload["hr_scale"] = 1.5
        self.my_generate.state["temperature"] = random.choice([0.75, 0.82, 0.93])
        await self.send_msg_websocket(
            {"name": "chatreply", "msg": "Generate Response"}, self.conversation_id
        )
        result_text, picture = await self.my_generate.fetch_results(
            prompt, input_text, self.iscreatedynimage
        )
        if result_text is None:
            result_text = "*Silent*"
        logging.info(f">>> The Response:\n {result_text}")
        if picture:
            self.dynamic_picture = "data:image/png;base64," + picture
        elif not picture:
            self.dynamic_picture = False
        result_text_cn = (
            await myTrans.translate_text("zh", result_text)
            if self.state["translate"] is True
            else result_text
        )

        tts_text_extracted = self.extract_text(result_text_cn)

        # get tts text and process the emotion and code format
        try:
            if tts_text_extracted != "":
                sentiment_text = (
                    tts_text_extracted
                    if self.state["translate"] is True
                    else await myTrans.translate_text("zh", tts_text_extracted)
                )
                emotion = await self.async_sentiment_analysis(sentiment_text)
                emotion_des = emotion[0]["label"]
            else:
                emotion_des = "none"

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
            logging.info("Error get emotion: ", e)
            emotion_des = "none"
        logging.info(f"The emotion is: {emotion_des}")

        avatarimg_base64 = await self.gen_avatar(
            self.my_generate, self.state["char_avatar"], emotion_des
        )
        avatar_url = "data:image/png;base64," + avatarimg_base64

        self.ai_lastword = result_text
        self.chathistory.append(f"{self.ainame}: {result_text}")
        # logging.info(f">>>chat history in server reply: \n{self.chathistory}")

        if self.is_chinese(tts_text_extracted):
            self.ai_speakers = self.ai_role.ai_speaker
        else:
            self.ai_speakers = self.ai_role.ai_speaker_en
        logging.info(self.ai_speakers)
        self.G_avatar_url = avatar_url
        self.G_ai_text = result_text_cn
        self.G_voice_text = tts_text_extracted
        await self.send_msg_websocket(
            {"name": "chatreply", "msg": "DONE"}, self.conversation_id
        )
        return (
            self.G_ai_text,
            self.G_voice_text,
            self.ai_speakers,
            self.speaker_tone,
            self.G_avatar_url,
            self.dynamic_picture,
        )
    
    # Assistant functions for server reply function
    async def async_sentiment_analysis(self, text):
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, lambda: self.sentiment_pipeline(text))
        return result
    
    @staticmethod
    def is_chinese(text):
        clean_text = re.sub(r"[^\u4e00-\u9fa5]", "", text)
        return len(clean_text) > 0
    
    @staticmethod
    def extract_text(text):
        clean_text = re.sub(r"\*[^*]*\*", "", text)
        clean_text = re.sub(r"```(.*?)```", "", clean_text, flags=re.DOTALL)
        return clean_text

    def create_instruct_template(self, ainame, username):
        template = self.prompts_templates[self.state["prompt_template"]]
        pt = template.replace(r"<|character|>", ainame).replace(r"<|user|>", username)
        self.my_generate.get_rephrase_template()
        return pt
    
    # Regeneration reply 
    async def regen_msg(self, user_msg):
        # for i in range(2):
        #     del self.chathistory[-1]
        self.chathistory = self.chathistory[:-2]
        self.my_generate.last_context = self.my_generate.last_context[:-2]
        (
            ai_text,
            voice_text,
            speaker,
            speak_tone,
            avatar_url,
            dynamic_picture,
        ) = await self.server_reply(user_msg)
        return (
            ai_text,
            voice_text,
            speaker,
            speak_tone,
            avatar_url,
            dynamic_picture,
        )  
        
    # Chat history operations
    def chat_history_op(self, operation: str):
        if operation == "save":
            char = self.chathistory[-1].split(": ", maxsplit=1)
            if len(self.chathistory) > 1 and char[0] == self.ainame:
                db_chat_history = copy.deepcopy(self.chathistory)
                db_chat_history.pop(0)
                chat_record = []
                for record in db_chat_history:
                    chatitem = record.split(": ", maxsplit=1)
                    if chatitem[0] == self.username:
                        chatitem[0] = r"{{user}}"
                    else:
                        chatitem[0] = r"{{char}}"
                    chatitem[1] = (
                        chatitem[1]
                        .replace(self.username, r"{{user}}")
                        .replace(self.ainame, r"{{char}}")
                    )
                    chatitem_dict = {"role": chatitem[0], "msg": chatitem[1]}
                    chat_record.append(chatitem_dict)
                save_result = database.save_chat_records(
                    username=self.user_sys_name,
                    character=self.ai_role_name,
                    chat_data=chat_record,
                )
                return save_result
            else:
                return False

        if operation == "load":
            user_chat_history = database.get_chat_records(
                username=self.user_sys_name, character=self.ai_role_name
            )
            if user_chat_history:
                self.chathistory[:] = self.chathistory[:1]
                self.loadedhistory = []
                history_content = user_chat_history[0]["content"]
                for msg in history_content:
                    msgs = (
                        msg["msg"]
                        .replace(r"{{user}}", self.username)
                        .replace(r"{{char}}", self.ainame)
                    )
                    msgsMarkdown = markdownText(msgs)
                    self.loadedhistory.append(
                        {
                            "role": "user" if msg["role"] == r"{{user}}" else "char",
                            "msg": msgsMarkdown,
                        }
                    )
                    role = (
                        msg["role"]
                        .replace(r"{{user}}", self.username)
                        .replace(r"{{char}}", self.ainame)
                    )
                    self.chathistory.append(f"{role}: {msgs}")
                # logging.info(f">>> chat history after loaded is \n {self.chathistory}")
                return self.loadedhistory
            else:
                return False
        if operation == "delete":
            delete_result = database.delete_chat_records(
                username=self.user_sys_name, character=self.ai_role_name
            )
            return delete_result
        
