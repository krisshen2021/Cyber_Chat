import httpx, pynvml, sys, asyncio, json, base64, io, re, copy, os, aiofiles, yaml
from tqdm import tqdm
from pathlib import Path

project_root = str(Path(__file__).parents[1])
if project_root not in sys.path:
    sys.path.append(project_root)
from httpx import Timeout
from io import BytesIO
from mutagen import File as MutagenFile
from fastapi import APIRouter, Depends, HTTPException, Header
from fastapi.responses import StreamingResponse, Response, JSONResponse
from pydantic import BaseModel
from typing import List, Optional
from sd_setting import update_SDAPI_config
from opanairouter_setting import select_model
from tts_setting import tts_select_endpoint
from stt_setting import stt_select_endpoint
from modules.colorlogger import logger
from modules.ANSI_tool import ansiColor
from modules.tqdm_barformat import Pbar
from pydanticClass_tabby import CompletionsParam
from remote_api_hub import (
    ChatMessage,
    cohere_stream,
    cohere_invoke,
    cohere_client,
    CohereParam,
    mistral_stream,
    mistral_invoke,
    MistralParam,
    deepseek_stream,
    deepseek_invoke,
    DeepseekParam,
    togetherAi_stream,
    togetherAi_invoke,
    togetherai_api_key,
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
    sentenceCompletionParam,
    sentenceCompletion_invoke,
)


timeout = Timeout(180.0)
### SD selector
update_SDAPI_config()
### Openairouter selector
openairouter_model, OAI_model_list = select_model()

restapi_tts = tts_select_endpoint()

restapi_stt = stt_select_endpoint()

AUDIO_DIR = os.path.join(project_root, "static","music")

logger.info(f"OAI model:{openairouter_model}")
ansiColor.color_print(
    "Remote Server Started\nWaiting for connection...",
    ansiColor.BG_BRIGHT_MAGENTA + ansiColor.WHITE,
    ansiColor.BOLD,
)
COLORBAR = Pbar.setBar(
    Pbar.BarColorer.GREEN, Pbar.BarColorer.YELLOW, Pbar.BarColorer.GREEN
)


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
    speaker: Optional[str] = None


class STTPayload(BaseModel):
    audio_data: str  # {"file": ("audio.webm", io.BytesIO(audio_data), "audio/webm")}

# class StreamMuiscPayload(BaseModel):
#     moment: Optional[str] = None
#     music_name: Optional[str] = None


sd_api_url = "http://127.0.0.1:7860"
api_txt2img_path = "/sdapi/v1/txt2img"
api_progress_path = "/internal/progress"

prompt_param_path = os.path.join(project_root, "config", "prompts", "prompts.yaml")
config_data_path = os.path.join(project_root, "config", "config.yml")


async def load_prompts_params():
    async with aiofiles.open(prompt_param_path, mode="r") as f:
        contents = await f.read()
    prompt_params = yaml.safe_load(contents)
    return prompt_params["sentenceCompletion_prompt"]


async def load_config_data():
    async with aiofiles.open(config_data_path, mode="r") as f:
        contents = await f.read()
    config_data = yaml.safe_load(contents)
    return config_data


sentence_completion_prompt = asyncio.run(load_prompts_params())
config_data = asyncio.run(load_config_data())
local_tabby_server_base = config_data["local_tabby_server_base"]
api_key = config_data["api_key"]
admin_key = config_data["admin_key"]
tabbyHeaders = {
            "accept": "application/json",
            "x-api-key": api_key,
            "x-admin-key": admin_key,
            "Content-Type": "application/json",
        }

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
            logger.info(
                f"Generate Image from {sd_api_url}, task_id: {progress_payload.get('id_task','Empty')}"
            )
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


# XTTS tts to audio (local xtts server)
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
async def check_progress(payload: SDProcessPayload, SD_URL: str = Header(None)):
    payload_dict = payload.model_dump()
    api_instance = StableDiffusionAPI()

    async def progress_generator():
        async for progress_info in api_instance.check_progress(
            progress_payload=payload_dict, sd_api_url=SD_URL
        ):
            yield json.dumps(progress_info) + "\n"

    return StreamingResponse(progress_generator(), media_type="application/x-ndjson")


# SD model list
@router.post("/v1/SDapiModelList")
async def SD_api_modellist(SD_URL: str = Header(None)):
    logger.info(f"Getting Model list from {SD_URL}")
    model_list_endpoint = "/sdapi/v1/sd-models"
    headers = {"accept": "application/json"}
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url=SD_URL+model_list_endpoint, headers=headers, timeout=timeout)
            response.raise_for_status()
            response_data = response.json()
            return response_data
    except Exception as e:
        print("Error on fetch Model List from SDapi: ", e)

