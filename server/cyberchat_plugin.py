import httpx, pynvml, sys, asyncio, json, base64, io
from tqdm import tqdm
from pathlib import Path

project_root = str(Path(__file__).parents[1])
if project_root not in sys.path:
    sys.path.append(project_root)
from httpx import Timeout
from io import BytesIO
from fastapi import APIRouter, Depends, HTTPException, Header
from fastapi.responses import StreamingResponse, Response
from pydantic import BaseModel
from typing import List, Optional
from sd_setting import update_SDAPI_config
from opanairouter_setting import select_model
from tts_setting import tts_select_endpoint
from stt_setting import stt_select_endpoint
from modules.colorlogger import logger
from modules.ANSI_tool import ansiColor
from modules.tqdm_barformat import Pbar
from remote_api_hub import (
    ChatMessage,
    cohere_stream,
    cohere_invoke,
    CohereParam,
    mistral_stream,
    mistral_invoke,
    MistralParam,
    deepseek_stream,
    deepseek_invoke,
    DeepseekParam,
    togetherAi_stream,
    togetherAi_invoke,
    TogetherAiParam,
    yiAi_stream,
    yiAi_invoke,
    YiParam,
    nvidia_stream,
    nvidia_invoke,
    NvidiaParam,
    claude_stream,
    claude_invoke,
    ClaudeParam,
    xiaoai_stream,
    xiaoai_invoke,
    XiaoaiParam,
    openairouter_stream,
    openairouter_invoke,
    OAIParam,
)


timeout = Timeout(180.0)
### SD selector
update_SDAPI_config()
### Openairouter selector
openairouter_model = select_model()

restapi_tts = tts_select_endpoint()

restapi_stt = stt_select_endpoint()

ansiColor.color_print("Remote Server Started\nWaiting for connection...", ansiColor.BG_BRIGHT_MAGENTA+ansiColor.WHITE, ansiColor.BOLD)
COLORBAR = Pbar.setBar(Pbar.BarColorer.GREEN,Pbar.BarColorer.YELLOW,Pbar.BarColorer.GREEN)

class OverrideSettings(BaseModel):
    sd_vae: Optional[str] = "Automatic"
    sd_model_checkpoint: str
    face_restoration_model: Optional[str] = "CodeFormer"
    CLIP_stop_at_last_layers: Optional[int] = 2


class SDPayload(BaseModel):
    force_task_id: Optional[str] = "SD_task_id"
    hr_negative_prompt: Optional[str] = None
    hr_prompt: Optional[str] = None
    hr_scale: Optional[float] = None
    hr_second_pass_steps: Optional[int] = None
    seed: Optional[int] = None
    enable_hr: Optional[bool] = False
    width: int
    height: int
    hr_upscaler: Optional[str] = None
    negative_prompt: Optional[str] = None
    prompt: str
    sampler_name: Optional[str] = None
    cfg_scale: Optional[float] = None
    denoising_strength: Optional[float] = None
    steps: Optional[int] = None
    restore_faces: Optional[bool] = False
    override_settings: OverrideSettings
    override_settings_restore_afterwards: Optional[bool] = True


class SDProcessPayload(BaseModel):
    id_task: str = "SD_task_id"
    id_live_preview: Optional[float] = -1
    live_preview: Optional[bool] = True


class TaskRequest(BaseModel):
    txt2img_payload: Optional[SDPayload] = None
    progress_payload: Optional[SDProcessPayload] = None


class XTTSPayload(BaseModel):
    text: Optional[str] = None
    speaker_wav: Optional[str] = "en_female_01"
    language: Optional[str] = "en"
    server_url: Optional[str] = "http://127.0.0.1:8020/tts_to_audio/"
    
class RestAPI_TTSPayload(BaseModel):
    text: Optional[str] = None
    
class STTPayload(BaseModel):
    audio_data:str #{"file": ("audio.webm", io.BytesIO(audio_data), "audio/webm")}
    

sd_api_url = "http://127.0.0.1:7860"
api_txt2img_path = "/sdapi/v1/txt2img"
api_progress_path = "/internal/progress"


