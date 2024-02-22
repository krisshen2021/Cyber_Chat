#tabbyAPI_server Class
#link to server
from openai import OpenAI
from tabby_fastapi_server import tabby_fastapi
import requests, json, os, tiktoken, yaml, sys

dir_path = os.path.dirname(os.path.realpath(__file__))
#get models
def get_model_name(api_base:str,model_type:str, api_key:str, admin_key:str):
    headers = {
        'accept': 'application/json',
        'x-api-key': api_key,
        'x-admin-key': admin_key,
        'Content-Type': 'application/json'
    }
    try:
        response = requests.get(url=api_base+"/model",headers=headers)
        response.raise_for_status()
        if response.status_code == 200:
            datas = response.json()
            model_name=datas['id']
            return model_name
        else:
            print("请求失败，状态码：", response.status_code)
    except Exception as e:
        print(f"Error to get model from {api_base}, \nPlease set up the {model_type} model address in config.yml before chatting")
        return "NONE"
        # sys.exit(1)
        
        

#Load prompts for generating'
def load_prompts(file_path):
    yaml_file_path = os.path.join(dir_path, "config", "prompts", file_path)
    with open(yaml_file_path, 'r') as file:
        prompts_data = yaml.safe_load(file)
        restruct_prompt = prompts_data['restruct_prompt']
        prmopt_fixed_prefix = prompts_data['prmopt_fixed_prefix']
        prmopt_fixed_suffix = prompts_data['prmopt_fixed_suffix']
        nagetive_prompt = prompts_data['nagetive_prompt']
    return restruct_prompt, prmopt_fixed_prefix, prmopt_fixed_suffix, nagetive_prompt

#Load Words dictionary and sex result matching
def load_vocabulary(file_path):
    file_path = os.path.join(dir_path, "config", "match_words", file_path+".yaml")
    with open(file_path, 'r') as file:
        data = yaml.safe_load(file)
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
    return False,f"nothing matched, input string is: \"{input_string}\""


