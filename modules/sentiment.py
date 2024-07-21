import torch, asyncio, os
from huggingface_hub import snapshot_download
from transformers import DistilBertTokenizer, DistilBertForSequenceClassification
#download model and tokenizer
repo_id = "distilbert-base-uncased-finetuned-sst-2-english"
locals_dir = "./config/sentimodel/"+repo_id
revision = "main"
if not os.path.exists(locals_dir):
    snapshot_download(repo_id=repo_id, local_dir=locals_dir, revision=revision)
#load model and tokenizer
tokenizer = DistilBertTokenizer.from_pretrained(locals_dir)
model = DistilBertForSequenceClassification.from_pretrained(locals_dir)

class SentimentAnalyzer:
    @staticmethod
    async def get_sentiment(text):
        inputs = tokenizer(text, return_tensors="pt")
        with torch.no_grad():
            logits = model(**inputs).logits

        predicted_class_id = logits.argmax().item()
        result = model.config.id2label[predicted_class_id]
        return result

SentiAna = SentimentAnalyzer()

if __name__ == "__main__":
    print(asyncio.run(SentiAna.get_sentiment("I hate you")))