class StableDiffusionAPI:
    def __init__(self):
        pass

    async def send_txt2img_request(
        self,
        sd_api_url=sd_api_url,
        api_txt2img_path=api_txt2img_path,
        txt2img_payload=None,
    ):

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{sd_api_url}{api_txt2img_path}",
                    json=txt2img_payload,
                    timeout=300.0,
                )
                # logger.error("txt2img request sent successfully")
                return response.json()
            except Exception as e:
                logger.error(f"An unexpected error occurred: {e}")

    async def check_progress(
        self,
        sd_api_url=sd_api_url,
        api_progress_path=api_progress_path,
        progress_payload=None,
    ):
        async with httpx.AsyncClient() as client:
            logger.info(f"Generate Image from {sd_api_url}, task_id: {progress_payload.get('id_task','Empty')}")
            self.pbar = tqdm(range(100), desc="Generating Image", bar_format=COLORBAR)
            while True:
                try:
                    response = await client.post(
                        f"{sd_api_url}{api_progress_path}",
                        json=progress_payload,
                        timeout=300.0,
                    )
                    progress_info = response.json()
                    if (
                        progress_info["progress"] is not None
                        and progress_info["progress"] < 0.99
                        and progress_info["completed"] is False
                    ):
                        self.pbar.n = int(progress_info["progress"] * 100)
                        yield progress_info
                    elif progress_info["completed"]:
                        self.pbar.n = 100
                        progress_info["progress"] = 1
                        yield progress_info
                        self.pbar.close()
                        break
                    self.pbar.refresh()
                    await asyncio.sleep(1)
                except Exception as e:
                    logger.error(f"Error checking progress: {e}")


router = APIRouter(tags=["cyberchat"])

# Openai like tts to audio
@router.post("/v1/tts_remote")
async def remotetts_to_audio(payload:RestAPI_TTSPayload):
    server_url = restapi_tts.get("server_url")
    headers = restapi_tts.get("headers")
    payload_tts = restapi_tts.get("payload_tts")
    endpoint_name = restapi_tts.get("name")
    if endpoint_name == 'Unrealspeech':
        payload_tts["Text"] = payload.text
    elif endpoint_name == 'Openai':
        payload_tts["input"] = payload.text
    elif endpoint_name == 'PlayHT':
        payload_tts["text"] = payload.text
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                server_url, json=payload_tts, headers=headers, timeout=timeout
            )
            if response.status_code == 200:
                audio_data = BytesIO(response.content)
                audio_data.seek(0)
                return StreamingResponse(
                    audio_data,
                    media_type="audio/wav",
                    headers={"Content-Disposition": "attachment; filename=output.wav"},
                )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/v1/tts_remote_stream")
async def remotetts_to_audio_stream(payload:RestAPI_TTSPayload):
    server_url = restapi_tts.get("server_url")
    headers = restapi_tts.get("headers")
    payload_tts = restapi_tts.get("payload_tts")
    endpoint_name = restapi_tts.get("name")
    if endpoint_name == 'Unrealspeech':
        payload_tts["Text"] = payload.text
    elif endpoint_name == 'Openai':
        payload_tts["input"] = payload.text
    elif endpoint_name == 'PlayHT':
        payload_tts["text"] = payload.text
    try:
        async def stream_audio():
            async with httpx.AsyncClient(timeout=300) as client:
                async with client.stream("POST", server_url, json=payload_tts, headers=headers) as response:
                    logger.info('Start to streaming audio')
                    async for chunk in response.aiter_bytes():
                        if chunk:
                            yield chunk
            logger.info('Streaming ends')
        return StreamingResponse(stream_audio(), media_type="audio/mpeg")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
# XTTS tts to audio
@router.post("/v1/xtts")
async def xtts_to_audio(payload: XTTSPayload):
    server_url = payload.server_url
    payload_xtts = {
        "text": payload.text,
        "speaker_wav": payload.speaker_wav,
        "language": payload.language,
    }
    headers = {"accept": "audio/wav", "Content-Type": "application/json"}
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                server_url, json=payload_xtts, headers=headers, timeout=timeout
            )
            if response.status_code == 200:
                audio_data = BytesIO(response.content)
                audio_data.seek(0)
                return StreamingResponse(
                    audio_data,
                    media_type="audio/wav",
                    headers={"Content-Disposition": "attachment; filename=output.wav"},
                )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
