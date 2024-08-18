from fastapimode.sys_path import project_root
from fastapimode.tabby_fastapi_websocket import tabby_fastapi
import os, tiktoken, yaml, httpx, aiofiles, asyncio, re, httpx, copy
from modules.global_sets_async import (
    logger,
    config_data,
    timeout,
    prompt_params,
    getGlobalConfig,
    convert_to_webpbase64,
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
        if hasattr(self, "tabby_server") and isinstance(self.tabby_server, tabby_fastapi):
            self.tabby_server.model = value
    async def async_init(
        self, state: dict, image_payload: dict, send_msg_websocket: callable = None
    ):
        self.send_msg_websocket = send_msg_websocket
        self.state = state
        self.pattern_task =re.compile(r'<Task>.*?</Task>', re.DOTALL)
        self.pattern_plot = re.compile(r"<Plot_of_the_RolePlay>(.*?)</Plot_of_the_RolePlay>", re.DOTALL)
        self.pattern_firstword = re.compile(rf"({re.escape(self.state['char_name'])}:[\s\S]*?)(?=\n\w+:|$)", re.DOTALL)
        self.express_words = prompt_params['face_expression_words_list']
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
    ):
        comp_data = copy.deepcopy(self.completions_data)
        comp_data.update(
            {
                "temperature": (
                    self.state["temperature"] if temperature is None else temperature
                ),
                "stream": stream,
                "prompt": system_prompt,
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
        payloads = self.update_completion_data(system_prompt, temperature, stream)
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
        if match_bg and match_outfit and match_emotion:
            result_bg = match_bg.group(1).strip()
            result_outfit = match_outfit.group(1).strip()
            result_emotion = match_emotion.group(1).strip()
            logger.info(
                f"Background:> {result_bg}  Outfits:> {result_outfit}  Emotion:> {result_emotion}"
            )
            if result_bg != "SIMILAR_ENV":
                self.state["env_setting"] = (
                    result_bg  # Update the environment setting
                )
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
                        + f"({result_emotion} expressions:1.15)",
                        prompt_main="",
                        prompt_suffix=self.prmopt_fixed_suffix,
                        lora_prompt="",
                        env_setting=self.state["env_setting"],
                        show_prompt=True,
                        task_flag="generate_live-ChatBackgroud",
                    )
                )
                livebgBase64 = await livebgTask
                livebgBase64 = await convert_to_webpbase64(
                    livebgBase64, quality=85
                )
                await self.send_msg_websocket(
                    {
                        "name": "live-ChatBackgroud",
                        "imgBase64URI": "data:image/webp;base64,"
                        + livebgBase64,
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
        max_tokens = 100
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
                        logger.info(f"BG analysis result: > {response.text}")
                        bg_result = response.text
                        task = asyncio.create_task(self.create_live_bgbase64(bg_result))
            except Exception as e:
                logger.error(f"Error generating background analysis: {e}")
        else:
            system_prompt = self.rephrase_template.replace(
                r"<|system_prompt|>", sysprompt
            ).replace(r"<|user_prompt|>", userprompt)
            payloads = self.update_completion_data(system_prompt, temperature, stream, max_tokens)
            bg_result = await self.tabby_server.inference(
                payloads=payloads
            )
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
    async def message_process(self, system_prompt: str):
        content_task_removed = self.pattern_task.sub("", system_prompt)
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
            
        response_text = await self.get_chat_response(
            system_prompt=system_prompt, stream=True, temperature=0.9
        )

        if response_text is None:
            return None
        last_ai_sentence = f"{self.state['char_name']}: {response_text}"
        self.last_context.append(last_ai_sentence)
        cliped_context = "\n".join(self.last_context[-10:])
        last_full_talk = "\n[scenario of RolePlay]\n\n"+plot_content +"\n\n[Dialogue of RolePlay]\n"+first_sentence+"\n"+cliped_context+"\n"
        # create task to check background and outfits
        task = asyncio.create_task(self.generate_bg_outfit(last_full_talk))

        if self.state["generate_dynamic_picture"] and self.iscreatedynimage:
            user_msg = f"\nUser provided input for scenario detection task: \n< {last_full_talk} >"
            response = await self.get_rephase_response(
                system_prompt=self.summary_prompt, user_msg=user_msg
            )
            logger.info(f"Rephrased Result: {response}")

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

    async def fetch_results(
        self, prompt: str, user_last_msg: str, iscreatedynimage: bool = True
    ):
        self.user_last_msg = user_last_msg.replace("'", "\\'").replace('"', '\\"')
        self.last_context.append(f"{self.state['user_name']}: {self.user_last_msg}")
        self.iscreatedynimage = iscreatedynimage
        self.image_bg_size = {
            "width": self.image_payload["width"],
            "height": self.image_payload["height"],
        }
        result = await self.message_process(system_prompt=prompt)

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
