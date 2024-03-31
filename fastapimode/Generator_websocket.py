# tabbyAPI_server Class
from fastapimode.sys_path import project_root
from fastapimode.tabby_fastapi_websocket import tabby_fastapi
import json, os, tiktoken, yaml, httpx, aiofiles
from modules.global_sets_async import logging, config_data, timeout
from modules.payload_state import completions_data

dir_path = project_root


# dir_path = os.path.dirname(os.path.realpath(__file__))
# get models
async def get_model_name(api_base: str, model_type: str, api_key: str, admin_key: str):
    headers = {
        "accept": "application/json",
        "x-api-key": api_key,
        "x-admin-key": admin_key,
        "Content-Type": "application/json",
    }
    model_name = "NONE"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url=api_base + "/model", headers=headers, timeout=timeout
            )
            response.raise_for_status()
            if response.status_code == 200:
                datas = response.json()
                model_name = datas["id"]
                return model_name
            else:
                logging.info("请求失败，状态码：", response.status_code)
    except Exception as e:
        logging.info(
            f"Error to get model from {api_base}, \nPlease set up the {model_type} model address in config.yml before chatting"
        )
    finally:
        return model_name


# Load prompts for generating'
async def load_prompts(file_path):
    yaml_file_path = os.path.join(dir_path, "config", "prompts", file_path)
    async with aiofiles.open(yaml_file_path, "r") as file:
        content = await file.read()
        prompts_data = yaml.safe_load(content)
        restruct_prompt = prompts_data["restruct_prompt"]
        prmopt_fixed_prefix = prompts_data["prmopt_fixed_prefix"]
        prmopt_fixed_suffix = prompts_data["prmopt_fixed_suffix"]
        nagetive_prompt = prompts_data["nagetive_prompt"]
    return restruct_prompt, prmopt_fixed_prefix, prmopt_fixed_suffix, nagetive_prompt


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

    async def async_init(
        self, state: dict, image_payload: dict, send_msg_websocket: callable = None
    ):
        self.send_msg_websocket = send_msg_websocket
        self.state = state
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
        self.chat_model = await get_model_name(
            self.state["openai_api_chat_base"], "Chat", self.api_key, self.admin_key
        )
        self.rephase_model = await get_model_name(
            self.state["openai_api_rephase_base"],
            "Rephase",
            self.api_key,
            self.admin_key,
        )
        self.vocabulary, self.resultslist, self.lora, self.summary_prompt = (
            await load_vocabulary(self.state["match_words_cata"])
        )
        (
            self.restruct_prompt,
            self.prmopt_fixed_prefix,
            self.prmopt_fixed_suffix,
            self.nagetive_prompt,
        ) = await load_prompts("prompts.yaml")
        self.restruct_prompt = self.restruct_prompt.replace(
            "<|default_bg|>", self.state["env_setting"]
        )
        logging.info(
            f"Chat model: {self.chat_model} | Rephase model: {self.rephase_model}"
        )

    def get_rephrase_template(self):
        chat_template_name = self.state["prompt_template"].split("_")
        rephrase_template_name = chat_template_name[0] + "_Rephrase"
        self.rephrase_template = self.state["prompts_templates"][rephrase_template_name]

    # Get LLM response
    async def get_chat_response(
        self,
        system_prompt: str,
        temperature=None,
        apiurl: str = None,
        stream: bool = False,
    ) -> str:
        self.completions_data["temperature"] = (
            self.state["temperature"] if temperature is None else temperature
        )
        self.completions_data["stream"] = stream
        self.completions_data["prompt"] = system_prompt
        self.completions_data["stop"] = self.state["custom_stop_string"]
        self.completions_data["max_tokens"] = self.state["max_tokens"]
        self.completions_data["top_k"] = self.state["top_k"]
        self.completions_data["top_p"] = self.state["top_p"]
        self.completions_data["min_p"] = self.state["min_p"]
        self.completions_data["tfs"] = self.state["tfs"]
        self.completions_data["frequency_penalty"] = self.state["frequency_penalty"]
        self.completions_data["presence_penalty"] = self.state["presence_penalty"]
        self.completions_data["repetition_penalty"] = self.state["repetition_penalty"]
        self.completions_data["mirostat_mode"] = self.state["mirostat_mode"]
        self.completions_data["mirostat_tau"] = self.state["mirostat_tau"]
        self.completions_data["mirostat_eta"] = self.state["mirostat_eta"]
        self.completions_data["temperature_last"] = self.state["temperature_last"]
        self.completions_data["smoothing_factor"] = self.state["smoothing_factor"]
        payloads = self.completions_data
        response = await self.tabby_server.inference(payloads=payloads, apiurl=apiurl)
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
    async def get_rephase_response(self, user_msg: str, system_prompt: str) -> str:
        prompt = self.rephrase_template.replace(
            r"<|system_prompt|>", system_prompt
        ).replace(r"<|user_prompt|>", user_msg)
        response_text = await self.get_chat_response(
            system_prompt=prompt,
            temperature=0.001,
            apiurl=config_data["openai_api_rephase_base"],
        )
        return response_text

    # Generate SD prompt and image
    async def generate_prompt_main(self, response_to_reprompt: str):
        system_prompt = self.restruct_prompt
        user_prompt = f'The subject needs to generate a final text2image prompt is: "{response_to_reprompt}"'
        response_text = await self.get_rephase_response(
            system_prompt=system_prompt, user_msg=user_prompt
        )
        return response_text

    async def generate_image(
        self,
        prompt_prefix="",
        char_looks="",
        prompt_main="",
        env_setting="",
        prompt_suffix="",
        lora_prompt="",
    ):

        if prompt_prefix != "":
            prompt_prefix = f"{prompt_prefix}, "
        if char_looks != "":
            char_looks = f"{char_looks}, "
        if prompt_main != "":
            prompt_main = await self.generate_prompt_main(prompt_main)
            prompt_main.strip(", ")
            prompt_main = f"({prompt_main}:1.15), "
        if env_setting != "":
            env_setting = f"{env_setting}, "
        if lora_prompt != "":
            lora_prompt = f"({lora_prompt}:1.12), "

        prompt_api = f"{prompt_prefix}{char_looks}{prompt_main}{env_setting}{lora_prompt}{prompt_suffix}"
        logging.info(f"The SD prompt: \n {prompt_api}")
        payload = {
            "hr_negative_prompt": self.nagetive_prompt,
            "hr_prompt": prompt_api,
            "hr_scale": self.image_payload["hr_scale"],
            "hr_second_pass_steps": self.image_payload["hr_second_pass_steps"],
            "seed": self.image_payload["seed"],
            "enable_hr": self.image_payload["enable_hr"],
            "width": self.image_payload["width"],
            "height": self.image_payload["height"],
            "hr_upscaler": self.image_payload["hr_upscaler"],
            "negative_prompt": self.nagetive_prompt,
            "prompt": prompt_api,
            "sampler_name": self.image_payload["sampler_name"],
            "cfg_scale": self.image_payload["cfg_scale"],
            "denoising_strength": self.image_payload["denoising_strength"],
            "steps": self.image_payload["steps"],
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
        imgBase64 = await self.tabby_server.SD_image(payload=payload)
        return imgBase64

    # Process if trigger key words
    async def generate_picture_by_sdapi(self, prompt: str = "", loraword: str = ""):
        recived_prompt = prompt
        lora_prompt = self.lora.get(loraword.strip(), "")
        logging.info(f"Lora :{lora_prompt}")
        if self.state["char_outfit"] is not None:
            char_outfit = self.state["char_outfit"][lora_prompt]
            if char_outfit is not None:
                char_looks = f"{self.state['char_looks']},{char_outfit}"
                lora_prompt = ""
                logging.info(char_looks)
            else:
                char_looks = self.state['char_looks']
        else:
            char_looks = self.state['char_looks']
        if self.send_msg_websocket is not None:
            await self.send_msg_websocket(
                {"name": "chatreply", "msg": "Generating Scene Image"},
                self.conversation_id,
            )
        logging.info(">>>Generate Dynamic Picture\n")
        image = await self.generate_image(
            prompt_prefix=self.prmopt_fixed_prefix,
            char_looks=char_looks,
            prompt_main=recived_prompt,
            prompt_suffix=self.prmopt_fixed_suffix,
            lora_prompt=lora_prompt,
        )
        return image

    # Process for chat message
    async def message_process(self, system_prompt:str):
        response_text = await self.get_chat_response(
            system_prompt=system_prompt, stream=True
        )
        if response_text is not None:
            self.last_context.append(f"{self.state['char_name']}: {response_text}")
            if (
                self.state["generate_dynamic_picture"] is True
                and self.iscreatedynimage is True
            ):
                self.last_context = self.last_context[-4:]
                repharse_text = "\n".join(self.last_context)
                user_msg = f"Output your selection base on following context: \n< {repharse_text} >"
                response = await self.get_rephase_response(
                    system_prompt=self.summary_prompt, user_msg=user_msg
                )
                logging.info(f">>>The rephase result is {response}")
                is_word_triggered, match_result = contains_vocabulary(
                    response, self.resultslist
                )
                if is_word_triggered is True:
                    logging.info(f">>>Matched result is: {match_result}")
                    text_to_image = response_text.replace("\n", ". ").strip()
                    result_picture = await self.generate_picture_by_sdapi(
                        prompt=text_to_image, loraword=match_result
                    )
                    return response_text, result_picture
            return response_text, False
        else:
            return None

    async def fetch_results(
        self, prompt: str, user_last_msg: str, iscreatedynimage: bool = True
    ):
        self.user_last_msg = user_last_msg.replace("'", "\\'").replace('"', '\\"')
        self.last_context.append(f"{self.state['user_name']}: {self.user_last_msg}")
        self.iscreatedynimage = iscreatedynimage
        result = await self.message_process(system_prompt=prompt)
        if isinstance(result, tuple):
            # 假定返回了字符串和图像对象
            string_value, image_object = result
        elif isinstance(result, str):
            # 只返回了图像对象base64 string
            image_object = result
            string_value = "OK~, here is what you asked for~ *i send back a picture*"
        else:
            # 处理其他意外情况
            image_object = None
            string_value = None
        return string_value, image_object
        # except Exception as e:
        #     logging.info(f"Error during eval: {e}")
        #     return None, None

    def count_token_numbers(self, string: str) -> int:
        """Returns the number of tokens in a text string."""
        encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
        num_tokens = len(encoding.encode(string))
        return num_tokens