# STT speak to text
@router.post("/v1/stt_remote")
async def stt_to_text(payload: STTPayload):
    server_url = restapi_stt.get("server_url")
    headers = restapi_stt.get("headers")
    data = restapi_stt.get("data")
    # print(payload.audio_data)
    # print(server_url,headers,data)
    audio_data = base64.b64decode(str(payload.audio_data))
    files = {
    "file": ("audio.webm", io.BytesIO(audio_data), "audio/webm")
    }    
    try:
        async with httpx.AsyncClient() as client:
            transcript = await client.post(url=server_url, headers=headers, files=files, data=data, timeout=60)
            if transcript.status_code == 200:
                return transcript.json()
            else:
                return {"text":"Error on transcribe audio"}
    except Exception as e:
        print(f"Error on transcribe audio: {e}")


# SD Picture Generator
@router.post("/v1/SDapi")
async def generate_image(payload: SDPayload, SD_URL: str = Header(None)):
    SD_URL = SD_URL.replace("/sdapi/v1/txt2img", "")
    payload_dict = payload.model_dump()
    api_instance = StableDiffusionAPI()
    txt2img_result = await api_instance.send_txt2img_request(
        txt2img_payload=payload_dict, sd_api_url=SD_URL
    )
    return txt2img_result

@router.post("/v1/check-progress")
async def check_progress(payload: SDProcessPayload, SD_URL:str = Header(None)):
    payload_dict = payload.model_dump()
    api_instance = StableDiffusionAPI()
    async def progress_generator():
        async for progress_info in api_instance.check_progress(progress_payload=payload_dict, sd_api_url=SD_URL):
            yield json.dumps(progress_info) + "\n"
    return StreamingResponse(progress_generator(), media_type="application/x-ndjson")


# SD model list
@router.post("/v1/SDapiModelList")
async def SD_api_modellist(SD_URL: str = Header(None)):
    logger.info(f"Getting Model list from {SD_URL.replace('/sdapi/v1/sd-models','')}")
    headers = {"accept": "application/json"}
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url=SD_URL, headers=headers, timeout=timeout)
            response.raise_for_status()
            response_data = response.json()
            return response_data
    except Exception as e:
        print("Error on fetch Model List from SDapi: ", e)


# GPU list endpoint
@router.get("/v1/gpu")
async def get_gpu_info():
    pynvml.nvmlInit()
    device_count = pynvml.nvmlDeviceGetCount()
    gpu_info = []

    for i in range(device_count):
        handle = pynvml.nvmlDeviceGetHandleByIndex(i)
        gpu_name = pynvml.nvmlDeviceGetName(handle)
        memory_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
        total_memory_gb = int(memory_info.total / (1024**3))  # Convert to GB
        gpu_info.append({"GPU": i, "Name": gpu_name, "GPU_Memory": total_memory_gb})

    pynvml.nvmlShutdown()
    return {"GPU Count": device_count, "GPU Info": gpu_info}


