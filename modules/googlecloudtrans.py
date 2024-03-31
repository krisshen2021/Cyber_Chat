import re
import requests,os
api_key = os.getenv("Google_API_Key")
headers = {
    "X-goog-api-key": api_key,
    "Content-Type": "application/json; charset=utf-8"
}
def googletranslate(query_list, target):
    data = {
        "q": query_list,
        "target": target,
        "format": "text"
    }
    response = requests.post(
        "https://translation.googleapis.com/language/translate/v2",
        headers=headers,
        json=data
    ).json()
    translatedList = []
    for result in response["data"]["translations"]:
        translatedList.append(result['translatedText'])
    return translatedList

def extract_code_blocks(text):
    pattern = r'(```.*?```)'
    parts = re.split(pattern, text, flags=re.DOTALL)
    result = []
    for part in parts:
        if part.strip():
            if re.match(pattern, part, flags=re.DOTALL):
                result.append({"text": part, "if_translated": False})
            else:
                result.append({"text": part, "if_translated": True})
    return result
class googletransClass:
    def __init__(self) -> None:
        pass
    def translate_text(self,target,text):
        text_pattern_list = extract_code_blocks(text)
        text_transtext_list = []
        for item in text_pattern_list:
            text_transtext_list.append(item["text"])
        trans_result_list = googletranslate(text_transtext_list,target)
        for index, element in enumerate(text_pattern_list):
            if element["if_translated"] is False:
                trans_result_list[index]=text_pattern_list[index]['text']
        finalResult = ''.join(trans_result_list)
        return finalResult
