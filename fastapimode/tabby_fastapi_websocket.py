import httpx, time, base64, json, asyncio, uuid, io
from tqdm import tqdm
from modules.tqdm_barformat import Pbar
from modules.global_sets_async import config_data, timeout, logger, getGlobalConfig
from modules.payload_state import completions_data, model_load_data, sd_payload

COLORBAR = Pbar.setBar(
    Pbar.BarColorer.CYAN, Pbar.BarColorer.MAGENTA, Pbar.BarColorer.CYAN
)


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
        self._model = None
        self.headers = {
            "accept": "application/json",
            "x-api-key": api_key,
            "x-admin-key": admin_key,
            "Content-Type": "application/json",
        }
        self.completions_data = completions_data
        self.model_load_data = model_load_data
    @property
    def model(self):
        return self._model
    @model.setter
    def model(self, value):
        self._model = value

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
                                    # await asyncio.sleep(0.1)
                                    yield output_char
                                else:
                                    yield "[DONE]"
                                    break
                            except json.JSONDecodeError:
                                pass
                        else:
                            continue
        except Exception as e:
            logger.info("Error to get stream data", e)

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
        # payloads.pop("model", None)
        headers = self.headers
        if stream is True:
            logger.info("Get streaming response from api.")
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
                            logger.info(completeMsg)
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
                logger.info("Error on inference: ", e)

    async def inference_remoteapi(self, payloads: dict, apiurl: str = None):
        """
        inference from remote api
        """
        config_data = await getGlobalConfig("config_data")
        data = payloads
        if apiurl is None:
            apiurl = self.url
        url = apiurl + "/remoteapi/" + config_data["remoteapi_endpoint"]
        data["model"] = self.model
        if data["stream"] is True:
            async with httpx.AsyncClient(timeout=timeout) as client:
                try:
                    logger.info(
                        f"Get streaming response from remoteapi - {config_data['remoteapi_endpoint']}."
                    )
                    async with client.stream("POST", url, json=data) as response:
                        if response.status_code == 200:
                            async for chunk in response.aiter_text():
                                json_msg = json.loads(chunk)
                                if json_msg["event"] == "text-generation":
                                    msgpack = {
                                        "event": "streaming",
                                        "text": json_msg["text"],
                                    }
                                    await self.send_msg_websocket(
                                        {"name": "chatreply", "msg": msgpack},
                                        self.conversation_id,
                                    )
                                else:
                                    msgpack = {"event": "streaming", "text": "[DONE]"}
                                    await self.send_msg_websocket(
                                        {"name": "chatreply", "msg": msgpack},
                                        self.conversation_id,
                                    )
                                    return json_msg["final_text"]
                        else:
                            print(
                                f"Request failed with status code {response.status_code}"
                            )
                            print(await response.aread())
                except Exception as e:
                    print(f"An error occurred: {e}")
        else:
            async with httpx.AsyncClient(timeout=timeout) as client:
                try:
                    response = await client.post(url, json=data)
                    if response.status_code == 200:
                        return response.text
                    else:
                        print(f"Request failed with status code {response.status_code}")
                        print(await response.aread())
                except Exception as e:
                    print(f"An error occurred: {e}")

    async def get_model(self):
        url = self.url + "/model"
        headers = self.headers
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url=url, headers=headers, timeout=timeout)
                if response.status_code == 200:
                    response = response.json()
                    logger.info(f"Current default model: {response['id']}")
                    return response["id"]
                else:
                    return None
        except Exception as e:
            logger.info("Error on get current model: ", e)
            return None

    async def get_model_list(self) -> list:
        url = self.url + "/models"
        headers = self.headers
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url=url, headers=headers, timeout=timeout)
                if response.status_code == 200:
                    response = response.json()
                    models = [model["id"] for model in response["data"]]
                    return models
                else:
                    return []
        except Exception as e:
            logger.info("Error on get current model-list: ", e)
            return []

    async def unload_model(self):
        if not config_data["using_remoteapi"]:
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
                logger.info("Error on unloading model: ", e)
                return False
        else:
            return True

    async def load_model(
        self,
        name: str = "",
        max_seq_len: int = 4096,
        gpu_split_auto: bool = True,
        gpu_split: list = [0],
        prompt_template: str = None,
    ):
        if not config_data["using_remoteapi"]:
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
                            logger.info(f"The Gpu Split to: {gpu_split}")
                except Exception as e:
                    logger.info("Error during load GPU info: ", e)
                    self.model_load_data["gpu_split_auto"] = True

                self.model_load_data["prompt_template"] = prompt_template

                try:
                    response = await client.post(
                        url=url, headers=headers, json=self.model_load_data, timeout=timeout
                    )
                    if response.status_code == 200:
                        logger.info(f" Model Changed To: {name}")
                        return "Success"
                    else:
                        logger.info(" Model Load Failed")
                        return "Fail"
                except Exception as e:
                    logger.info("Error on load model: ", e)
        else:
            # url = self.url + "/OAI_Switch_Model"
            # await self.send_msg_websocket(
            #     {"name": "initialization", "msg": f"Loading Model: {name} ..."},
            #     self.conversation_id,
            # ) 
            # async with httpx.AsyncClient() as client:
            #     try:
            #         response = await client.post(url=url, json={"model": name}, timeout=timeout)
            #         if response.status_code == 200:
            #             logger.info(response.json()["message"])
            #             return "Success"
            #         else:
            #             logger.info(" Model Load Failed")
            #             return "Fail"
            #     except Exception as e:
            #         logger.info("Error on load model: ", e)
            return "Success"

    async def get_sd_model_list(self):
        url = config_data["SDAPI_url"]
        APIurl = f'{config_data["openai_api_chat_base"]}/SDapiModelList'
        headers = {
            # 'accept': 'application/json'
            "SD-URL": url
        }
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url=APIurl, headers=headers, timeout=timeout
                )
                response = response.json()
                model_list = []
                for model_name in response:
                    model_list.append(model_name["model_name"])
                # logger.info(f"SD Model List: {model_list}")
                return model_list
        except Exception as e:
            logger.info("Error on get SD model list: ", e)
            return None
        
    async def get_sd_vram_status(self):
        url = config_data["SDAPI_url"]
        APIurl = f'{config_data["openai_api_chat_base"]}/SDapiVRAMStatus'
        headers = {
            "SD-URL": url
        }
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url=APIurl, headers=headers, timeout=timeout
                )
                vram_status = response.json()
                return vram_status.get("vram_status", None)
        except Exception as e:
            logger.info("Error on get SD vram status: ", e)
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
                logger.info("Start to fetch TTS audio")
                start_time = time.perf_counter()
                response = await client.post(
                    url=url, headers=headers, json=payload, timeout=timeout
                )
                response.raise_for_status()
                end_time = time.perf_counter()
                total_run_time = end_time - start_time
                logger.info(f"TTS cost time: {total_run_time:.2f} seconds")
                audio_data_base64 = base64.b64encode(response.content).decode("utf-8")
        except Exception as e:
            logger.info(f"Error on get xtts audio: {e}")
            audio_data_base64 = False
        finally:
            return audio_data_base64

    @classmethod
    async def SD_image(
        cls,
        url: str = None,
        payload: dict = None,
        headers: dict = None,
        timeout=timeout,
        checkprocess: bool = True,
        task_flag: str = None,
        send_msg_websocket: callable = None,
        client_id: str = None,
    ):
        if headers is None:
            headers = {"SD-URL": f'{config_data["SDAPI_url"]}'}
        if url is None:
            url = f'{config_data["openai_api_chat_base"]}'
        if payload is None:
            payload = sd_payload
        process_payload = {"id_live_preview": -1, "live_preview": True}

        if checkprocess:
            task_id = str(uuid.uuid4())
            txt2img_payload = {"force_task_id": task_id, **payload}
            process_payload = {"id_task": task_id, **process_payload}
            result, result_process = await asyncio.gather(
                cls.SD_txt2img(
                    url=url, payload=txt2img_payload, headers=headers, timeout=timeout
                ),
                cls.SD_process(
                    url=url,
                    payload=process_payload,
                    headers=headers,
                    task_flag=task_flag,
                    timeout=timeout,
                    send_msg_websocket=send_msg_websocket,
                    client_id=client_id,
                ),
            )
        else:
            result = await cls.SD_txt2img(
                url=url, payload=payload, headers=headers, timeout=timeout
            )
        return result

    @classmethod
    async def SD_txt2img(
        cls,
        url: str = None,
        payload: dict = None,
        headers: dict = None,
        timeout=timeout,
    ):
        try:
            url = url + "/SDapi"
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url=url, json=payload, headers=headers, timeout=timeout
                )
                result = response.json()
                imgBase64 = result["images"][0]
                return imgBase64
        except Exception as e:
            logger.info(f"Error to generate SD img: {e}")

    @classmethod
    async def SD_process(
        cls,
        url: str = None,
        headers: dict = None,
        payload: dict = None,
        task_flag: str = None,
        timeout=timeout,
        send_msg_websocket: callable = None,
        client_id: str = None,
    ):
        url = url + "/check-progress"
        last_id_live_preview = -1
        preview_img_base64 = None
        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                async with client.stream(
                    "POST", url=url, json=payload, headers=headers
                ) as response:
                    pbar = tqdm(
                        range(100), desc=f"Generating Image", bar_format=COLORBAR
                    )
                    try:
                        async for line in response.aiter_lines():
                            if line is not None:
                                progress_info = json.loads(line)
                                if progress_info is not None:
                                    percentage = int(
                                        progress_info.get("progress", 0) * 100
                                    )
                                    pbar.n = percentage
                                    pbar.refresh()
                                    current_id_live_preview = progress_info.get(
                                        "id_live_preview", -1
                                    )
                                    if current_id_live_preview != -1:
                                        if (
                                            progress_info.get("live_preview")
                                            is not None
                                            and current_id_live_preview
                                            != last_id_live_preview
                                        ):
                                            uri = progress_info.get("live_preview")
                                            preview_img_base64 = uri  # .split(",")[1]　if only need base64 <data>
                                            last_id_live_preview = (
                                                current_id_live_preview
                                            )

                                    if (
                                        send_msg_websocket is not None
                                        and client_id is not None
                                    ):
                                        msgpack = {
                                            "event": "SD_Process_status",
                                            "percentage": percentage,
                                            "task_flag": task_flag,
                                            "preview_img_base64": preview_img_base64
                                            or "empty",
                                        }
                                        await send_msg_websocket(
                                            {"name": "SD_generation", "msg": msgpack},
                                            client_id,
                                        )
                                if progress_info.get("completed", False):
                                    pbar.close()
                                    return True
                    except Exception as e:
                        print(f"Error processing progress stream: {e}")
                        return None
            except Exception as e:
                logger.error(f"Error on SD process: {e}")
                return None

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
                ">",
                "。",
                "！",
                "？",
                "”",
                "`",
                ")",
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
        apiurl: str = None,
    ):
        data = payloads
        config_data = await getGlobalConfig("config_data")
        if config_data["using_remoteapi"] is True:
            apiurl = (
                config_data["openai_api_chat_base"]
                + "/remoteapi/"
                + config_data["remoteapi_endpoint"]
            )
            if "prompt" in data:
                del data["prompt"]
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    response = await client.post(url=apiurl, json=data)
                    if response.status_code == 200:
                        return response.text
                    else:
                        print(f"Request failed with status code {response.status_code}")
                        print(await response.aread())
            except Exception as e:
                logger.info("Error on inference from remote: ", e)

        else:
            apiurl = config_data["openai_api_chat_base"] + "/completions"
            headers = {
                "accept": "application/json",
                "x-api-key": api_key,
                "x-admin-key": admin_key,
                "Content-Type": "application/json",
            }
            # data.pop("model", None)
            if "system_prompt" in data:
                del data["system_prompt"]
            if "messages" in data:
                del data["messages"]
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    response = await client.post(url=apiurl, headers=headers, json=data)
                    if response.status_code == 200:
                        response = response.json()
                        return response["choices"][0]["text"]
                    else:
                        print(f"Request failed with status code {response.status_code}")
                        print(await response.aread())
            except Exception as e:
                logger.info("Error on inference: ", e)

    @staticmethod
    async def transcribe_audio(audio_data) -> str:
        url = config_data["openai_api_chat_base"] + "/stt_remote"
        headers = {"accept": "application/json"}
        payload = {"audio_data": audio_data}
        try:
            async with httpx.AsyncClient() as client:
                transcripted_text = await client.post(
                    url, json=payload, headers=headers, timeout=60
                )
                return transcripted_text.json().get("text", "Slients....")
        except Exception as e:
            print(f"Error on transcribe audio: {e}")
