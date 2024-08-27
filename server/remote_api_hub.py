import cohere, asyncio, json, os, boto3
from modules.colorlogger import logger
from dotenv import load_dotenv
from pydantic import BaseModel
from typing import List, Optional
from openai import AsyncOpenAI, OpenAI


load_dotenv()

# api keys for different remote api
cohere_api_key = os.getenv("cohere_api_key", default="None")
mistral_api_key = os.getenv("mistral_api_key", default="None")
deepseek_api_key = os.getenv("deepseek_api_key", default="None")
togetherai_api_key = os.getenv("togetherai_api_key", default="None")
yi_api_key = os.getenv("yi_api_key", default="None")
nvidia_api_key = os.getenv("nvidia_api_key", default="None")
boto3_aws_access_key_id = os.getenv("boto3_aws_access_key_id", default="None")
boto3_aws_secret_access_key = os.getenv("boto3_aws_secret_access_key", default="None")
boto3_aws_region_name = os.getenv("boto3_aws_region_name", default="global")
xiaoai_api_key = os.getenv("xiaoai_api_key", default="None")
openrouter_api_key = os.getenv("openrouter_api_key", default="None")
groq_api_key = os.getenv("groq_api_key", default="None")
tabby_api_key = os.getenv("tabby_api_key", default="None")
aws_bedrock_config = {
    "region_name": boto3_aws_region_name,
    "aws_access_key_id": boto3_aws_access_key_id,
    "aws_secret_access_key": boto3_aws_secret_access_key,
}

# create config json for all remote api
remote_OAI_config = {
    "mistral": {"api_key": mistral_api_key, "url":"https://api.mistral.ai/v1"},
    "deepseek": {"api_key": deepseek_api_key, "url":"https://api.deepseek.com/v1"},
    "yi": {"api_key": yi_api_key, "url":"https://api.01.ai/v1"},
    "nvidia": {"api_key": nvidia_api_key, "url":"https://integrate.api.nvidia.com/v1"},
    "xiaoai": {"api_key": xiaoai_api_key, "url":"https://api.xiaoai.plus/v1"},
    "openrouter": {"api_key": openrouter_api_key, "url": "https://openrouter.ai/api/v1"},
    "groq": {"api_key": groq_api_key, "url": "https://api.groq.com/openai/v1"},
    "ollama": {"api_key":"ollama","url": "http://localhost:11434/v1"},
    "tabby": {"api_key":tabby_api_key,"url": "http://localhost:5555/v1"},
}


# api clients for different remote api
cohere_client = cohere.AsyncClient(api_key=cohere_api_key, timeout=120)

mistral_client = AsyncOpenAI(
    api_key=mistral_api_key, base_url="https://api.mistral.ai/v1", timeout=120
)
deepseek_client = AsyncOpenAI(
    api_key=deepseek_api_key, base_url="https://api.deepseek.com", timeout=120
)
togetherai_client = AsyncOpenAI(
    api_key=togetherai_api_key, base_url="https://api.together.xyz/v1", timeout=120
)
yi_client = AsyncOpenAI(
    api_key=yi_api_key, base_url="https://api.01.ai/v1", timeout=120
)
nvidia_client = AsyncOpenAI(
    api_key=nvidia_api_key, base_url="https://integrate.api.nvidia.com/v1", timeout=120
)
bedrock_client = boto3.client(service_name="bedrock-runtime", **aws_bedrock_config)
xiaoai_client = AsyncOpenAI(
    api_key=xiaoai_api_key, base_url="https://api.xiaoai.plus/v1", timeout=120
)
openairouter_client = AsyncOpenAI(
    api_key=openrouter_api_key, base_url="https://openrouter.ai/api/v1", timeout=600
)
openairouter_sync_client = OpenAI(
    api_key=openrouter_api_key, base_url="https://openrouter.ai/api/v1", timeout=600
)
sentenceCompletion_client = AsyncOpenAI(base_url="http://localhost:11434/v1", timeout=120, api_key="ollama")
# Pydantic models for different remote api params
class ChatMessage(BaseModel):
    role: str
    content: str | List


class OAIParam(BaseModel):
    messages: List[ChatMessage]
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    presence_penalty: Optional[float] = None
    top_p: Optional[float] = None
    stop: Optional[List[str]] = None
    model: str
    stream: Optional[bool] = True

