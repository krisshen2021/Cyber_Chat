from modules.global_sets_async import (
    database,
    prompt_params,
    sentiment_anlyzer,
    getGlobalConfig,
    convert_to_webpbase64,
    logger,
    config_data,
)
import os, random, re, io, base64, copy, markdown, asyncio, httpx, copy
from fastapimode.airole_creator_uncensor_websocket import airole
from modules.TranslateAsync import AsyncTranslator
from fastapimode.Generator_websocket import CoreGenerator
from PIL import Image
from modules.payload_state import sd_payload, sd_payload_for_vram, room_state
from fastapimode.sys_path import project_root

dir_path = project_root


# Read prompt template
async def get_instr_temp_list():
    instr_temp_list = []
    prompt_keys_list = await getGlobalConfig("prompt_templates")
    for templates in prompt_keys_list.keys():
        instr_temp_list.append(templates)
    return instr_temp_list


myTrans = AsyncTranslator()
asyncio.run(myTrans.init())


def markdownText(text):
    Mtext = markdown.markdown(
        text,
        extensions=["pymdownx.superfences", "pymdownx.highlight", "pymdownx.magiclink"],
    )
    return Mtext


def create_userfaceprompt(facelooks: dict):
    if facelooks["hair_color"] != "":
        hair_style = f"{facelooks['hair_color']} {facelooks['hair_style']}"
    else:
        hair_style = f"{facelooks['hair_style']}"
    ends = ", " if facelooks["beard"] != "" else ""
    facelooks_prompt = f"(One {facelooks['gender']}:1.22), {facelooks['race']}, {facelooks['age']}, ({hair_style}:1.15), {facelooks['eye_color']}{ends}{facelooks['beard']}"
    facelooks_desc = f"One {facelooks['gender']}, {facelooks['race']}, {facelooks['age']}, {hair_style}, {facelooks['eye_color']}{ends}{facelooks['beard']}"
    return {"prompt": facelooks_prompt, "desc": facelooks_desc}