class tabbyAPI:
    def __init__(self, state:dict, image_payload:dict, send_msg_websocket: callable = None ) -> None:
        self.state = state
        self.send_msg_websocket = send_msg_websocket
        self.image_payload = image_payload
        self.conversation_id = self.state["conversation_id"]
        self.api_key = self.state["tappyapi_api_key"]
        self.admin_key = self.state["tappyapi_admin_key"]
        self.chat_model = get_model_name(self.state['openai_api_chat_base'],"Chat", self.api_key, self.admin_key)       
        self.funcall_model = get_model_name(self.state['openai_api_funcall_base'],"Funcall", self.api_key, self.admin_key)
        self.rephase_model = get_model_name(self.state['openai_api_rephase_base'],"Rephase", self.api_key, self.admin_key)
        print(f'Chat model: {self.chat_model} | Fun call model: {self.funcall_model} | Rephase model: {self.rephase_model}')
        self.vocabulary, self.resultslist, self.lora, self.summary_prompt = load_vocabulary(self.state['match_words_cata'])
        self.restruct_prompt, self.prmopt_fixed_prefix, self.prmopt_fixed_suffix, self.nagetive_prompt = load_prompts("prompts.yaml")
        self.restruct_prompt = self.restruct_prompt.replace('<|default_bg|>', self.state['env_setting'])
        self.inputmsg = ""
        self.tabby_server = tabby_fastapi(url=self.state['openai_api_chat_base'], api_key=self.api_key, admin_key=self.admin_key, conversation_id=self.conversation_id)

    def get_rephrase_template(self):
        chat_template_name = self.state["prompt_template"].split("_")
        rephrase_template_name = chat_template_name[0]+"_Rephrase"
        self.rephrase_template = self.state["prompts_templates"][rephrase_template_name]
        pass


    #Chat Block
    def get_chat_response(self, system_prompt:str, temperature=None ) -> str:
        if temperature is None:
            temperature = self.state["temperature"]
        response_text = self.tabby_server.remove_extra_punctuation(self.tabby_server.inference(
            prompt=system_prompt, 
            stop_token=self.state["custom_stop_string"], 
            temperature=temperature,
            temperature_last=self.state["temperature_last"],
            min_p=self.state["min_p"],
            tfs=self.state["tfs"],
            max_tokens=self.state["max_new_tokens"], 
            repetition_penalty=self.state["repetition_penalty"],
            frequency_penalty=self.state["frequency_penalty"],
            presence_penalty=self.state["presence_penalty"],
            mirostat_mode=self.state["mirostat_mode"]
            ))
        return response_text
    
    #Funcall Block   
    def get_func_response(self,user_msg:str, functions:list) -> str:

        try:
            client_funcall = OpenAI(
                api_key=self.api_key,
                base_url=self.state['openai_api_funcall_base'],
                )
            funcall_response = client_funcall.chat.completions.create(
            model=self.funcall_model,
            temperature=0.001,
            max_tokens=2000,
            messages=[
                {"role": "user", "content": user_msg},
                {"role": "functions", "content": json.dumps(functions)}
                ]
            )
            response_text = funcall_response.choices[0].message.content.strip()
            return response_text
        except Exception as e:
            print(e, user_msg)
        # client_funcall = OpenAI(
        #     api_key=openai_api_key,
        #     base_url=self.state['openai_api_funcall_base'],
        # )

        # funcall_response = client_funcall.chat.completions.create(
        #     model=self.funcall_model,
        #     max_tokens=1000,
        #     temperature=0.001,
        #     messages=[
        #         {"role": "system", "content": system_prompt},
        #         {"role": "user", "content": user_msg},
        #     ],
        #     stop=['Thought:']
        # )
        # response_text = funcall_response.choices[0].message.content.replace('Call: ','').strip()
        return response_text

    #Rephase Block
    def get_rephase_response(self,user_msg:str, system_prompt:str) -> str:
        if self.state['openai_api_rephase_base'] == self.state['openai_api_chat_base']:
            prompt = self.rephrase_template.replace(r"<|system_prompt|>", system_prompt).replace(r"<|user_prompt|>", user_msg)
            response_text = self.get_chat_response(system_prompt=prompt, temperature=0.001).strip()
            return response_text
        else:
            client_rephase = OpenAI(
                api_key=self.api_key,
                base_url=self.state['openai_api_rephase_base']
            )

            rephase_response = client_rephase.chat.completions.create(
                model=self.rephase_model,
                max_tokens=200,
                temperature=0.001,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_msg}
                    ]
            )
            response_text = rephase_response.choices[0].message.content.strip().replace('"','')
            return response_text

    #Generate Images!
    def generate_prompt_main(self, response_to_reprompt:str):
        system_prompt = self.restruct_prompt
        user_prompt = f'The subject needs to generate a final text2image prompt is: \"{response_to_reprompt}\"'
        response_text = self.get_rephase_response(system_prompt=system_prompt,user_msg=user_prompt)
        return response_text

    def generate_image(self,prompt_prefix="", char_looks="", prompt_main="", env_setting="", prompt_suffix="", lora_prompt=""):#call SD api.
        # print(f'the prompt to restruct is: {prompt_main}')
        if prompt_main != "":
            prompt_main = self.generate_prompt_main(prompt_main)
        prompt_api = f'{prompt_prefix}, {char_looks}, (({prompt_main})), {env_setting}, {lora_prompt}, {prompt_suffix}'
        # print(prompt_api)
        payload = {
            "hr_negative_prompt" : self.nagetive_prompt,
            "hr_prompt" : prompt_api,
            "hr_scale" : self.image_payload['hr_scale'],
            "hr_second_pass_steps" : self.image_payload['hr_second_pass_steps'],
            "seed" : self.image_payload['seed'],
            "enable_hr" : self.image_payload['enable_hr'],
            "width" : self.image_payload['width'],
            "height" : self.image_payload['height'],
            "hr_upscaler" : self.image_payload['hr_upscaler'],
            "negative_prompt" : self.nagetive_prompt,
            "prompt" : prompt_api,
            "sampler_name" : self.image_payload['sampler_name'],
            "cfg_scale" : self.image_payload['cfg_scale'],
            "denoising_strength" : self.image_payload['denoising_strength'],
            "steps" : self.image_payload['steps'],
            "override_settings" :{
                "sd_vae" : self.image_payload['override_settings']['sd_vae'],
                "sd_model_checkpoint": self.image_payload['override_settings']['sd_model_checkpoint']
                },
            "override_settings_restore_afterwards" : self.image_payload['override_settings_restore_afterwards']
        }
        SDurl = f'{self.state["SDAPI_url"]}/sdapi/v1/txt2img'
        tabbySDApi = f'{self.state["openai_api_chat_base"]}/SDapi'
        headers = {
            "SD-URL":SDurl
        }
        # response = requests.post(url=f'{self.state["SDAPI_url"]}/sdapi/v1/txt2img', json=payload)
        response = requests.post(url=tabbySDApi, json=payload, headers=headers)
        r = response.json()
        self.imgBase64 = r['images'][0]
        return self.imgBase64

    #Excutions !
    def generate_picture_by_sdapi(self, prompt:str="", loraword:str=""):
        recived_prompt = prompt
        lora_prompt = self.lora.get(loraword.strip(), "")
        if self.send_msg_websocket is not None:
            self.send_msg_websocket({"name":"chatreply","msg":"Generating Scene Image"}, self.conversation_id)
        print(">>>Generate Dynamic Picture\n")
        image = self.generate_image(prompt_prefix=self.prmopt_fixed_prefix, char_looks=self.state['char_looks'], prompt_main=recived_prompt, env_setting="", prompt_suffix=self.prmopt_fixed_suffix, lora_prompt=lora_prompt)
        return image
        
        # user_msg=f'Output your selection base on this context: \"{recived_prompt}\"'
        # response = self.get_rephase_response(system_prompt=system_prompt,user_msg=user_msg)
        # is_matched_se,final_response = contains_vocabulary(response, self.resultslist)
        # print(f"<{final_response}>")
        # if is_matched_se :
        #     lora_prompt = self.lora.get(final_response.strip(), "")
        #     if self.send_msg_websocket is not None:
        #         self.send_msg_websocket({"name":"chatreply","msg":"Generating Scene Image"}, self.conversation_id)
        #     print(">>>Generate Dynamic Picture\n")
        #     image = self.generate_image(prompt_prefix=self.prmopt_fixed_prefix, char_looks=self.state['char_looks'], prompt_main=recived_prompt, env_setting="", prompt_suffix=self.prmopt_fixed_suffix, lora_prompt=lora_prompt)
        #     return image
        # else:
        #     return False


    #Block for funcation call
    def get_funcall_result(self, user_prompt):
        functions = [
        {
            "name": "LLM chat",
            "api_name": "self.Chat_with_LLM",
            "description": "Using LLM to Generate a response according to input words",
            "parameters": [{"name": "words", "description": "String type, the full & raw words from input (full texts & raw format, do not break it.)"}]
        },
        
        {
            "name": "Picture generator",
            "api_name": "self.generate_picture_by_sdapi",
            "description": "Generate a picture base on the full & raw input prompt then SEND to user",
            "parameters": [{"name": "prompt", "description": "String type, the full & raw texts for generating picture"}]
        }
        ]
        response = self.get_func_response(user_msg=user_prompt, functions=functions)
        # RAVEN_PROMPT = \
        # '''
        # Function:
        # def Chat_with_LLM(words):
        #     """
        #     Chat with LLM as default function overall, send words to LLM and return response from LLM

        #     Args:
        #     words (str): The words text, Raw String only.

        #     Returns:
        #     str: The reply message from LLM
        #     """

        # Function:
        # def generate_picture_by_sdapi(prompt):
        #     """
        #     Generate picture based on given prompt

        #     Args:
        #     prompt (str): The prompt text, Raw String only.

        #     Returns:
        #     String: the Base64 image encoded string
        #     """

        # '''

        # response = self.get_func_response(user_msg=user_prompt, system_prompt=RAVEN_PROMPT)
        return response
        

    #Block for chat