class sentenceCompletionParam(OAIParam):
    model: Optional[str] = "gemma2-9b" # "gemma-2-uncensored" "gemma2-9b" "llama3-1-uncensored"
    stream: Optional[bool] = False
    max_tokens: Optional[int] = 200
    temperature: Optional[float] = 0.5
    
class XiaoaiParam(OAIParam):
    model: Optional[str] = "gpt-4o"

class CohereParam(BaseModel):  # for cohere
    preamble: Optional[str] = None
    message: str
    temperature: Optional[float] = None
    model: Optional[str] = "command-r-plus"
    max_tokens: Optional[int] = None
    presence_penalty: Optional[float] = None
    raw_prompting: Optional[bool] = False
    p: Optional[float] = None
    stop_sequences: Optional[List[str]] = None


class MistralParam(BaseModel):
    messages: List[ChatMessage]
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    top_p: Optional[float] = None
    presence_penalty: Optional[float] = None
    stop: Optional[List[str]] = None
    model: Optional[str] = "mistral-large-latest"
    stream: Optional[bool] = True


class DeepseekParam(BaseModel):
    messages: List[ChatMessage]
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    presence_penalty: Optional[float] = None
    top_p: Optional[float] = None
    stop: Optional[List[str]] = None
    model: Optional[str] = "deepseek-chat"
    stream: Optional[bool] = True


class TogetherAiParam(BaseModel):
    messages: List[ChatMessage]
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    presence_penalty: Optional[float] = None
    top_p: Optional[float] = None
    stop: Optional[List[str]] = None
    model: Optional[str] = "NousResearch/Nous-Hermes-2-Mixtral-8x7B-DPO"
    stream: Optional[bool] = True


class YiParam(BaseModel):
    messages: List[ChatMessage]
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    presence_penalty: Optional[float] = None
    top_p: Optional[float] = None
    stop: Optional[List[str]] = None
    model: Optional[str] = "yi-large"
    stream: Optional[bool] = True


class NvidiaParam(BaseModel):
    messages: List[ChatMessage]
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    presence_penalty: Optional[float] = None
    top_p: Optional[float] = None
    stop: Optional[List[str]] = None
    model: Optional[str] = "nvidia/nemotron-4-340b-instruct"
    stream: Optional[bool] = True


class ClaudeParam(BaseModel):
    anthropic_version: Optional[str] = "bedrock-2023-05-31"
    max_tokens: int = 200
    messages: List[ChatMessage]
    system: Optional[str] = None
    stop: Optional[List[str]] = None
    temperature: Optional[float] = None
    top_k: Optional[int] = None
    top_p: Optional[float] = None
    model: Optional[str] = "anthropic.claude-3-5-sonnet-20240620-v1:0"


async def OAI_stream(base_url: str, api_key: str, params: OAIParam):
    final_text = ""
    oai_client = AsyncOpenAI(api_key=api_key, base_url=base_url, timeout=120)
    data = params.model_dump(exclude_none=True, exclude_unset=True)

    async for chunk in await oai_client.chat.completions.create(**data, stream=True):
        if chunk.choices[0].finish_reason is None:
            if chunk.choices[0].delta.content:
                msg = json.dumps(
                    {
                        "event": "text-generation",
                        "text": chunk.choices[0].delta.content,
                    }
                )
                final_text += chunk.choices[0].delta.content
                yield msg
                await asyncio.sleep(0.01)
            else:
                continue
        elif chunk.choices[0].finish_reason is not None:
            msg = json.dumps(
                {
                    "event": "stream-end",
                    "finish_reason": chunk.choices[0].finish_reason,
                    "final_text": final_text,
                }
            )
            yield msg


async def cohere_stream(params: CohereParam):
    data = params.model_dump(exclude_none=True)
    async for event in cohere_client.chat_stream(**data):
        if event.event_type == "text-generation":
            msg = json.dumps(
                {
                    "event": "text-generation",
                    "text": event.text,
                }
            )
            yield msg
            await asyncio.sleep(0.01)
        elif event.event_type == "stream-end":
            msg = json.dumps(
                {
                    "event": "stream-end",
                    "finish_reason": event.finish_reason,
                    "final_text": event.response.text,
                }
            )
            yield msg


async def cohere_invoke(params: CohereParam):
    data = params.model_dump(exclude_none=True)
    if "stream" in data:
        data.pop("stream")
    resp = await cohere_client.chat(**data)
    return resp.text