# the main room class
class ChatRoom_Uncensored:
    def __init__(
        self,
        user_sys_name: str = None,
        ai_role_name: str = None,
        username: str = None,
        usergender: str = None,
        user_facelooks: dict = None,
        conversation_id: str = None,
        windowRatio: float = None,
        send_msg_websocket: callable = None,
    ) -> None:
        self.send_msg_websocket = send_msg_websocket
        self.user_sys_name = user_sys_name
        self.ai_role_name = ai_role_name
        self.username = username
        self.usergender = usergender
        self.user_facelooks = create_userfaceprompt(user_facelooks)
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
        self._model = None
        self.bg_music = None
        self.ttskey = os.environ.get("SPEECH_KEY")
        self.sentiment_anlyzer = sentiment_anlyzer
        self.dynamic_picture = ""
        self.state = copy.deepcopy(room_state)
        self.ai_role = airole(
            roleselector=self.ai_role_name,
            username=self.username,
            usergender=self.usergender,
        )
        self.my_generate = CoreGenerator()
        self.initialization_start = False

    @property
    def model(self):
        return self._model

    # Set the model property
    @model.setter
    def model(self, value):
        self._model = value
        if hasattr(self, "my_generate") and isinstance(self.my_generate, CoreGenerator):
            self.my_generate.model = value

    async def initialize(self):
        self.initialization_start = True
        self.image_payload = copy.deepcopy(sd_payload)
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
        self.config_data = await getGlobalConfig("config_data")
        self.prompts_templates = await getGlobalConfig("prompt_templates")
        self.instr_temp_list = await get_instr_temp_list()
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
        await self.create_role_desc_msg()
        self.ai_lastword = ""
        self.G_ai_text = self.welcome_text
        self.G_voice_text = self.extract_text(self.G_ai_text)
        self.ai_speakers = self.ai_role.ai_speaker
        self.speaker_tone = "affectionate"

    async def create_custom_comp_data(self):
        self.state["custom_stop_string"] = self.state["custom_stop_string"] + [
            f"{self.username}:",
            f"{self.ainame}:",
        ]
        if self.ai_role.custom_comp_data is not False:
            self.state["temperature"] = (
                self.ai_role.custom_comp_data["temperature"]
                if "temperaure" in self.ai_role.custom_comp_data.keys()
                else self.state["temperature"]
            )
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
            self.state["smoothing_factor"] = self.ai_role.custom_comp_data[
                "smoothing_factor"
            ]

    async def create_chat_generator(self):
        await self.my_generate.async_init(
            state=self.state,
            image_payload=self.image_payload,
            send_msg_websocket=self.send_msg_websocket,
        )
        self.model_list = await self.my_generate.tabby_server.get_model_list()
        self.SD_model_list = await self.my_generate.tabby_server.get_sd_model_list()
        self.SD_vram_status = await self.my_generate.tabby_server.get_sd_vram_status()
        logger.info(f"SD server vram status: {self.SD_vram_status}")
        self.my_generate.image_payload.update(
            sd_payload_for_vram.get(self.SD_vram_status, {})
        )
        self.model = await self.my_generate.tabby_server.get_model()
        logger.info(f"Set model in My_Generate: {self.my_generate.model}")
        logger.info(f"Set model in tabby_server: {self.my_generate.tabby_server.model}")
        if self.ai_role.model_to_load is not False:
            await self.my_generate.tabby_server.unload_model()
            await self.my_generate.tabby_server.load_model(
                name=self.ai_role.model_to_load
            )
        if self.ai_role.prompt_to_load is not False:
            self.my_generate.state["prompt_template"] = self.ai_role.prompt_to_load
            self.my_generate.get_rephrase_template()

    async def create_envart(self):
        if self.state["ai_is_live_char"] is True:
            await self.send_msg_websocket(
                {"name": "initialization", "msg": "Preparing A.I Role"},
                self.conversation_id,
            )
            logger.info("Generate Character Background")
            emotion = await self.emotion_detector(self.first_message)
            logger.info(f"{self.ainame}'s Initial emotion: [{emotion}]")
            moment = await self.scenario_moment_detector(self.first_message)
            logger.info(f"{self.ainame}'s Initial moment: [{moment}]")
            self.bg_music = moment
            bgimg_base64 = await self.gen_bgImg(
                tabbyGen=self.my_generate,
                char_looks=self.state["char_looks"],
                bgImgstr=self.state["env_setting"],
                char_outfit=self.state["char_outfit"],
                task_flag="generate_background-ai",
                emotion=emotion,
            )
            self.bkImg = "data:image/webp;base64," + bgimg_base64
            await self.send_msg_websocket(
                {"name": "initialization", "msg": "Generate A.I Avatar"},
                self.conversation_id,
            )
            logger.info("Generate A.I Avatar")
            avatarimg_base64 = await self.gen_avatar(
                tabbyGen=self.my_generate,
                char_avatar=self.state["char_avatar"],
                emotion=emotion,
                char_outfit=self.state["char_outfit"],
                is_save=True,
                task_flag="generate_avatar-ai",
            )
            self.G_avatar_url = "data:image/webp;base64," + avatarimg_base64
        else:
            self.bkImg = None
            self.G_avatar_url = None
            self.bg_music = "Relaxing_Moment"

        await self.send_msg_websocket(
            {"name": "initialization", "msg": "Preparing Your Role"},
            self.conversation_id,
        )
        logger.info("Generate User Background")
        bgimg_base64 = await self.gen_bgImg(
            tabbyGen=self.my_generate,
            char_looks=self.user_facelooks["prompt"],
            bgImgstr=self.state["env_setting"],
            is_save=False,
            is_user=True,
            task_flag="generate_background-user",
        )
        self.user_bkImg = "data:image/webp;base64," + bgimg_base64

        await self.send_msg_websocket(
            {"name": "initialization", "msg": "Generate Your Avatar"},
            self.conversation_id,
        )
        userlooksprefix = ", Perfect face portrait, (close-up:0.8)"
        logger.info("Generate User Avatar")
        avatarimg_base64 = await self.gen_avatar(
            tabbyGen=self.my_generate,
            char_avatar=self.user_facelooks["prompt"] + userlooksprefix,
            emotion="smile",
            is_save=False,
            task_flag="generate_avatar-user",
        )
        self.G_userlooks_url = "data:image/webp;base64," + avatarimg_base64
        return True

    # assistant functions
    async def create_role_desc_msg(self):
        self.state["prompt_template"] = self.ai_role.prompt_to_load
        chat_template_name = self.state["prompt_template"].split("_")
        rephrase_template_name = chat_template_name[0] + "_Rephrase"
        self.rephrase_template = self.state["prompts_templates"][rephrase_template_name]
        self.char_desc_system = (
            self.ai_role.ai_system_role.replace(
                r"<|Current Chapter|>", self.ai_role.chapters[0]["name"]
            )
            .replace(r"<|User_Looks|>", self.user_facelooks["desc"])
            .replace(r"{{char}}", self.ainame)
            .replace(r"{{user}}", self.username)
        )

        self.first_message = self.ai_role.welcome_text_dec.replace(
            r"{{user}}", self.username
        ).replace(r"{{char}}", self.ainame)
        self.welcome_text = self.first_message
        self.prologue_intro = (
            self.ai_role.prologue.replace("\n", "<br>")
            .replace(r"{{user}}", f"<em>{self.username}</em>")
            .replace(r"{{char}}", f"<em>{self.ainame}</em>")
        )
        if self.state["language"] != "English":
            logger.info(f"Translating prologue to {self.state['language']}")
            await self.send_msg_websocket(
                {"name": "initialization", "msg": f"Translating prologue to {self.state['language']}..."},
                self.conversation_id,
            )
            self.prologue_intro = await myTrans.translate_text(
                self.state["language"], self.prologue_intro, self.rephrase_template
            )
            await self.send_msg_websocket(
                {"name": "initialization", "msg": f"Translating first message to {self.state['language']}..."},
                self.conversation_id,
            )
            
            self.welcome_text = await myTrans.translate_text(
                self.state["language"], self.first_message, self.rephrase_template
            )
            
        self.messages = f"{self.char_desc_system}{self.ainame}: {self.first_message}"

        if len(self.chathistory) == 0:
            self.chathistory.append(self.messages)
        else:
            self.chathistory[0] = self.messages

    @staticmethod
    def save_image_sync(image_data, file_path):
        image_save = Image.open(io.BytesIO(base64.b64decode(image_data)))
        image_save.save(file_path, format="WEBP", quality=75)

    async def save_image_async(self, image_data, file_path, file_name):
        if not os.path.exists(file_path):
            os.makedirs(file_path)
        file_path = os.path.join(file_path, file_name)
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            self.save_image_sync,
            image_data,
            file_path,
        )

    async def gen_bgImg(
        self,
        tabbyGen,
        char_looks,
        bgImgstr,
        is_save=True,
        is_user=False,
        char_outfit=None,
        task_flag=None,
        emotion="",
    ):
        # logger.info(f">>>The window ratio[w/h]: {self.windowRatio}")
        tabbyGen.image_payload["enable_hr"] = True

        if not is_user:
            if char_outfit is not None:
                char_looks = f"{char_looks},{char_outfit['normal']}"
            # tabbyGen.image_payload["hr_second_pass_steps"] = 4
            tabbyGen.image_payload["hr_scale"] = 1.5
            tabbyGen.image_payload["width"] = 1024 if self.windowRatio >= 1 else 512
            tabbyGen.image_payload["height"] = int(
                tabbyGen.image_payload["width"] / self.windowRatio
            )
            # tabbyGen.image_payload["steps"] = 4
            portraitprefix = "(half body portrait:1.27), looking at the viewer"
            # logger.info(
            #     f"{tabbyGen.image_payload['width']} / {tabbyGen.image_payload['height']}"
            # )
        elif is_user:
            # tabbyGen.image_payload["hr_second_pass_steps"] = 4
            tabbyGen.image_payload["hr_scale"] = 1.5
            tabbyGen.image_payload["width"] = 768 if self.windowRatio >= 1 else 512
            tabbyGen.image_payload["height"] = (
                512
                if self.windowRatio >= 1
                else int((tabbyGen.image_payload["width"] / self.windowRatio) * 0.5)
            )
            # tabbyGen.image_payload["steps"] = 4
            portraitprefix = "Upper body portrait, looking at the viewer"
            # logger.info(
            #     f"{tabbyGen.image_payload['width']} / {tabbyGen.image_payload['height']}"
            # )

        if emotion != "":
            emotion = f"({emotion} expression:1.24), "
        bkImg = await tabbyGen.generate_image(
            prompt_prefix=tabbyGen.prmopt_fixed_prefix,
            char_looks=char_looks + ", " + emotion + portraitprefix,
            env_setting=bgImgstr,
            prompt_suffix=tabbyGen.prmopt_fixed_suffix,
            task_flag=task_flag,
        )
        if is_save:
            img_path = os.path.join(
                dir_path, "static", "images", "avatar", self.ai_role_name
            )
            await self.save_image_async(bkImg, img_path, "background.webp")

        return await convert_to_webpbase64(bkImg, quality=85)

    async def gen_avatar(
        self,
        tabbyGen,
        char_avatar,
        emotion: str = "",
        char_outfit: dict = {},
        task_flag=None,
        is_save=True,
    ):
        env_setting = ",".join(
            (self.state.get("env_setting", "").split(",") + ["", ""])[:2]
        )
        if not env_setting.strip(","):
            env_setting = "plain background"
        char_outfit_setting = ",".join(
            (char_outfit.get("normal", "").split(",") + ["", ""])[:2]
        )
        if not char_outfit_setting.strip(","):
            char_outfit_setting = ""
        tabbyGen.image_payload["enable_hr"] = False
        tabbyGen.image_payload["hr_scale"] = 1.2
        # tabbyGen.image_payload["hr_second_pass_steps"] = 4
        tabbyGen.image_payload["width"] = 512
        tabbyGen.image_payload["height"] = 512
        # tabbyGen.image_payload["steps"] = 4
        char_avatar = char_avatar.replace("<|emotion|>", emotion)
        avatarImg = await tabbyGen.generate_image(
            prompt_prefix=tabbyGen.prmopt_fixed_prefix,
            char_looks=char_avatar + ", " + char_outfit_setting,
            env_setting=env_setting,
            prompt_suffix=tabbyGen.prmopt_fixed_suffix,
            task_flag=task_flag,
        )

        if is_save:
            img_path = os.path.join(
                dir_path, "static", "images", "avatar", self.ai_role_name
            )
            await self.save_image_async(avatarImg, img_path, "none.webp")

        return await convert_to_webpbase64(avatarImg)

    async def emotion_detector(self, input_msg: str, fastmode: bool = False):
        if not fastmode:
            config_data = await getGlobalConfig("config_data")
            face_expression_prompt = prompt_params["face_expression_prompt"]
            face_expression_words_list = prompt_params["face_expression_words_list"]
            user_prompt = f"User Provided Context:\n<context>{self.ainame}: {input_msg}</context><for_char>{self.ainame}</for_char><emotion_type>{face_expression_words_list}</emotion_type>\nOutput:"
            if config_data["using_remoteapi"]:
                prompt = face_expression_prompt + "\n" + user_prompt
            else:
                prompt = self.rephrase_template.replace(
                    "<|system_prompt|>", face_expression_prompt
                ).replace("<|user_prompt|>", user_prompt)
            payloads = {
                "prompt": prompt,
                "max_tokens": 20,
                "temperature": 0.5,
                "stream": False,
                "model": self.model,
            }
            # logger.info(f"Emotion Detector Payload: {prompt}")
            emotion_des = await self.my_generate.tabby_server.pure_inference(
                payloads=payloads
            )
        else:
            emotion_des = await self.sentiment_anlyzer.get_sentiment(input_msg)
            positive_emotions = ["joy", "surprise", "love", "fun"]
            negative_emotions = ["sadness", "anger", "fear", "disgust"]
            emotion_des = (
                str(emotion_des)
                .replace("POSITIVE", random.choice(positive_emotions))
                .replace("NEGATIVE", random.choice(negative_emotions))
            )
        return emotion_des

    async def scenario_moment_detector(self, input_msg: str):
        config_data = await getGlobalConfig("config_data")
        scenario_moment_prompt = prompt_params["scenario_moment_prompt"]
        url = config_data["openai_api_chat_base"] + "/music/playlist"
        async with httpx.AsyncClient(timeout=300) as client:
            response = await client.get(url=url)
            response = response.json()
            moments_list = [item["title"] for item in response["playlist"]]
            moments_prompt = ", ".join(moments_list)
            user_prompt = f"User Provided Context:\n<context>{self.ainame}: {input_msg}</context><for_char>{self.ainame}</for_char><moment_type>{moments_prompt}</moment_type>\nOutput:"

        if config_data["using_remoteapi"]:
            prompt = scenario_moment_prompt + "\n" + user_prompt
        else:
            prompt = self.rephrase_template.replace(
                "<|system_prompt|>", scenario_moment_prompt
            ).replace("<|user_prompt|>", user_prompt)

        payloads = {
            "prompt": prompt,
            "max_tokens": 20,
            "temperature": 0.5,
            "stream": False,
            "model": self.model,
        }
        # logger.info(f"Scenario Moment Detector Payload: {prompt}")
        scenario_moment = await self.my_generate.tabby_server.pure_inference(
            payloads=payloads
        )
        return scenario_moment.strip()

    async def sentence_completion(self, message: dict):
        chat_history = copy.deepcopy(self.chathistory)
        system_intro = chat_history.pop(0)
        system_intro = re.sub(
            re.escape(f"{self.ainame}: {self.first_message}"), "", system_intro
        )
        chat_history.insert(0, f"{self.ainame}: {self.first_message}")
        if len(chat_history) >= 5:
            chat_history = chat_history[-5:]  # Only keep the last 5 messages
        chat_history = "\n".join(chat_history)
        user_prompt = f"User provided context:<CONTEXT>{system_intro}\n{chat_history}</CONTEXT><PREFIX>{self.username}: {message['prefix']}</PREFIX>{{BLOCK FOR COMPLETION}}<SUFFIX>{message['suffix']}</SUFFIX>"
        system_prompt = prompt_params["sentenceCompletion_prompt"]
        if config_data["using_remoteapi"]:
            prompt = system_prompt + "\n" + user_prompt
        else:
            prompt = self.rephrase_template.replace(
                "<|system_prompt|>", system_prompt
            ).replace("<|user_prompt|>", user_prompt)
        payloads = {
            "prompt": prompt,
            "max_tokens": 120,
            "temperature": 0.7,
            "stream": False,
            "model": self.model,
        }
        logger.info(f"Sentence Completion Processing >>>")
        sentence_result = await self.my_generate.tabby_server.pure_inference(
            payloads=payloads
        )
        if sentence_result is not None:
            return (
                sentence_result.rstrip()
                .replace("[SPACE]", " ")
                .replace("[NOSPACE]", "")
            )
        else:
            return "No response from server"

    # Main Server Reply Blocks
    async def server_reply(self, usermsg):
        input_text = (
            await myTrans.translate_text("English", usermsg, self.rephrase_template)
            if self.state["language"] != "English"
            else usermsg
        )
        self.chathistory.append(f"{self.username}: {input_text}")
        # logger.info(f"Reply base on input text:\n{self.username}:{input_text}")
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
        # llm request
        self.my_generate.image_payload["width"] = 512 if self.windowRatio <= 1 else 768
        self.my_generate.image_payload["height"] = 768 if self.windowRatio <= 1 else 512
        self.my_generate.image_payload["enable_hr"] = True
        # self.my_generate.image_payload["steps"] = 20
        self.my_generate.image_payload["hr_scale"] = 1.5
        # self.my_generate.state["temperature"] = random.choice([0.75, 0.82, 0.93])
        await self.send_msg_websocket(
            {"name": "chatreply", "msg": "Generate Response"}, self.conversation_id
        )
        result_text, picture = await self.my_generate.fetch_results(
            prompt, input_text, self.iscreatedynimage
        )
        if result_text is None:
            result_text = "*Silent*"

        # logger.info(f"Raw Reply Content:\n {result_text}")

        if picture:
            picture = await convert_to_webpbase64(picture)
            self.dynamic_picture = "data:image/webp;base64," + picture
        elif not picture:
            self.dynamic_picture = False

        result_text_cn = (
            await myTrans.translate_text(
                self.state["language"], result_text, self.rephrase_template
            )
            if self.state["language"] != "English"
            else result_text
        )

        tts_text_extracted = (
            self.extract_text(result_text_cn).replace(r"\\n", " ").strip()
        )
        # logger.info(f"Extracted TTS:\n {tts_text_extracted}")
        # get tts text and process the emotion and code format
        try:
            if result_text != "*Silent*":
                emotion_des = await self.emotion_detector(result_text, fastmode=False)
                logger.info(f"{self.ainame}'s current emotion: [{emotion_des}]")
            else:
                emotion_des = "none"
        except Exception as e:
            logger.info("Error get emotion: ", e)
            emotion_des = "none"

        if self.state["ai_is_live_char"] is True:
            avatarimg_base64 = await self.gen_avatar(
                tabbyGen=self.my_generate,
                char_avatar=self.state["char_avatar"],
                emotion=emotion_des,
                char_outfit=self.state["char_outfit"],
                is_save=True,
                task_flag="generate_live-CharacterAvatar",
            )
            avatar_url = "data:image/webp;base64," + avatarimg_base64
        else:
            avatar_url = None

        self.ai_lastword = result_text
        self.chathistory.append(f"{self.ainame}: {result_text}")
        # logger.info(f">>>chat history in server reply: \n{self.chathistory}")

        if self.is_chinese(tts_text_extracted):
            self.ai_speakers = self.ai_role.ai_speaker
        else:
            self.ai_speakers = self.ai_role.ai_speaker_en
        logger.info(self.ai_speakers)
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
    @staticmethod
    def is_chinese(text):
        clean_text = re.sub(r"[^\u4e00-\u9fa5]", "", text)
        return len(clean_text) > 0

    @staticmethod
    def extract_text(text):
        clean_text = re.sub(r"\*[^*]*\*", "", text)
        clean_text = re.sub(r"```(.*?)```", "", clean_text, flags=re.DOTALL)
        return clean_text.strip()

    def create_instruct_template(self, ainame, username):
        if self.config_data["using_remoteapi"] is not True:
            template = self.prompts_templates[self.state["prompt_template"]]
        else:
            if self.ai_role.match_words_cata == "SFW":
                template = self.prompts_templates["Remote_RP_SFW"]
            elif self.ai_role.match_words_cata == "NSFW":
                template = self.prompts_templates["Remote_RP_NSFW"]
        pt = template.replace(r"<|character|>", ainame).replace(r"<|user|>", username)
        self.my_generate.get_rephrase_template()
        return pt

    # Regeneration reply
    async def regen_msg(self, user_msg):

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
                # logger.info(f">>> chat history after loaded is \n {self.chathistory}")
                return self.loadedhistory
            else:
                return False
        if operation == "delete":
            delete_result = database.delete_chat_records(
                username=self.user_sys_name, character=self.ai_role_name
            )
            return delete_result
