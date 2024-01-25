import requests, uuid

key = 'd7f0555229ed46c2b3d7024c1edba578'
endpoint = "https://api.cognitive.microsofttranslator.com"
location = "eastasia"

path = '/translate'
constructed_url = endpoint + path
headers = {
    'Ocp-Apim-Subscription-Key': key,
    'Ocp-Apim-Subscription-Region': location,
    'Content-type': 'application/json',
    'X-ClientTraceId': str(uuid.uuid4())
}
class azuretransClass:
    def __init__(self) -> None:
        pass
    def translate_text(self, to_locaiton:str, text_to_trans:str) -> str:
        self.text_to_trans = text_to_trans
        self.to_locaiton = to_locaiton
        params = {
            'api-version': '3.0',
            'to': [self.to_locaiton]
        }
        body = [{
            'text': self.text_to_trans
        }]
        request = requests.post(constructed_url, params=params, headers=headers, json=body)
        response = request.json()[0]['translations'][0]['text']
        return response