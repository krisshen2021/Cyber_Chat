import sys
from pathlib import Path

project_root = str(Path(__file__).parents[1])


def create_syspath():
    if project_root not in sys.path:
        sys.path.append(project_root)


create_syspath()

import re, logging, json
from modules.global_sets_async import getGlobalConfig
from fastapimode.tabby_fastapi_websocket import tabby_fastapi as tabby

config_data:dict
def convert_punctuation(match):
    punctuation_map = {
        "，": ",",
        "。": ".",
        "！": "!",
        "？": "?",
        "；": ";",
        "：": ":",
        "“": '"',
        "”": '"',
        "‘": "'",
        "’": "'",
        "（": "(",
        "）": ")",
        "【": "[",
        "】": "]",
        "《": "<",
        "》": ">",
        "、": ",",
        "…": "...",
        "－": "-",
        "～": "~",
        "＊": "*",
    }
    char = match.group(0)
    return punctuation_map.get(char, char)


async def convert_text(text):
    pattern = "[，。！？；：“”‘’（）【】《》、…－～＊]"
    return re.sub(pattern, convert_punctuation, text)


async def translate_ai_driven(translater_prompt, target, prompt_template):
    config_data = await getGlobalConfig('config_data')
    system_prompt = (
        f"You are a professional language translator, Base on the given json list, translate the texts to {target}, "
        + "1. Maintain astriks(*) in the texts, never replace/translate/remove them, \n "
        + "2. Refine each translated text to make it more conversational and natural in the target language,\n"
        + "3. if the target language is Simplified Chinese, Use very casual, everyday spoken language. Imagine you're talking to a friend,\n"
        + 'Finally, return a valid json list with the same structure, the json list structure is: [{"index": original_index_number, "text": "translated_text"}], output the josn list only, do not output any other text or json code block marks.'
    )
    user_prompt = (
        f"The given json list is: \n{translater_prompt}\n, the result will be:"
    )
    if config_data["using_remoteapi"] is True:
        prompt = system_prompt + "\n" + user_prompt
    else:
        prompt = prompt_template.replace("<|system_prompt|>", system_prompt).replace(
            "<|user_prompt|>", user_prompt
        )
    payloads = {
        "prompt": prompt,
        "max_tokens": 2000,
        "temperature": 0.1,
        "top_p": 0.7,
        "stream": False,
    }
    # logging.info(f"Translate prompt: {prompt}")
    try:
        result = await tabby.pure_inference(payloads=payloads)
        # logging.info(f"Translate result: {result}")
        result = await convert_text(result)
        # 提取方括号中的内容
        outer_pattern = r"\{.*\}(?=[^\}]*\])"
        # (?=[^\}]*\]) 向前看，确保当前位置之后存在一系列非右花括号的字符（可以是零个或多个），然后是一个右方括号
        outer_match = re.search(outer_pattern, result, re.DOTALL)
        if outer_match:
            json_content = outer_match.group()
            # logging.info(f"Translate json_content: {json_content}")
            # 提取并处理每个对象
            object_pattern = r'\{"index":\s*(\d+),\s*"text":\s*"(.*?)"\}'

            def replace_func(match):
                # logging.info("match found!!!")
                index, text = match.groups()
                escaped_text = text.replace('"', "'").replace("\\*", "*")
                return f'{{"index":{index},"text":"{escaped_text}"}}'

            processed_content = re.sub(
                object_pattern, replace_func, json_content, flags=re.DOTALL
            )

            # 重建完整的 JSON 字符串
            rebuilt_json = f"[{processed_content}]"
            logging.info(f"Translate rebuilt_json: {rebuilt_json}")

            try:
                parsed_result = json.loads(rebuilt_json)
                return parsed_result
            except json.JSONDecodeError as e:
                logging.error(f"Rebuilt JSON string: {rebuilt_json}")
                logging.error(f"JSON decode error: {e}")
                raise ValueError("Failed to parse rebuilt JSON string") from e
        else:
            logging.error("No JSON-like list found in the result")
            logging.error(f"Raw result: {result}")
            raise ValueError("No valid JSON list found in the translation result")

    except Exception as e:
        logging.error(f"An error occurred: {e}")
        raise


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
        command_text = None
        if text is not None or text != "":
            text = text.strip()
            # logging.info(f"Text to translate: {text}")
            command_pattern = r"^(### Request to A.I assistant: )(.+)$"
            match = re.match(command_pattern, text, re.DOTALL)
            if match:
                command_text = match.group(1)
                text = match.group(2).strip()
                # logging.info(f"Command text: {command_text}, text:{text}")
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
                translated_json_list = await translate_ai_driven(
                    translater_prompt, target, prompt_template
                )
                # logging.info(f"Translated json list: {translated_json_list}")
                for index, text in enumerate(text_transtext_list):
                    for item in translated_json_list:
                        if item["index"] == index:
                            text_transtext_list[index] = item["text"]
                finalResult = "\n".join(text_transtext_list)
                if command_text is not None:
                    finalResult = command_text + finalResult
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