#    
    def Chat_with_LLM(self, words:str):
        system_prompt=self.inputmsg
        response_text = self.get_chat_response(system_prompt=system_prompt).strip()
        if self.state['generate_dynamic_picture'] is True:
            user_msg=f'Output your selection base on this context: \"{response_text}\"'
            response = self.get_rephase_response(system_prompt=self.summary_prompt,user_msg=user_msg)
            print(f">>>The rephase result is {response}")
            is_word_triggered, match_result = contains_vocabulary(response, self.resultslist)
            # is_word_triggered, match_word = contains_vocabulary(response_text, self.vocabulary)
            if is_word_triggered is True :
                print(f">>>Matched result is: {match_result}")
                text_to_image = response_text.replace("\n",".").strip()
                result_picture = self.generate_picture_by_sdapi(prompt=text_to_image,loraword=match_result)
                return response_text, result_picture
            else:
                return response_text, False

        else:
            return response_text, False
        

    def fetch_results(self, inputmsg:str, user_last_msg:str):
           
        try:
            self.user_last_msg = user_last_msg.replace("'","\\'").replace('"','\\"')
            self.inputmsg = inputmsg
            # cmd = self.get_funcall_result(f'USER:{self.user_last_msg}')
            # print(cmd)
            # result = eval(cmd)
            result = self.Chat_with_LLM(inputmsg)
            # print(type(result))
        except Exception as e:
            # 处理 eval 过程中可能发生的错误
            print(f"Error during eval: {e}")
            return None, None

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
    
    def count_token_numbers(self, string: str) -> int:
        """Returns the number of tokens in a text string."""
        encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
        num_tokens = len(encoding.encode(string))
        return num_tokens



