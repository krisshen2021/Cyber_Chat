import chromadb
import os
import yaml
from chromadb.config import Settings
from chromadb.utils import embedding_functions
from deep_translator import GoogleTranslator

sentence_transformer_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="paraphrase-multilingual-mpnet-base-v2"
)
dir_path = os.path.dirname(os.path.realpath(__file__))
config_path = os.path.join(dir_path, 'config', 'config.yml')
with open(config_path, 'r') as file:
    config_data = yaml.safe_load(file)
chroma_client = chromadb.Client(
    Settings(
        chroma_api_impl="rest",
        chroma_server_host=config_data["chroma_server_host"],
        chroma_server_http_port=config_data["chroma_server_http_port"],
    )
)


class chroma_embedding:
    def __init__(self, collection_name="mygpt"):
        self.collection_name = collection_name
        self.collection = chroma_client.get_collection(
            name=self.collection_name, embedding_function=sentence_transformer_ef
        )

    def queryEmb(self, qstr):
        qstr = GoogleTranslator(source="zh-CN", target="en").translate(qstr)
        qresult = self.collection.query(query_texts=[qstr], n_results=2)
        answers = []
        for answer in qresult["documents"][0]:
            answers.append(answer)
        embstr = ";".join(answers)
        prompt_request = f"%embeddings_start% {embstr} %embeddings_end% \n基于以上给到的参考内容，我的问题是: {qstr}"
        return prompt_request