async def mistral_stream(params: MistralParam):
    final_text = ""
    data = params.model_dump(exclude_none=True)
    async for chunk in await mistral_client.chat.completions.create(**data):
        if chunk.choices[0].finish_reason is None:
            if chunk.choices[0].delta.content:
                msg = json.dumps(
                    {
                        "event": "text-generation",
                        "text": chunk.choices[0].delta.content,
                    }
                )
                final_text += chunk.choices[0].delta.content
                yield msg
                await asyncio.sleep(0.01)
            else:
                continue
        elif chunk.choices[0].finish_reason is not None:
            msg = json.dumps(
                {
                    "event": "stream-end",
                    "finish_reason": chunk.choices[0].finish_reason,
                    "final_text": final_text,
                }
            )
            yield msg


async def mistral_invoke(params: MistralParam):
    data = params.model_dump(exclude_none=True)
    resp = await mistral_client.chat.completions.create(**data)
    return resp.choices[0].message.content


async def deepseek_stream(params: DeepseekParam):
    final_text = ""
    data = params.model_dump(exclude_none=True)
    async for chunk in await deepseek_client.chat.completions.create(**data):
        if chunk.choices[0].finish_reason is None:
            if chunk.choices[0].delta.content:
                msg = json.dumps(
                    {
                        "event": "text-generation",
                        "text": chunk.choices[0].delta.content,
                    }
                )
                final_text += chunk.choices[0].delta.content
                yield msg
                await asyncio.sleep(0.01)
            else:
                continue
        elif chunk.choices[0].finish_reason is not None:
            msg = json.dumps(
                {
                    "event": "stream-end",
                    "finish_reason": chunk.choices[0].finish_reason,
                    "final_text": final_text,
                }
            )
            yield msg


async def deepseek_invoke(params: DeepseekParam):
    data = params.model_dump(exclude_none=True)
    resp = await deepseek_client.chat.completions.create(**data)
    return resp.choices[0].message.content


async def togetherAi_stream(params: TogetherAiParam):
    final_text = ""
    data = params.model_dump(exclude_none=True)
    async for chunk in await togetherai_client.chat.completions.create(**data):
        if chunk.choices[0].finish_reason is None:
            if chunk.choices[0].delta.content:
                msg = json.dumps(
                    {
                        "event": "text-generation",
                        "text": chunk.choices[0].delta.content,
                    }
                )
                final_text += chunk.choices[0].delta.content
                yield msg
                await asyncio.sleep(0.01)
            else:
                continue
        elif chunk.choices[0].finish_reason is not None:
            msg = json.dumps(
                {
                    "event": "stream-end",
                    "finish_reason": chunk.choices[0].finish_reason,
                    "final_text": final_text,
                }
            )
            yield msg


async def togetherAi_invoke(params: TogetherAiParam):
    data = params.model_dump(exclude_none=True)
    resp = await togetherai_client.chat.completions.create(**data)
    return resp.choices[0].message.content


async def yiAi_stream(params: YiParam):
    final_text = ""
    data = params.model_dump(exclude_none=True)
    async for chunk in await yi_client.chat.completions.create(**data):
        if chunk.choices[0].finish_reason is None:
            if chunk.choices[0].delta.content:
                msg = json.dumps(
                    {
                        "event": "text-generation",
                        "text": chunk.choices[0].delta.content,
                    }
                )
                final_text += chunk.choices[0].delta.content
                yield msg
                await asyncio.sleep(0.01)
            else:
                continue
        elif chunk.choices[0].finish_reason is not None:
            msg = json.dumps(
                {
                    "event": "stream-end",
                    "finish_reason": chunk.choices[0].finish_reason,
                    "final_text": final_text,
                }
            )
            yield msg


async def yiAi_invoke(params: YiParam):
    data = params.model_dump(exclude_none=True)
    resp = await yi_client.chat.completions.create(**data)
    return resp.choices[0].message.content


async def nvidia_stream(params: NvidiaParam):
    final_text = ""
    data = params.model_dump(exclude_none=True)
    async for chunk in await nvidia_client.chat.completions.create(**data):
        if chunk.choices[0].finish_reason is None:
            if chunk.choices[0].delta.content:
                msg = json.dumps(
                    {
                        "event": "text-generation",
                        "text": chunk.choices[0].delta.content,
                    }
                )
                final_text += chunk.choices[0].delta.content
                yield msg
                await asyncio.sleep(0.01)
            else:
                continue
        elif chunk.choices[0].finish_reason is not None:
            msg = json.dumps(
                {
                    "event": "stream-end",
                    "finish_reason": chunk.choices[0].finish_reason,
                    "final_text": final_text,
                }
            )
            yield msg


