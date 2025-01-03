from fastapimode.sys_path import project_root
from fastapimode.tabby_fastapi_websocket import tabby_fastapi
import os, tiktoken, yaml, httpx, aiofiles, asyncio, re, httpx, copy, json
from datetime import datetime
from modules.global_sets_async import (
    logger,
    config_data,
    prompt_params,
    getGlobalConfig,
    convert_to_webpbase64,
    init_memory,
)
from modules.payload_state import completions_data

dir_path = project_root


# Load Words dictionary
async def load_vocabulary(file_path):
    vocabs_file_path = os.path.join(
        dir_path, "config", "match_words", file_path + ".yaml"
    )
    async with aiofiles.open(vocabs_file_path, "r") as file:
        content = await file.read()
        data = yaml.safe_load(content)
        vocabs = [word.lower() for word in data["words"]]
        result = [word.lower() for word in data["results"]]
        lora = data["lora"]
        summary_prompt = data["summary_prompt"]
    return vocabs, result, lora, summary_prompt


def contains_vocabulary(input_string, vocabulary):
    input_string = input_string.lower()
    for word in vocabulary:
        if word in input_string:
            # if re.search(r'\b' + re.escape(word) + r'\b', input_string): 备份，功能是完全匹配词的边界，如果应用的话，ass和asshole就不匹配了
            return True, word
    return False, None


