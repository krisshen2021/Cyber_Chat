import sys
from pathlib import Path

project_root = str(Path(__file__).parents[1])


def create_syspath():
    if project_root not in sys.path:
        sys.path.append(project_root)


create_syspath()

import re, json
from modules.global_sets_async import getGlobalConfig, logger, languageClient
from fastapimode.tabby_fastapi_websocket import tabby_fastapi as tabby


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
    system_prompt = (
        f"You are a professional language translator, Base on the given json list, translate the texts to {target}, \n"
        + r"- Maintain astriks(*) in the texts, do not translate them.\n"
        + r"- Do NOT translate '{{char}}' and '{{user}}',\n"
        + r"- Do NOT translate any proper names in text, especially character names, for example, 'David' should be 'David',\n"
        + r"- Use very casual, everyday spoken language. Imagine you're talking to a friend,\n"
        + r'Finally, return a VALIAD and compliant json list with the same structure, the json list structure is: [{"index": original_index_number, "text": "translated_text"}], Output the josn list only, do not output any other text or json code block marks.'
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
    # Use internal api
    # payloads = {
    #     "prompt": prompt,
    #     "max_tokens": 2000,
    #     "temperature": 0.1,
    #     "top_p": 0.7,
    #     "stream": False,
    # }
    # logger.info(f"Translate prompt: {translater_prompt}")
    try:
        # result = await tabby.pure_inference(payloads=payloads)
        # logger.info(f"Translate result: {result}")
        result = await languageClient.chat.completions.create(
            model="gemma2-9b-it",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            stream=False,
            temperature=0.5,
        )
        result = result.choices[0].message.content
        # logger.info(f"Translate result: {result}")
        result = await convert_text(result)
        # 提取方括号中的内容
        outer_pattern = r"\{.*\}(?=[^\}]*\])"
        # (?=[^\}]*\]) 向前看，确保当前位置之后存在一系列非右花括号的字符（可以是零个或多个），然后是一个右方括号
        outer_match = re.search(outer_pattern, result, re.DOTALL)
        if outer_match:
            json_content = outer_match.group()
            # logger.info(f"Translate json_content: {json_content}")
            # 提取并处理每个对象
            object_pattern = r'\{"index":\s*(\d+),\s*"text":\s*"(.*?)"\}'

            def replace_func(match):
                # logger.info("match found!!!")
                index, text = match.groups()
                escaped_text = text.replace('"', "'").replace("\\*", "*").replace('\\','%').replace('%n','\\n').replace("%'","'")
                return f'{{"index":{index},"text":"{escaped_text}"}}'

            processed_content = re.sub(
                object_pattern, replace_func, json_content, flags=re.DOTALL
            )

            # 重建完整的 JSON 字符串
            rebuilt_json = f"[{processed_content}]"
            # logger.info(f"Translate rebuilt_json: {rebuilt_json}")

            try:
                parsed_result = json.loads(rebuilt_json)
                return parsed_result
            except json.JSONDecodeError as e:
                logger.error(f"Rebuilt JSON string: {rebuilt_json}")
                logger.error(f"JSON decode error: {e}")
                return json.loads(translater_prompt)
        else:
            logger.error("No JSON-like list found in the result")
            logger.error(f"Raw result: {result}")
            return json.loads(translater_prompt)

    except Exception as e:
        logger.error(f"An error occurred: {e}")
        return json.loads(translater_prompt)


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
    async def init(self):
        global config_data
        config_data = await getGlobalConfig('config_data')

    async def translate_text(self, target, text, prompt_template=None):
        # logger.info(f"current prompt template is : {prompt_template}")
        command_text = None
        if text is not None or text != "":
            text = text.strip()
            # logger.info(f"Text to translate: {text}")
            command_pattern = r"^(### Request to A.I assistant: )(.+)$"
            match = re.match(command_pattern, text, re.DOTALL)
            if match:
                command_text = match.group(1)
                text = match.group(2).strip()
                # logger.info(f"Command text: {command_text}, text:{text}")
            text_pattern_list = await extract_code_blocks(text)
            text_transtext_list = []
            texts_to_translate = []
            for item in text_pattern_list:
                text_transtext_list.append(item["text"])
            # logger.info(f"Text pattern list: {text_pattern_list}")
            for index, element in enumerate(text_pattern_list):
                if element["if_translated"] is True:
                    texts_to_translate.append({"index": index, "text": element["text"]})
            if len(texts_to_translate) > 0:
                translater_prompt = json.dumps(texts_to_translate, ensure_ascii=False)
                translated_json_list = await translate_ai_driven(
                    translater_prompt, target, prompt_template
                )
                # logger.info(f"Translated json list: {translated_json_list}")
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
    asyncio.run(mytrans.init())
    text = """
    here is the code you asked for:
    ```python
    def hello_world():
        print("Hello, World!")
    ```
    hope it helps!
    """
    result = asyncio.run(mytrans.translate_text("simplified chinese", text))
    logger.info(f"Translate result: {result}")
