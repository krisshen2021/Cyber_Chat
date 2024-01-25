import deepl

auth_key = "ad825890-f2ec-e896-fd44-e278b02ee079:fx" 
translator = deepl.Translator(auth_key)

class deepltransClass:
    def __init__(self) -> None:
        pass

    def translate_text(self,target: str, text: str) -> str:
        result = translator.translate_text(text=text, target_lang=target, split_sentences="nonewlines", preserve_formatting=True)
        print(result.text)
        return result.text