# SD vram status
@router.post("/v1/SDapiVRAMStatus")
async def SD_api_vram(SD_URL: str = Header(None)):
    logger.info(f"Getting VRAM status from {SD_URL}")
    memory_endpoint = "/sdapi/v1/memory"
    cmd_flags_endpoint = "/sdapi/v1/cmd-flags"
    headers = {"accept": "application/json"}
    try:
        # Fetch memory information
        async with httpx.AsyncClient() as client:
            response = await client.get(url=SD_URL+memory_endpoint, headers=headers, timeout=timeout)
            response.raise_for_status()
            memory_data = response.json()
            memory = memory_data["cuda"]["system"]["total"]
        # Fetch cmd_flags to check if lowvram is enabled
            response = await client.get(url=SD_URL+cmd_flags_endpoint, headers=headers, timeout=timeout)
            response.raise_for_status()
            cmd_flags = response.json()
            lowvram = cmd_flags["lowvram"]
            medvram = cmd_flags["medvram"]
        # identiify vram status
            if lowvram or medvram or memory < 10000000000:
                vram_status = "low"
            else:
                vram_status = "high"
            return {"vram_status": vram_status}
                
    except Exception as e:
        print("Error on fetch VRAM status from SDapi: ", e)

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



# local tabby server ONLY endpoints
@router.post("/v1/model/unload")
async def unload_model():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            url=f"{local_tabby_server_base}/model/unload",
            headers=tabbyHeaders,
            timeout=timeout,
        )
        if response.status_code == 200:
            return True
        else:
            return False
    
@router.post("/v1/model/load")
async def load_model(payload:dict):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            url=f"{local_tabby_server_base}/model/load",
            headers=tabbyHeaders,
            json=payload,
            timeout=timeout,
        )
        if response.status_code == 200:
            return True
        else:
            return False
@router.post("/v1/completions")
async def local_completion(params: CompletionsParam):
    data = params.model_dump(exclude_none=True)
    stream = data["stream"]
    headers = {
        "accept": "application/json",
        "x-api-key": api_key,
        "x-admin-key": admin_key,
        "Content-Type": "application/json",
    }
    if stream:

        async def stream_generator():
            try:
                async with httpx.AsyncClient() as client:
                    async with client.stream(
                        "POST",
                        url=f"{local_tabby_server_base}/completions",
                        json=data,
                        headers=headers,
                        timeout=timeout,
                    ) as response:
                        async for chunk in response.aiter_text():
                            yield chunk
            except Exception as e:
                print("Error on fetch from Tabby: ", e)

        return StreamingResponse(stream_generator(), media_type="application/json")
    
    else:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url=f"{local_tabby_server_base}/completions",
                    json=data,
                    headers=headers,
                    timeout=timeout,
                )
                response.raise_for_status()
                response_data = response.json()
                return response_data
        except Exception as e:
            print("Error on fetch from Tabby: ", e)



# Endpoints for remote actions
# OAI tts to audio
@router.post("/v1/tts_remote_stream")
async def remotetts_to_audio_stream(payload: RestAPI_TTSPayload):
    server_url = restapi_tts.get("server_url")
    headers = restapi_tts.get("headers")
    payload_tts = copy.deepcopy(restapi_tts.get("payload_tts"))
    endpoint_name = restapi_tts.get("name")
    speaker = payload.speaker
    pattern = r"(_female_)"
    match = re.search(pattern, speaker)
    if match:
        gender = "female"
    else:
        gender = "male"
    if endpoint_name == "Unrealspeech":
        payload_tts["Text"] = payload.text
        payload_tts["VoiceId"] = payload_tts["VoiceId"][gender]
    elif endpoint_name == "Openai":
        payload_tts["input"] = payload.text
        payload_tts["voice"] = payload_tts["voice"][gender]
    elif endpoint_name == "PlayHT":
        payload_tts["text"] = payload.text
        payload_tts["voice"] = payload_tts["voice"][gender]
    try:

        async def stream_audio():
            async with httpx.AsyncClient(timeout=300) as client:
                async with client.stream(
                    "POST", server_url, json=payload_tts, headers=headers
                ) as response:
                    logger.info("Start to streaming audio")
                    async for chunk in response.aiter_bytes():
                        if chunk:
                            yield chunk
                            await asyncio.sleep(0.01)
            logger.info("Streaming ends")

        return StreamingResponse(stream_audio(), media_type="audio/mpeg")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
