import sys
from pathlib import Path

project_root = str(Path(__file__).parents[1])


def create_syspath():
    if project_root not in sys.path:
        sys.path.append(project_root)


create_syspath()

import re, logging, json
from modules.global_sets_async import config_data
from fastapimode.tabby_fastapi_websocket import tabby_fastapi as tabby


async def translate_ai_driven(translater_prompt, target, prompt_template):
    system_prompt = f"You are a professional language translator, Base on the given json list, translate the texts to {target}, " + 'maintaining the original punctuation in the texts, and return a json list with the same structure. The json list structure is as follows: [{"index": 0, "text": "text to translate"}, {"index": 1, "text": "text to translate"}], output the josn list only, do not output any other text or json code block marks.'
    user_prompt = f"The json list is: \n{translater_prompt}\n"
    if config_data["using_remoteapi"] is True:
        prompt = system_prompt + "\n" + user_prompt
    else:
        prompt = prompt_template.replace("<|system_prompt|>", system_prompt).replace("<|user_prompt|>", user_prompt)
    payloads = {
        "prompt": prompt,
        "max_tokens": 500,
        "temperature": 0.1,
        "top_p": 0.95,
        "stream": False,
    }
    # logging.info(f"Translate prompt: {prompt}")
    try:
        result = await tabby.pure_inference(payloads=payloads)
        # logging.info(f"Translate result: {result}")
        result = json.loads(result)
        return result
    except Exception as e:
        logging.info("Error on inference: ", e)


async def extract_code_blocks(text):
    pattern = r"(```.*?```)"
    parts = re.split(pattern, text, flags=re.DOTALL)
    result = []
    for part in parts:
        if part.strip():
            if re.match(pattern, part, flags=re.DOTALL):
                result.append({"text": part, "if_translated": False})
            else:
                result.append({"text": part, "if_translated": True})
    return result


class AsyncTranslator:
    def __init__(self) -> None:
        pass

    async def translate_text(self, target, text, prompt_template=None):
        # logging.info(f"current prompt template is : {prompt_template}")
        if text is not None or text != "":
            text_pattern_list = await extract_code_blocks(text)
            text_transtext_list = []
            texts_to_translate = []
            for item in text_pattern_list:
                text_transtext_list.append(item["text"])
            # logging.info(f"Text pattern list: {text_pattern_list}")
            for index, element in enumerate(text_pattern_list):
                if element["if_translated"] is True:
                    texts_to_translate.append({"index": index, "text": element["text"]})
            if len(texts_to_translate) > 0:
                translater_prompt = json.dumps(texts_to_translate, ensure_ascii=False)
                translated_json_list = await translate_ai_driven(translater_prompt, target, prompt_template)
                for index, text in enumerate(text_transtext_list):
                    for item in translated_json_list:
                        if item["index"] == index:
                            text_transtext_list[index] = item["text"]
                finalResult = "\n".join(text_transtext_list)
                return finalResult
            else:
                return text
        else:
            return "Empty"
        
        
        
        
if __name__ == "__main__":
    import asyncio
    mytrans = AsyncTranslator()
    text = """
    here is the code you asked for:
    ```python
    def hello_world():
        print("Hello, World!")
    ```
    hope it helps!
    """
    result = asyncio.run(mytrans.translate_text("simplified chinese", text))
    logging.info(f"Translate result: {result}")
