import httpx, time, base64, json, asyncio
from modules.global_sets_async import config_data, timeout, logging
from modules.payload_state import completions_data, model_load_data, sd_payload


class tabby_fastapi:
    """
    Core class for interact with tabby api

    functions include:

    inference(streaming or normal)

    unload / load model

    get model list

    get stable diffusion model list

    xtts audio generate

    stable_diffusion api
    """

    def __init__(
        self,
        url: str = None,
        api_key: str = None,
        admin_key: str = None,
        conversation_id: str = None,
        send_msg_websocket: callable = None,
    ) -> None:
        self.send_msg_websocket = send_msg_websocket
        self.conversation_id = conversation_id
        self.url = url
        self.headers = {
            "accept": "application/json",
            "x-api-key": api_key,
            "x-admin-key": admin_key,
            "Content-Type": "application/json",
        }
        self.completions_data = completions_data
        self.model_load_data = model_load_data

    async def inference_stream(self, url: str, headers: dict, payloads: dict):
        try:
            async with httpx.AsyncClient() as client:
                async with client.stream(
                    "POST", url=url, headers=headers, json=payloads, timeout=timeout
                ) as response:
                    async for chunk in response.aiter_text():
                        if "data:" in chunk:
                            try:
                                __, datastr = chunk.split("data:", 1)
                                datastr = datastr.strip()
                                if datastr != "[DONE]":
                                    output = json.loads(datastr)
                                    output_char = output["choices"][0]["text"]
                                    await asyncio.sleep(0.1)
                                    yield output_char
                                else:
                                    yield "[DONE]"
                                    break
                            except json.JSONDecodeError:
                                pass
                        else:
                            continue
        except Exception as e:
            logging.info("Error to get stream data", e)

    async def inference(self, payloads: dict = None, apiurl: str = None):
        """
        LLM tabby api inference

        set parm (stream) to switch working mode.
        """
        if payloads is None:
            payloads = self.completions_data

        if apiurl is None:
            apiurl = self.url + "/completions"
        else:
            apiurl = apiurl + "/completions"

        stream = payloads["stream"]
        headers = self.headers
        if stream is True:
            logging.info("Get streaming response from api.")
            completeMsg = ""
            try:
                async for outputchar in self.inference_stream(
                    url=apiurl, payloads=payloads, headers=headers
                ):
                    if outputchar is not None:
                        if outputchar != "[DONE]":
                            msgpack = {"event": "streaming", "text": outputchar}
                            await self.send_msg_websocket(
                                {"name": "chatreply", "msg": msgpack},
                                self.conversation_id,
                            )
                            completeMsg += outputchar
                        else:
                            msgpack = {"event": "streaming", "text": outputchar}
                            await self.send_msg_websocket(
                                {"name": "chatreply", "msg": msgpack},
                                self.conversation_id,
                            )
                            logging.info(completeMsg)
                            return completeMsg
                    else:
                        return None
            except Exception as e:
                print(f"发生错误: {e}")

        else:
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        url=apiurl, headers=headers, json=payloads, timeout=timeout
                    )
                    response = response.json()
                    response = response["choices"][0]["text"]
                    return response
            except Exception as e:
                logging.info("Error on inference: ", e)

    async def get_model(self):
        url = self.url + "/model"
        headers = self.headers
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url=url, headers=headers, timeout=timeout)
                response = response.json()
                logging.info(f"Current model: {response['id']}")
                return response["id"]
        except Exception as e:
            logging.info("Error on get current model: ", e)
            return "None"

    async def get_model_list(self) -> list:
        url = self.url + "/models"
        headers = self.headers
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url=url, headers=headers, timeout=timeout)
                response = response.json()
                models = [model["id"] for model in response["data"]]
                return models
        except Exception as e:
            logging.info("Error on get current model-list: ", e)
            return []

    async def unload_model(self):
        url = self.url + "/model/unload"
        headers = self.headers
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url=url, headers=headers, timeout=timeout)
                if response.status_code == 200:
                    return True
                else:
                    return False
        except Exception as e:
            logging.info("Error on unloading model: ", e)
            return False

    async def load_model(
        self,
        name: str = "",
        max_seq_len: int = 4096,
        gpu_split_auto: bool = True,
        gpu_split: list = [0],
        prompt_template: str = None,
    ):
        url = self.url + "/model/load"
        headers = self.headers
        self.model_load_data["name"] = name
        self.model_load_data["max_seq_len"] = max_seq_len
        await self.send_msg_websocket(
            {"name": "initialization", "msg": f"Loading Model: {name} ..."},
            self.conversation_id,
        )
        async with httpx.AsyncClient() as client:
            try:
                gpu_info = await client.get(
                    url=self.url + "/gpu", headers=headers, timeout=timeout
                )
                if gpu_info.status_code == 200:
                    gpu_info = gpu_info.json()
                    if gpu_info["GPU Count"] == 1:
                        self.model_load_data["gpu_split_auto"] = True
                    else:
                        self.model_load_data["gpu_split_auto"] = False
                        gpu_split = []
                        for gpu in gpu_info["GPU Info"]:
                            gpu_split.append(int(gpu["GPU_Memory"] * 0.7))
                        self.model_load_data["gpu_split"] = gpu_split
                        logging.info(f"The Gpu Split to: {gpu_split}")
            except Exception as e:
                logging.info("Error during load GPU info: ", e)
                self.model_load_data["gpu_split_auto"] = True

            self.model_load_data["prompt_template"] = prompt_template

            try:
                response = await client.post(
                    url=url, headers=headers, json=self.model_load_data, timeout=timeout
                )
                if response.status_code == 200:
                    logging.info(f">>> Model Changed To: {name}")
                    return "Success"
                else:
                    logging.info(">>> Model Load Failed")
                    return "Fail"
            except Exception as e:
                logging.info("Error on load model: ", e)

    async def get_sd_model_list(self):
        url = config_data["SDAPI_url"] + "/sdapi/v1/sd-models"
        tabbyAPIurl = f'{config_data["openai_api_chat_base"]}/SDapiModelList'
        headers = {
            # 'accept': 'application/json'
            "SD-URL": url
        }
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url=tabbyAPIurl, headers=headers, timeout=timeout
                )
                response = response.json()
                model_list = []
                for model_name in response:
                    model_list.append(model_name["model_name"])
                logging.info(f">>> SD Model List: {model_list}")
                return model_list
        except Exception as e:
            logging.info("Error on get SD model list: ", e)
            return None

    @staticmethod
    async def xtts_audio(
        url: str,
        text: str,
        speaker_wav: str,
        language: str,
        server_url: str,
        timeout=timeout,
    ):
        """
        url: api point of xtts in tabbyapi
        server_url: api point of xtts api server "end with '/'"
        """
        headers = {"accept": "audio/wav", "Content-Type": "application/json"}
        payload = {
            "text": text,
            "speaker_wav": speaker_wav,
            "language": language,
            "server_url": server_url,
        }
        try:
            async with httpx.AsyncClient() as client:
                logging.info("Start to fetch TTS audio")
                start_time = time.perf_counter()
                response = await client.post(
                    url=url, headers=headers, json=payload, timeout=timeout
                )
                response.raise_for_status()
                end_time = time.perf_counter()
                total_run_time = end_time - start_time
                logging.info(f"TTS cost time: {total_run_time:.2f} seconds")
                audio_data_base64 = base64.b64encode(response.content).decode("utf-8")
        except Exception as e:
            logging.info(f"Error on get xtts audio: {e}")
            audio_data_base64 = False
        finally:
            return audio_data_base64

    @staticmethod
    async def SD_image(
        url: str = None, payload: dict = None, headers: dict = None, timeout=timeout
    ):
        if headers is None:
            headers = {"SD-URL": f'{config_data["SDAPI_url"]}/sdapi/v1/txt2img'}
        if url is None:
            url = f'{config_data["openai_api_chat_base"]}/SDapi'
        if payload is None:
            payload = sd_payload
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url=url, json=payload, headers=headers, timeout=timeout
                )
                result = response.json()
                imgBase64 = result["images"][0]
                return imgBase64
        except Exception as e:
            logging.info(f"Error to generate SD img: {e}")

    @staticmethod
    def remove_extra_punctuation(text):
        if text is not None and text != "":
            end_punctuation = [
                ".",
                "!",
                "?",
                "…",
                "*",
                '"',
                "```",
                "。",
                "！",
                "？",
                "”",
            ]
            if text[-1] not in end_punctuation:
                for i in range(len(text) - 1, -1, -1):
                    if text[i] in end_punctuation:
                        text = text[: i + 1]
                        break
            return text
        else:
            return None

    @staticmethod
    async def pure_inference(
        api_key: str = config_data["api_key"],
        admin_key: str = config_data["admin_key"],
        payloads: dict = completions_data,
        apiurl: str = config_data["openai_api_chat_base"] + "/completions",
    ):
        headers = {
            "accept": "application/json",
            "x-api-key": api_key,
            "x-admin-key": admin_key,
            "Content-Type": "application/json",
        }
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url=apiurl, headers=headers, json=payloads, timeout=timeout
                )
                response = response.json()
                response = response["choices"][0]["text"]
                return response
        except Exception as e:
            logging.info("Error on inference: ", e)