# OAI model list endpoint
@router.get("/v1/models")
async def get_models():
    if config_data["using_remoteapi"] and config_data["remoteapi_endpoint"] == "openairouter":
        return JSONResponse(content=OAI_model_list)
    elif config_data["using_remoteapi"] and config_data["remoteapi_endpoint"] == "cohere":
        response = await cohere_client.models.list()
        model_list = []
        for model in response.models:
            if "command" in model.name or "aya" in model.name:
                model_list.append({"id": model.name, "object": "model", "owned_by": "cohere"})
        sorted_model_list = sorted(model_list, key=lambda x: x["id"])
        content ={
            "object": "list",
            "data": sorted_model_list
        }
        return JSONResponse(content=content)
    elif config_data["using_remoteapi"] and config_data["remoteapi_endpoint"] == "togetherai":
        togetherai_url = "https://api.together.xyz/v1/models"
        async with httpx.AsyncClient(timeout=300) as client:
            response = await client.get(url=togetherai_url, headers={"Authorization": f"Bearer {togetherai_api_key}", "accept":"application/json"})
            content = response.json()
            model_list = [{"id": model["id"], "object": "model", "owned_by": "togetherai"} for model in content if "chat" in model["type"]]
            sorted_model_list = sorted(model_list, key=lambda x: x["id"].lower())
            content = {
                "object": "list",
                "data": sorted_model_list
            }
            return JSONResponse(content=content)
        
    elif not config_data["using_remoteapi"]:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url=f"{local_tabby_server_base}/models",
                headers=tabbyHeaders,
                timeout=timeout,
            )
            response.raise_for_status()
            response_data = response.json()
            return response_data
    else:
        raise HTTPException(status_code=404, detail="Model list not found")
    
# OAI model get default model
@router.get("/v1/model")
async def get_default_model():
    global openairouter_model
    if config_data["using_remoteapi"] and config_data["remoteapi_endpoint"] == "openairouter":
        return JSONResponse(content={"id": openairouter_model})
    elif config_data["using_remoteapi"] and config_data["remoteapi_endpoint"] == "cohere":
        return JSONResponse(content={"id": "command-r-plus"})
    elif config_data["using_remoteapi"] and config_data["remoteapi_endpoint"] == "togetherai":
        return JSONResponse(content={"id": "NousResearch/Nous-Hermes-2-Mixtral-8x7B-DPO"})
    elif not config_data["using_remoteapi"]:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url=f"{local_tabby_server_base}/model",
                headers=tabbyHeaders,
                timeout=timeout,
            )
            response.raise_for_status()
            response_data = response.json()
            return response_data
    else:
        raise HTTPException(status_code=404, detail="Current model not found")
# OAI default model switch  
@router.post("/v1/OAI_Switch_Model")
async def switch_model(model: dict):
    global openairouter_model
    openairouter_model = model["model"]
    logger.info(f"Switching to model: {openairouter_model}")
    return JSONResponse(content={"model":openairouter_model,"message": f"Switched to model: {openairouter_model}"})
# OAI STT speak to text
@router.post("/v1/stt_remote")
async def stt_to_text(payload: STTPayload):
    server_url = restapi_stt.get("server_url")
    headers = restapi_stt.get("headers")
    data = restapi_stt.get("data")
    # print(payload.audio_data)
    # print(server_url,headers,data)
    audio_data = base64.b64decode(str(payload.audio_data))
    files = {"file": ("audio.webm", io.BytesIO(audio_data), "audio/webm")}
    try:
        async with httpx.AsyncClient() as client:
            transcript = await client.post(
                url=server_url, headers=headers, files=files, data=data, timeout=60
            )
            if transcript.status_code == 200:
                return transcript.json()
            else:
                return {"text": "Error on transcribe audio"}
    except Exception as e:
        print(f"Error on transcribe audio: {e}")
# OAI remote api endpoint
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
        global openairouter_model
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



#Music streaming endpoints
@router.get("/v1/music/playlist")
async def get_playlist():
    files = [f for f in os.listdir(AUDIO_DIR) if f.endswith(('.mp3', '.wav', '.ogg'))]
    files.sort(key=str.lower)
    full_playlist = []
    for music in files:
        music_path = os.path.join(AUDIO_DIR, music)
        if os.path.isfile(music_path):
            audio = MutagenFile(music_path)
            # print(audio.tags)
            music = {
                "name": music,
                "duration": audio.info.length,
                "size": os.path.getsize(music_path),
                "title": audio.get("TIT2").text[0] if audio.get("TIT2") else "Unknown",
                "artist": audio.get("TPE1").text[0] if audio.get("TPE1") else "Unknown",
                "album": audio.get("TALB").text[0] if audio.get("TALB") else "Unknown",
            }
            full_playlist.append(music)
    return JSONResponse(content={"playlist": full_playlist})

@router.get("/v1/music/play/{filename}")
async def play_music(filename: str):
    respnose = await get_playlist()
    music_list = respnose.body
    music_list = json.loads(music_list.decode())
    for music in music_list.get("playlist"):
        if music.get("title") == filename or music.get("name") == filename:
            music_path = os.path.join(AUDIO_DIR, music.get("name"))
            if os.path.isfile(music_path):
                async def interfile(start=0, chunk_size=8192):
                    async with aiofiles.open(music_path, "rb") as f:
                        await f.seek(start)
                        while chunk := await f.read(chunk_size):
                            yield chunk
                return StreamingResponse(interfile(), media_type="audio/mpeg")
            else:
                raise HTTPException(status_code=404, detail="Music not found")
    raise HTTPException(status_code=404, detail="Music not found")