import requests

class tabby_fastapi:
    def __init__(self, url: str = "", api_key: str = "", admin_key: str = "", conversation_id:str="" ) -> None:
        self.conversation_id = conversation_id
        self.url = url
        self.headers = {
            'accept': 'application/json',
            'x-api-key': api_key,
            'x-admin-key': admin_key,
            'Content-Type': 'application/json'
        }
        self.completions_data = {
            # "model": "",
            # "best_of": 0,
            # "echo": False,
            # "logprobs": 0,
            # "n": 1,
            # "suffix": "string",
            # "user": "string",
            "stream": False,
            "stop": ['###'],
            "max_tokens": 150,
            "token_healing": True,
            "temperature": 1,
            "temperature_last": True,
            "top_k": 0,
            "top_p": 1,
            "top_a": 0,
            "typical": 1,
            "min_p": 0,
            "tfs": 0.95,
            "frequency_penalty": 0,
            "presence_penalty": 0,
            "repetition_penalty": 1,
            "repetition_decay": 0,
            "mirostat_mode": 0,
            "mirostat_tau": 1.5,
            "mirostat_eta": 0.1,
            "add_bos_token": True,
            "ban_eos_token": False,
            "repetition_range": -1,
            "prompt": ""
        }
        self.model_load_data = {
            "name": "",
            "max_seq_len": 4096,
            # "override_base_seq_len": 0,
            "gpu_split_auto": True,
            "gpu_split": [
                0
            ],
            # "rope_scale": 1,
            # "rope_alpha": 0,
            "no_flash_attention": False,
            "cache_mode": "FP16",
            "prompt_template": "string",
            # "num_experts_per_token": 0,
            # "draft": {
            #     "draft_model_name": "string",
            #     "draft_rope_scale": 1,
            #     "draft_rope_alpha": 0
            # }
        }
        pass

    def inference(self, prompt: str = "", max_tokens: int = 300, stop_token: list = ["###"], temperature: float = 0.7, repetition_penalty: float = 1.1, frequency_penalty:float = 0.0, presence_penalty:float = 0.0, temperature_last: bool = True, min_p: float = 0.05, tfs: float = 1, mirostat_mode: int = 0):
        url = self.url+'/completions'
        headers = self.headers
        # data = copy.deepcopy(self.completions_data)
        self.completions_data["prompt"] = prompt
        self.completions_data["max_tokens"] = max_tokens
        self.completions_data["temperature"] = temperature
        self.completions_data["repetition_penalty"] = repetition_penalty
        self.completions_data["frequency_penalty"] = frequency_penalty
        self.completions_data["presence_penalty"] = presence_penalty
        self.completions_data["temperature_last"] = temperature_last
        self.completions_data["min_p"] = min_p
        self.completions_data["tfs"] = tfs
        self.completions_data["stop"] = stop_token
        self.completions_data["mirostat_mode"] = mirostat_mode
        # self.completions_data["model"] = self.get_model()
        response = requests.post(url, headers=headers,
                                 json=self.completions_data).json()
        return response['choices'][0]['text']

    def get_model(self):
        url = self.url+'/model'
        headers = self.headers
        try:
            response = requests.get(url, headers=headers).json()
            return response["id"]
        except Exception as e:
            print("Error on get current model: ", e)
            return "None"
            

    def get_model_list(self) -> list:
        url = self.url+'/models'
        headers = self.headers
        try:
            response = requests.get(url, headers=headers).json()
            models = []
            for model in response["data"]:
                models.append(model["id"])
            return models
        except Exception as e:
            print("Error on get current model-list: ", e)
            return []

    def unload_model(self):
        url = self.url+"/model/unload"
        headers = self.headers
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                return response
            elif response.status_code == 405:
                response = requests.post(url, headers=headers)
                if response.status_code == 200:
                    return response
        except Exception as e:
            print("Error on get current model-list: ", e)
            return False

    def load_model(self, name: str = "", max_seq_len: int = 4096, gpu_split_auto: bool = True, gpu_split: list = [0], prompt_template: str = None, send_msg_websocket: callable = None):
        # Then load the model
        url = self.url+"/model/load"
        headers = self.headers
        # data = copy.deepcopy(self.model_load_data)
        self.model_load_data["name"] = name
        self.model_load_data["max_seq_len"] = max_seq_len
        if send_msg_websocket is not None:
            send_msg_websocket({"name":"initialization","msg":f"Loading Model: {name} ..."}, self.conversation_id)
        try:
            gpu_info = requests.get(self.url+'/gpu',headers=headers)
            if gpu_info.status_code == 200:
                gpu_info = gpu_info.json()
                if gpu_info["GPU Count"]==1:
                    self.model_load_data["gpu_split_auto"] = True
                else:
                    self.model_load_data["gpu_split_auto"] = False
                    gpu_split = []
                    for gpu in gpu_info["GPU Info"]:
                        gpu_split.append(int(gpu["GPU_Memory"]*0.7))
                    self.model_load_data["gpu_split"] = gpu_split
                    print(f"The Gpu Split to: {gpu_split}")
        except Exception as e:
            print("Error during load GPU info: ",e)
            self.model_load_data["gpu_split_auto"] = True

        self.model_load_data["prompt_template"] = prompt_template
        response = requests.post(
            url=url, headers=headers, json=self.model_load_data)
        if response.status_code == 200:
            # if send_msg_websocket is not None:
            #     send_msg_websocket({"name":"initialization","msg":"DONE"}, self.conversation_id)
            print(f">>> Model Changed To: {name}")
            return "Success"
        else:
            print(">>> Model Load Failed")
            return "Fail"

    def remove_extra_punctuation(self, text):
        end_punctuation = ['.', '!', '?', '…', '*', '"','```']
        if text[-1] not in end_punctuation:
            for i in range(len(text)-1, -1, -1):
                if text[i] in end_punctuation:
                    text = text[:i+1]
                    break
        return text