class CoreGenerator:
    """
    Message Functional Generator,

    Functions:

    generate inference result,

    detect trigger words,

    create images
    """

    def __init__(self) -> None:
        self.api_key = config_data["api_key"]
        self.admin_key = config_data["admin_key"]
        self.completions_data = completions_data
        self.iscreatedynimage = True
        self._model = None

    @property
    def model(self):
        return self._model

    @model.setter
    def model(self, value):
        self._model = value
        if hasattr(self, "tabby_server") and isinstance(
            self.tabby_server, tabby_fastapi
        ):
            self.tabby_server.model = value

    async def async_init(
        self, state: dict, image_payload: dict, send_msg_websocket: callable = None
    ):
        self.send_msg_websocket = send_msg_websocket
        self.state = state
        self.ai_is_memory_mode = state["ai_is_memory_mode"]
        logger.info(f"is memory mode: {self.ai_is_memory_mode}")
        self.pattern_task = re.compile(r"<Task>(.*?)</Task>", re.DOTALL)
        self.pattern_plot = re.compile(
            r"<Plot_of_the_RolePlay>(.*?)</Plot_of_the_RolePlay>", re.DOTALL
        )
        self.pattern_firstword = re.compile(
            rf"({re.escape(self.state['char_name'])}:[\s\S]*?)(?=\n\w+:|$)", re.DOTALL
        )
        self.express_words = prompt_params["face_expression_words_list"]
        self.char_outfit = self.state["char_outfit"]
        self.conversation_id = self.state["conversation_id"]
        self.image_payload = image_payload
        # context window created
        self.last_context = []
        self.tabby_server = tabby_fastapi(
            url=self.state["openai_api_chat_base"],
            api_key=self.api_key,
            admin_key=self.admin_key,
            conversation_id=self.conversation_id,
            send_msg_websocket=self.send_msg_websocket,
        )
        self.vocabulary, self.resultslist, self.lora, self.summary_prompt = (
            await load_vocabulary(self.state["match_words_cata"])
        )
        self.restruct_prompt = prompt_params["restruct_prompt"]
        self.prmopt_fixed_prefix = prompt_params["prmopt_fixed_prefix"]
        self.prmopt_fixed_suffix = prompt_params["prmopt_fixed_suffix"]
        self.nagetive_prompt = prompt_params["nagetive_prompt"]
        self.restruct_prompt = self.restruct_prompt.replace(
            "<|default_bg|>", self.state["env_setting"]
        )
        if self.ai_is_memory_mode is True:
            self.cyberchat_memory = await init_memory()
        else:
            self.cyberchat_memory = None

    def get_rephrase_template(self):
        chat_template_name = self.state["prompt_template"].split("_")
        rephrase_template_name = chat_template_name[0] + "_Rephrase"
        self.rephrase_template = self.state["prompts_templates"][rephrase_template_name]

    def update_completion_data(
        self,
        system_prompt: str,
        temperature=None,
        stream: bool = False,
        max_tokens=None,
        using_remoteapi: bool = None,
    ):
        comp_data = copy.deepcopy(self.completions_data)
        comp_data.update(
            {
                "temperature": (
                    self.state["temperature"] if temperature is None else temperature
                ),
                "stream": stream,
                "stop": self.state["custom_stop_string"],
                "max_tokens": (
                    self.state["max_tokens"] if max_tokens is None else max_tokens
                ),
                "top_k": self.state["top_k"],
                "top_p": self.state["top_p"],
                "min_p": self.state["min_p"],
                "tfs": self.state["tfs"],
                "frequency_penalty": self.state["frequency_penalty"],
                "presence_penalty": self.state["presence_penalty"],
                "repetition_penalty": self.state["repetition_penalty"],
                "mirostat_mode": self.state["mirostat_mode"],
                "mirostat_tau": self.state["mirostat_tau"],
                "mirostat_eta": self.state["mirostat_eta"],
                "temperature_last": self.state["temperature_last"],
                "smoothing_factor": self.state["smoothing_factor"],
            }
        )
        if using_remoteapi is True:
            match = self.pattern_task.search(system_prompt)
            if match:
                system_task_prompt = match.group(1).strip()
                messages = self.pattern_task.sub("", system_prompt).strip()
                # logger.info(f"system_task_prompt: {system_task_prompt}")
                # logger.info(f"messages: {messages}")
            else:
                system_task_prompt = None
                messages = system_prompt
            comp_data["system_prompt"] = system_task_prompt
            comp_data["messages"] = messages
            if "prompt" in comp_data:
                del comp_data["prompt"]
        else:
            comp_data["prompt"] = system_prompt
            if "system_prompt" in comp_data:
                del comp_data["system_prompt"]
            if "messages" in comp_data:
                del comp_data["messages"]
        return comp_data

    # Get LLM response
    async def get_chat_response(
        self,
        system_prompt: str,
        temperature=None,
        apiurl: str = None,
        stream: bool = False,
        using_remoteapi: bool = None,
    ) -> str:
        if using_remoteapi is None:
            config_data = await getGlobalConfig("config_data")
            using_remoteapi = config_data["using_remoteapi"]
        payloads = self.update_completion_data(
            system_prompt=system_prompt,
            temperature=temperature,
            stream=stream,
            using_remoteapi=using_remoteapi,
        )
        if using_remoteapi is not True:
            response = await self.tabby_server.inference(
                payloads=payloads, apiurl=apiurl
            )
        else:
            response = await self.tabby_server.inference_remoteapi(
                payloads=payloads, apiurl=apiurl
            )
        if response is not None:
            response_text = self.tabby_server.remove_extra_punctuation(response)
            if response_text is not None:
                response_text = response_text.strip()
                return response_text
            else:
                return None
        else:
            return None

    # Rephase Function
    async def get_rephase_response(
        self,
        user_msg: str,
        system_prompt: str,
        using_remoteapi: bool = None,
    ) -> str:
        if using_remoteapi is None:
            config_data = await getGlobalConfig("config_data")
            using_remoteapi = config_data["using_remoteapi"]
        if using_remoteapi is not True:
            prompt = self.rephrase_template.replace(
                r"<|system_prompt|>", system_prompt
            ).replace(r"<|user_prompt|>", user_msg)
        else:
            prompt = f"{system_prompt}\n{user_msg}"
            # logger.info(f"Rephrase prompt: {prompt}")
        response_text = await self.get_chat_response(
            system_prompt=prompt,
            temperature=0.7,
            apiurl=config_data["openai_api_chat_base"],
        )
        return response_text

    # Generate SD prompt and image
    async def generate_prompt_main(self, response_to_reprompt: str):
        system_prompt = self.restruct_prompt
        user_prompt = f"user provided input:\n<context>{response_to_reprompt}</context><for_char>{self.state['char_name']}</for_char>\nOutput:"
        response_text = await self.get_rephase_response(
            system_prompt=system_prompt, user_msg=user_prompt
        )
        if response_text is not None:
            return response_text
        else:
            return "(Error: Failed to generate prompt.)"

    async def create_live_bgbase64(self, response_text: str):
        match_bg = re.search(
            r"<current_env>(.*?)</current_env>",
            response_text,
            re.DOTALL,
        )
        match_outfit = re.search(
            r"<wear_type_of>(.*?)</wear_type_of>",
            response_text,
            re.DOTALL,
        )
        match_emotion = re.search(
            r"<current_emotion>(.*?)</current_emotion>",
            response_text,
            re.DOTALL,
        )
        match_behavior = re.search(
            r"<current_postures_actions>(.*?)</current_postures_actions>",
            response_text,
            re.DOTALL,
        )
        if match_bg and match_outfit and match_emotion and match_behavior:
            result_bg = match_bg.group(1).strip()
            result_outfit = match_outfit.group(1).strip()
            result_emotion = match_emotion.group(1).strip()
            result_behavior = match_behavior.group(1).strip()
            logger.info(
                f"Background:> {result_bg}  Outfits:> {result_outfit}  Emotion:> {result_emotion} Behavior:> {result_behavior}"
            )
            if result_bg != "SIMILAR_ENV":
                self.state["env_setting"] = result_bg  # Update the environment setting
                if result_outfit in self.state["char_outfit"]:
                    outfits = self.state["char_outfit"][result_outfit]
                else:
                    outfits = self.state["char_outfit"]["normal"]
                logger.info("Add AsyncTask for Live Background...")
                livebgTask = asyncio.create_task(
                    self.generate_image(
                        width=self.image_bg_size["width"],
                        height=self.image_bg_size["height"],
                        hr_scale=1.5,
                        steps=self.image_payload["steps"],
                        enable_hr=True,
                        prompt_prefix=self.prmopt_fixed_prefix,
                        char_looks=self.state["char_looks"]
                        + ", "
                        + outfits
                        + ", "
                        + f"({result_emotion} expressions:1.15)"
                        + ", "
                        + result_behavior,
                        prompt_main="",
                        prompt_suffix=self.prmopt_fixed_suffix,
                        lora_prompt="",
                        env_setting=self.state["env_setting"],
                        show_prompt=True,
                        task_flag="generate_live-ChatBackgroud",
                    )
                )
                livebgBase64 = await livebgTask
                livebgBase64 = await convert_to_webpbase64(livebgBase64, quality=85)
                await self.send_msg_websocket(
                    {
                        "name": "live-ChatBackgroud",
                        "imgBase64URI": "data:image/webp;base64," + livebgBase64,
                    },
                    self.conversation_id,
                )

        else:
            logger.info(f"Background: > error output format detected")

    # Generate background and outfit
    async def generate_bg_outfit(self, context):
        weartype_list = ",".join(self.state["char_outfit"].keys())
        sysprompt = prompt_params["scenario_setting_prompt"]
        userprompt = f"User provided input:\n<context>\n{context}\n</context>\n<pre_env>{self.state['env_setting']}</pre_env>\n<for_char>{self.state['char_name']}</for_char>\n<wear_type>{weartype_list}</wear_type><emotion_type>{self.express_words}</emotion_type>\nOutput:"
        # logger.info(f"BG outfit prompt:\n{sysprompt}\n{userprompt}")
        config_data = await getGlobalConfig("config_data")
        using_remoteapi = config_data["using_remoteapi"]
        temperature = 0.5
        stream = False
        max_tokens = 300
        if using_remoteapi:
            payloads = {
                "system_prompt": sysprompt,
                "messages": userprompt,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": stream,
            }
            apiurl = (
                config_data["openai_api_chat_base"]
                + "/remoteapi/"
                + config_data["remoteapi_endpoint"]
            )
            try:
                async with httpx.AsyncClient(timeout=80) as client:
                    response = await client.post(url=apiurl, json=payloads)
                    if response.status_code == 200:
                        # logger.info(f"BG analysis result: > {response.text}")
                        bg_result = response.text
                        task = asyncio.create_task(self.create_live_bgbase64(bg_result))
            except Exception as e:
                logger.error(f"Error generating background analysis: {e}")
        else:
            system_prompt = self.rephrase_template.replace(
                r"<|system_prompt|>", sysprompt
            ).replace(r"<|user_prompt|>", userprompt)
            payloads = self.update_completion_data(
                system_prompt=system_prompt,
                temperature=temperature,
                stream=stream,
                max_tokens=max_tokens,
                using_remoteapi=using_remoteapi,
            )
            bg_result = await self.tabby_server.inference(payloads=payloads)
            task = asyncio.create_task(self.create_live_bgbase64(bg_result))

    async def generate_image(
        self,
        width=None,
        height=None,
        hr_scale=None,
        steps=None,
        enable_hr=None,
        prompt_prefix="",
        char_looks="",
        prompt_main="",
        env_setting="",
        prompt_suffix="",
        lora_prompt="",
        show_prompt: bool = False,
        task_flag=None,
    ):

        if prompt_prefix != "":
            prompt_prefix = f"{prompt_prefix}, "
        if char_looks != "":
            char_looks = f"{char_looks}, "
        if prompt_main != "":
            prompt_main = await self.generate_prompt_main(prompt_main)
            prompt_main.strip(", ")
            prompt_main = f"{prompt_main}, "
        if env_setting != "":
            env_setting = f"{env_setting}, "
        if lora_prompt != "":
            lora_prompt = f"{lora_prompt}, "
        if width is None:
            width = self.image_payload["width"]
        if height is None:
            height = self.image_payload["height"]
        if hr_scale is None:
            hr_scale = self.image_payload["hr_scale"]
        if steps is None:
            steps = self.image_payload["steps"]
        if enable_hr is None:
            enable_hr = self.image_payload["enable_hr"]
        prompt_api = f"{prompt_prefix}{char_looks}{prompt_main}{lora_prompt}{env_setting}{prompt_suffix}"
        if show_prompt:
            logger.info(f"The SD prompt: \n {prompt_api}")
        payload = {
            "hr_negative_prompt": self.nagetive_prompt,
            "hr_prompt": prompt_api,
            "hr_scale": hr_scale,
            "hr_second_pass_steps": self.image_payload["hr_second_pass_steps"],
            "seed": self.image_payload["seed"],
            "enable_hr": enable_hr,
            "width": width,
            "height": height,
            "hr_upscaler": self.image_payload["hr_upscaler"],
            "negative_prompt": self.nagetive_prompt,
            "prompt": prompt_api,
            "sampler_name": self.image_payload["sampler_name"],
            "cfg_scale": self.image_payload["cfg_scale"],
            "denoising_strength": self.image_payload["denoising_strength"],
            "steps": steps,
            "override_settings": {
                "sd_vae": self.image_payload["override_settings"]["sd_vae"],
                "sd_model_checkpoint": self.image_payload["override_settings"][
                    "sd_model_checkpoint"
                ],
            },
            "override_settings_restore_afterwards": self.image_payload[
                "override_settings_restore_afterwards"
            ],
        }
        imgBase64 = await self.tabby_server.SD_image(
            payload=payload,
            task_flag=task_flag,
            send_msg_websocket=self.send_msg_websocket,
            client_id=self.conversation_id,
        )
        return imgBase64

    # Process if trigger key words
    async def generate_picture_by_sdapi(self, prompt: str = "", loraword: str = ""):
        lora_prompt = self.lora.get(loraword.strip(), "")
        logger.info(f"Lora :{lora_prompt}")
        char_looks = self.state["char_looks"]
        if self.state["char_outfit"] and lora_prompt in self.state["char_outfit"]:
            char_outfit = self.state["char_outfit"][lora_prompt]
            if char_outfit:
                char_looks = f"{char_looks},{char_outfit}"
                lora_prompt = ""
                logger.info(char_looks)
        if self.send_msg_websocket:
            await self.send_msg_websocket(
                {"name": "chatreply", "msg": "Generating Scene Image"},
                self.conversation_id,
            )
        logger.info("Generate Dynamic Picture")
        image = await self.generate_image(
            prompt_prefix=self.prmopt_fixed_prefix,
            char_looks=char_looks,
            prompt_main=prompt,
            prompt_suffix=self.prmopt_fixed_suffix,
            lora_prompt=lora_prompt,
            env_setting=self.state["env_setting"],
            show_prompt=True,
            enable_hr=True,
            task_flag="generate_live-DynamicPicture",
        )
        return image

    # Process for chat message
    async def message_process(
        self, full_prompt: str, plot_content: str, first_sentence: str
    ):
        # Here is generate streaming chat response from LLM
        response_text = await self.get_chat_response(
            system_prompt=full_prompt, stream=True, temperature=0.9
        )

        if response_text is None:
            return None
        
        last_ai_sentence = f"{self.state['char_name']}: {response_text}"
        self.last_context.append(last_ai_sentence)
        cliped_context = "\n".join(self.last_context[-10:])
        last_full_talk = (
            "\n[scenario of RolePlay]\n\n"
            + plot_content
            + "\n\n[Dialogue of RolePlay]\n"
            + first_sentence
            + "\n"
            + cliped_context
            + "\n"
        )
        # create task to check background and outfits
        task_generate_bg_outfit = asyncio.create_task(
            self.generate_bg_outfit(last_full_talk)
        )
        
        # if memory mode is on, then create task to save memory and generate previous summary
        if self.ai_is_memory_mode is True:
            task_memory_saving = asyncio.create_task(
                self.memory_saving_process(response_text)
            )
            task_memory_previous_summary = asyncio.create_task(
                self.memory_previous_summary(
                    owner=self.state["char_name"],
                    user_name=self.state["user_name"],
                    plot_description=plot_content,
                    dialog=self.last_context,
                )
            )

        if self.state["generate_dynamic_picture"] and self.iscreatedynimage:
            user_msg = f"\nUser provided input: \n<context>{cliped_context}</context><for_char>{self.state['char_name']}</for_char>\nOutput:"
            response = await self.get_rephase_response(
                system_prompt=self.summary_prompt, user_msg=user_msg
            )
            logger.info(f"Rephrased Result of scenario detection: \n[ {response} ]")
            if response is None:
                response = "Normal"
            is_word_triggered, match_result = contains_vocabulary(
                response, self.resultslist
            )

            if is_word_triggered:
                logger.info(f"Matched Result: {match_result}")
                result_picture = await self.generate_picture_by_sdapi(
                    prompt=last_full_talk, loraword=match_result
                )
                return response_text, result_picture

        return response_text, False

    async def memory_saving_process(self, response_text: str):
        # if memory has been exsited, then add memory to the context
        dialog = [
            {"role": "user", "content": self.user_last_msg},
            {"role": "assistant", "content": response_text},
        ]
        if_memory_exist = await self.cyberchat_memory.judge_if_memory_has_exsited(
            char_uid=self.state["char_uid"],
            user_uid=self.state["user_uid"],
            owner=self.state["char_name"],
            user_name=self.state["user_name"],
            vector_name="memory_vector",
            dialog=dialog,
        )
        logger.info(f"If_memory_exist: {json.loads(if_memory_exist)}")
        if json.loads(if_memory_exist)["has_existed"] is not True:
            memory_judge = await self.cyberchat_memory.judge_dialog_if_need_add_memory(
                owner=self.state["char_name"],
                user_name=self.state["user_name"],
                dialog=dialog,
            )
            # print(memory_judge)
            memory_data = json.loads(memory_judge)
            logger.info(f"Is_worthy_to_add_to_memory_database: {memory_data}")
            if memory_data["is_worthy_to_add_to_memory_database"] is True:
                S_value_of_retention = (
                    await self.cyberchat_memory.evaluate_memory_retention(
                        description=memory_data["description"]
                    )
                )
                S_value = round(float(json.loads(S_value_of_retention)["S_value"]), 4)
                await self.cyberchat_memory.add_memory(
                    vector_name="memory_vector",
                    description=memory_data["description"],
                    S_value_of_retention=S_value,
                    char_uid=self.state["char_uid"],
                    owner=self.state["char_name"],
                    user_uid=self.state["user_uid"],
                    user_name=self.state["user_name"],
                    memory_level="user-level",
                    memory_type=memory_data["memory_type"],
                    memory_category=memory_data["memory_category"],
                    memory_date=datetime.now().strftime("%Y-%m-%d"),
                )
                
    async def memory_previous_summary(self, owner: str, user_name: str, plot_description: str, dialog: list):
        previous_summary = await self.cyberchat_memory.memory_previous_summary(
            owner=owner,
            user_name=user_name,
            plot_description=plot_description,
            dialog=dialog,
        )
        previous_summary = json.loads(previous_summary)
        narrator_summary = previous_summary["previous_summary_narrator"]
        owner_summary = previous_summary["previous_summary_owner"]
        the_latest_words_user = previous_summary["the_latest_words_1"]
        the_latest_words_owner = previous_summary["the_latest_words_2"]
        memory_json = {
            "previous_summary_narrator": narrator_summary,
            "previous_summary_owner": owner_summary,
            "the_latest_words_user": the_latest_words_user,
            "the_latest_words_owner": the_latest_words_owner,
        }
        # logger.info(f"memory_json: {memory_json}")
        memory_json_str = json.dumps(memory_json)
        await self.cyberchat_memory.add_memory(
            vector_name="memory_vector",
            description=memory_json_str,
            char_uid=self.state["char_uid"],
            owner=owner,
            user_uid=self.state["user_uid"],
            user_name=user_name,
            is_previous_summary=True,
            memory_date=datetime.now().strftime("%Y-%m-%d")
        )
        

    async def fetch_results(
        self, prompt: str, user_last_msg: str, iscreatedynimage: bool = True
    ):
        self.user_last_msg = user_last_msg.replace("'", "\\'").replace('"', '\\"')

        self.iscreatedynimage = iscreatedynimage
        self.image_bg_size = {
            "width": self.image_payload["width"],
            "height": self.image_payload["height"],
        }
        # deassemble the prompt
        content_task_removed = self.pattern_task.sub("", prompt)
        match = self.pattern_plot.search(content_task_removed)
        if match:
            plot_content = match.group(1).strip()
        else:
            plot_content = ""

        match = self.pattern_firstword.search(content_task_removed)
        if match:
            first_sentence = match.group(1).strip()
        else:
            first_sentence = ""
        if len(self.last_context) == 0:
            self.last_context.append(first_sentence)
        self.last_context.append(f"{self.state['user_name']}: {self.user_last_msg}")
        if self.ai_is_memory_mode is True:
            dialog = [
                {
                    "role": "assistant",
                    "content": self.last_context[-2].split(
                        f"{self.state['char_name']}: "
                    )[1],
                },
                {"role": "user", "content": self.user_last_msg},
            ]
            if_search_memory = (
                await self.cyberchat_memory.judge_dialog_if_need_search_memory(
                    owner=self.state["char_name"],
                    user_name=self.state["user_name"],
                    dialog=dialog,
                )
            )
            if_search_memory = json.loads(if_search_memory)
            logger.info(f"if_search_memory: {if_search_memory}")
            if if_search_memory["if_need_search_memory"] is True:
                search_result = await self.cyberchat_memory.search_memory(
                    dialog=dialog,
                    vector_name="memory_vector",
                    limit=3,
                    char_uid=self.state["char_uid"],
                    user_uid=self.state["user_uid"],
                    owner=self.state["char_name"],
                    user_name=self.state["user_name"],
                    memory_level="user-level",
                    convert_dialog_to_query=True,
                )
                logger.info(f"search_result: {search_result}")
                if search_result is not None:
                    prompt = (
                        prompt
                        + f"\n[Memories of {self.state['char_name']} for reference to reply to {self.state['user_name']}, if there is no valuable information, please ignore it and reply directly as normal:\n {search_result}]"
                    )

        result = await self.message_process(
            full_prompt=prompt, plot_content=plot_content, first_sentence=first_sentence
        )

        if isinstance(result, tuple):
            return result
        elif isinstance(result, str):
            return "OK~, here is what you asked for~ *i send back a picture*", result
        else:
            return None, None

    def count_token_numbers(self, string: str) -> int:
        """Returns the number of tokens in a text string."""
        encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
        num_tokens = len(encoding.encode(string))
        return num_tokens