# remote api endpoint
@router.post("/v1/remoteapi/{ai_type}")
async def remote_ai_stream(ai_type: str, params_json: dict):
    if ai_type == "cohere":
        keys_to_keep = [
            "system_prompt",
            "messages",
            "temperature",
            "max_tokens",
            "presence_penalty",
            "model",
            "stop",
            "raw_prompting",
            "top_p",
            "stream",
        ]
        cohere_dict = {
            key: params_json[key] for key in keys_to_keep if key in params_json
        }
        cohere_dict["message"] = cohere_dict.pop("messages")
        if "top_p" in cohere_dict and cohere_dict["top_p"] is not None:
            cohere_dict["p"] = cohere_dict.pop("top_p")
        if "stop" in cohere_dict and cohere_dict["stop"] is not None:
            cohere_dict["stop_sequences"] = cohere_dict.pop("stop")
            # print(cohere_dict["stop_sequences"])
            cohere_dict["stop_sequences"] = cohere_dict["stop_sequences"][-5:]
        if "system_prompt" in cohere_dict and cohere_dict["system_prompt"] is not None:
            cohere_dict["preamble"] = cohere_dict.pop("system_prompt")
        if (
            "presence_penalty" in cohere_dict
            and cohere_dict["presence_penalty"] is not None
        ):
            if cohere_dict["presence_penalty"] > 1:
                integer_part = int(cohere_dict["presence_penalty"])
                decimal_part = cohere_dict["presence_penalty"] - integer_part
                cohere_dict["presence_penalty"] = round(decimal_part, 2)

        if cohere_dict["stream"] is True:
            cohere_dict.pop("stream")
            params = CohereParam(**cohere_dict)
            return StreamingResponse(cohere_stream(params), media_type="text/plain")
        else:
            cohere_dict.pop("stream")
            params = CohereParam(**cohere_dict)
            return Response(
                content=await cohere_invoke(params), media_type="text/plain"
            )

    elif ai_type == "mistral":
        keys_to_keep = [
            "system_prompt",
            "messages",
            "temperature",
            "max_tokens",
            "stop",
            "top_p",
            "model",
            "stream",
        ]
        mistral_dict = {
            key: params_json[key] for key in keys_to_keep if key in params_json
        }
        mistral_dict["messages"] = [
            ChatMessage(role="user", content=mistral_dict["messages"]),
        ]
        if (
            "system_prompt" in mistral_dict
            and mistral_dict["system_prompt"] is not None
        ):
            mistral_dict["messages"].insert(
                0, ChatMessage(role="system", content=mistral_dict["system_prompt"])
            )
        params = MistralParam(**mistral_dict)
        if params.stream is True:
            return StreamingResponse(mistral_stream(params), media_type="text/plain")
        else:
            return Response(
                content=await mistral_invoke(params), media_type="text/plain"
            )

    elif ai_type == "deepseek":
        keys_to_keep = [
            "system_prompt",
            "messages",
            "temperature",
            "max_tokens",
            "top_p",
            "stop",
            "model",
            "presence_penalty",
            "stream",
        ]
        deepseek_dict = {
            key: params_json[key] for key in keys_to_keep if key in params_json
        }
        deepseek_dict["messages"] = [
            ChatMessage(role="user", content=deepseek_dict["messages"]),
        ]
        if (
            "system_prompt" in deepseek_dict
            and deepseek_dict["system_prompt"] is not None
        ):
            deepseek_dict["messages"].insert(
                0, ChatMessage(role="system", content=deepseek_dict["system_prompt"])
            )
        params = DeepseekParam(**deepseek_dict)
        if params.stream is True:
            return StreamingResponse(deepseek_stream(params), media_type="text/plain")
        else:
            return Response(
                content=await deepseek_invoke(params), media_type="text/plain"
            )

    elif ai_type == "togetherai":
        keys_to_keep = [
            "system_prompt",
            "messages",
            "temperature",
            "max_tokens",
            "top_p",
            "stop",
            "model",
            "presence_penalty",
            "stream",
        ]
        togetherai_dict = {
            key: params_json[key] for key in keys_to_keep if key in params_json
        }
        togetherai_dict["messages"] = [
            ChatMessage(role="user", content=togetherai_dict["messages"]),
        ]
        if (
            "system_prompt" in togetherai_dict
            and togetherai_dict["system_prompt"] is not None
        ):
            togetherai_dict["messages"].insert(
                0, ChatMessage(role="system", content=togetherai_dict["system_prompt"])
            )
        params = TogetherAiParam(**togetherai_dict)
        if params.stream is True:
            return StreamingResponse(togetherAi_stream(params), media_type="text/plain")
        else:
            return Response(
                content=await togetherAi_invoke(params), media_type="text/plain"
            )

    elif ai_type == "yi":
        keys_to_keep = [
            "system_prompt",
            "messages",
            "temperature",
            "max_tokens",
            "top_p",
            "stop",
            "model",
            "presence_penalty",
            "stream",
        ]
        Yi_dict = {key: params_json[key] for key in keys_to_keep if key in params_json}
        Yi_dict["messages"] = [
            ChatMessage(role="user", content=Yi_dict["messages"]),
        ]
        if "system_prompt" in Yi_dict and Yi_dict["system_prompt"] is not None:
            Yi_dict["messages"].insert(
                0, ChatMessage(role="system", content=Yi_dict["system_prompt"])
            )
        params = YiParam(**Yi_dict)
        if params.stream is True:
            return StreamingResponse(yiAi_stream(params), media_type="text/plain")
        else:
            return Response(content=await yiAi_invoke(params), media_type="text/plain")

    elif ai_type == "nvidia":
        keys_to_keep = [
            "system_prompt",
            "messages",
            "temperature",
            "max_tokens",
            "top_p",
            "stop",
            "model",
            "stream",
        ]
        nvidia_dict = {
            key: params_json[key] for key in keys_to_keep if key in params_json
        }
        nvidia_dict["messages"] = [
            ChatMessage(role="user", content=nvidia_dict["messages"]),
        ]
        if "system_prompt" in nvidia_dict and nvidia_dict["system_prompt"] is not None:
            nvidia_dict["messages"].insert(
                0, ChatMessage(role="system", content=nvidia_dict["system_prompt"])
            )
        params = NvidiaParam(**nvidia_dict)
        if params.stream is True:
            return StreamingResponse(nvidia_stream(params), media_type="text/plain")
        else:
            return Response(
                content=await nvidia_invoke(params), media_type="text/plain"
            )

    elif ai_type == "claude":
        keys_to_keep = [
            "system_prompt",
            "messages",
            "temperature",
            "max_tokens",
            "top_p",
            "stop",
            "model",
            "stream",
        ]
        claude_dict = {
            key: params_json[key] for key in keys_to_keep if key in params_json
        }
        if "system_prompt" in claude_dict and claude_dict["system_prompt"] is not None:
            claude_dict["system"] = claude_dict.pop("system_prompt")
        claude_dict["messages"] = [
            ChatMessage(role="user", content=claude_dict["messages"]),
        ]
        if claude_dict["stream"] is True:
            claude_dict.pop("stream")
            params = ClaudeParam(**claude_dict)
            return StreamingResponse(claude_stream(params), media_type="text/plain")
        else:
            claude_dict.pop("stream")
            params = ClaudeParam(**claude_dict)
            return Response(
                content=await claude_invoke(params), media_type="text/plain"
            )
    elif ai_type == "xiaoai":
        keys_to_keep = [
            "system_prompt",
            "messages",
            "temperature",
            "max_tokens",
            "top_p",
            "stop",
            "model",
            "presence_penalty",
            "stream",
        ]
        xiaoai_dict = {
            key: params_json[key] for key in keys_to_keep if key in params_json
        }
        if "stop" in xiaoai_dict and xiaoai_dict["stop"] is not None:
            if isinstance(xiaoai_dict["stop"], list):
                if len(xiaoai_dict["stop"]) > 4:
                    xiaoai_dict["stop"] = xiaoai_dict["stop"][-4:]
        xiaoai_dict["messages"] = [
            ChatMessage(role="user", content=xiaoai_dict["messages"]),
        ]
        if "system_prompt" in xiaoai_dict and xiaoai_dict["system_prompt"] is not None:
            xiaoai_dict["messages"].insert(
                0, ChatMessage(role="system", content=xiaoai_dict["system_prompt"])
            )
        params = XiaoaiParam(**xiaoai_dict)
        if params.stream is True:
            return StreamingResponse(xiaoai_stream(params), media_type="text/plain")
        else:
            return Response(
                content=await xiaoai_invoke(params), media_type="text/plain"
            )
    elif ai_type == "openairouter":
        keys_to_keep = [
            "system_prompt",
            "messages",
            "temperature",
            "max_tokens",
            "top_p",
            "stop",
            "model",
            "presence_penalty",
            "stream",
        ]
        openairouter_dict = {
            key: params_json[key] for key in keys_to_keep if key in params_json
        }
        if "model" not in openairouter_dict or openairouter_dict["model"] is None:
            openairouter_dict["model"] = openairouter_model or "cohere/command-r"
        if "stop" in openairouter_dict and openairouter_dict["stop"] is not None:
            if isinstance(openairouter_dict["stop"], list):
                if len(openairouter_dict["stop"]) > 4:
                    openairouter_dict["stop"] = openairouter_dict["stop"][-4:]
                    # logger.info(f"openairouter stop: {openairouter_dict['stop']}")
        openairouter_dict["messages"] = [
            ChatMessage(role="user", content=openairouter_dict["messages"]),
        ]
        if (
            "system_prompt" in openairouter_dict
            and openairouter_dict["system_prompt"] is not None
        ):
            openairouter_dict["messages"].insert(
                0,
                ChatMessage(role="system", content=openairouter_dict["system_prompt"]),
            )
        params = OAIParam(**openairouter_dict)
        if params.stream is True:
            return StreamingResponse(
                openairouter_stream(params), media_type="text/plain"
            )
        else:
            return Response(
                content=await openairouter_invoke(params), media_type="text/plain"
            )
    else:
        return "Invalid AI type"