async def nvidia_invoke(params: NvidiaParam):
    data = params.model_dump(exclude_none=True)
    resp = await nvidia_client.chat.completions.create(**data)
    return resp.choices[0].message.content


async def claude_stream(params: ClaudeParam):
    final_text = ""
    data = params.model_dump(exclude_none=True)
    modelId = data.pop("model")
    if "stop" in data:
        data["stop_sequences"] = data.pop("stop")
    body = json.dumps(data)

    for event in bedrock_client.invoke_model_with_response_stream(
        modelId=modelId, body=body
    ).get("body"):
        chunk = event.get("chunk")
        if chunk:
            texts = json.loads(chunk.get("bytes").decode())
            if texts["type"] == "content_block_delta":
                # print(texts['delta']['text'], end='',flush=True)
                msg = json.dumps(
                    {
                        "event": "text-generation",
                        "text": texts["delta"]["text"],
                    }
                )
                final_text += texts["delta"]["text"]
                yield msg
                await asyncio.sleep(0.01)
            elif texts["type"] == "message_delta":
                msg = json.dumps(
                    {
                        "event": "stream-end",
                        "finish_reason": texts["delta"]["stop_reason"],
                        "final_text": final_text,
                    }
                )
                yield msg


async def claude_invoke(params: ClaudeParam):
    data = params.model_dump(exclude_none=True)
    modelId = data.pop("model")
    if "stop" in data:
        data["stop_sequences"] = data.pop("stop")
    body = json.dumps(data)
    resp = bedrock_client.invoke_model(modelId=modelId, body=body)
    resp_item = json.loads(resp.get("body").read())
    content = ""
    for content_item in resp_item["content"]:
        content += content_item["text"]
    return content


async def xiaoai_stream(params: XiaoaiParam):
    final_text = ""
    data = params.model_dump(exclude_none=True)
    async for chunk in await xiaoai_client.chat.completions.create(**data):
        if chunk.choices[0].finish_reason is None:
            if chunk.choices[0].delta.content:
                msg = json.dumps(
                    {
                        "event": "text-generation",
                        "text": chunk.choices[0].delta.content,
                    }
                )
                final_text += chunk.choices[0].delta.content
                yield msg
                await asyncio.sleep(0.01)
            else:
                continue
        elif chunk.choices[0].finish_reason is not None:
            msg = json.dumps(
                {
                    "event": "stream-end",
                    "finish_reason": chunk.choices[0].finish_reason,
                    "final_text": final_text,
                }
            )
            yield msg


async def xiaoai_invoke(params: XiaoaiParam):
    data = params.model_dump(exclude_none=True)
    resp = await xiaoai_client.chat.completions.create(**data)
    return resp.choices[0].message.content

async def openairouter_stream(params: OAIParam):
    final_text = ""
    data = params.model_dump(exclude_none=True)
    logger.info(openairouter_client.base_url)
    logger.info(data.get("model"))
    async for chunk in await openairouter_client.chat.completions.create(**data):
        if chunk.choices[0].finish_reason is None:
            if chunk.choices[0].delta.content:
                msg = json.dumps(
                    {
                        "event": "text-generation",
                        "text": chunk.choices[0].delta.content,
                    }
                )
                final_text += chunk.choices[0].delta.content
                yield msg
                await asyncio.sleep(0.01)
            else:
                continue
        elif chunk.choices[0].finish_reason is not None:
            msg = json.dumps(
                {
                    "event": "stream-end",
                    "finish_reason": chunk.choices[0].finish_reason,
                    "final_text": final_text,
                }
            )
            yield msg


async def openairouter_invoke(params: OAIParam):
    data = params.model_dump(exclude_none=True)
    resp = await openairouter_client.chat.completions.create(**data)
    return resp.choices[0].message.content

async def sentenceCompletion_invoke(params: sentenceCompletionParam):
    data = params.model_dump(exclude_none=True)
    resp = await sentenceCompletion_client.chat.completions.create(**data)
    return resp.choices[0].message.content
logger.info("...Starting Remote Hub Server...")