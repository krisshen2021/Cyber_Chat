from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
import httpx,json, os
import asyncio
from tqdm import tqdm
import logging

# 设置日志
logging.basicConfig(
    level=logging.ERROR, format="%(asctime)s - %(levelname)s - %(message)s"
)
sd_api_url = "http://127.0.0.1:7860"
api_txt2img_path = "/sdapi/v1/txt2img"
api_progress_path = "/internal/progress"
def clear_screen():
    # 针对不同操作系统的清屏命令
    if os.name == "nt":  # Windows
        _ = os.system("cls")
    else:  # Mac and Linux
        _ = os.system("clear")
clear_screen()
class StableDiffusionAPI:
    def __init__(self):
        pass
    
    async def send_txt2img_request(self, sd_api_url=sd_api_url, api_txt2img_path=api_txt2img_path, txt2img_payload=None):
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{sd_api_url}{api_txt2img_path}", json=txt2img_payload, timeout=300.0
                )
                # logging.error("txt2img request sent successfully")
                return response.json()
            except Exception as e:
                logging.error(f"An unexpected error occurred: {e}")

    async def check_progress(self, sd_api_url=sd_api_url, api_progress_path=api_progress_path, progress_payload=None):
        async with httpx.AsyncClient() as client:
            self.pbar = tqdm(total=100, desc="Image processing")
            while True:
                try:
                    response = await client.post(
                        f"{sd_api_url}{api_progress_path}", json=progress_payload, timeout=300.0
                    )
                    progress_info = response.json()
                    if progress_info["progress"] is not None and progress_info["progress"] < 0.99 and progress_info['completed'] is False:
                        self.pbar.n = int(progress_info["progress"] * 100)
                        yield progress_info
                    elif progress_info["completed"]:
                        self.pbar.n = 100
                        progress_info["progress"] = 1
                        yield progress_info
                        self.pbar.close()
                        break
                    self.pbar.update(0)
                    await asyncio.sleep(1)
                except Exception as e:
                    logging.error(f"Error checking progress: {e}")
                    

app = FastAPI()

class TaskRequest(BaseModel):
    txt2img_payload: Optional[dict] = {
    "force_task_id": "tester00001",
    "negative_prompt": "",
    "hr_scale": 2,
    "seed": -1,
    "enable_hr": True,
    "width": 512,
    "height": 768,
    "hr_upscaler": "Latent",
    "sampler_name": "Euler a",
    "cfg_scale": 7,
    "denoising_strength": 0.55,
    "steps": 40,
    "prompt": "a girl, reading a box, sitting in toilet, sunny day",
    "override_settings": {
        "sd_vae": "Automatic",
        "sd_model_checkpoint": "astranime_V6",
    },
    "override_settings_restore_afterwards": True,
}
    progress_payload: Optional[dict] = {
    "id_task": "tester00001",
    "id_live_preview": -1,
    "live_preview": False,
}

@app.post("/generate-image")
async def generate_image(request: TaskRequest):
    api_instance = StableDiffusionAPI()
    txt2img_result = await api_instance.send_txt2img_request(txt2img_payload=request.txt2img_payload)
    return txt2img_result

@app.post("/check-progress")
async def check_progress(request: TaskRequest):
    api_instance = StableDiffusionAPI()
    async def progress_generator():
        async for progress_info in api_instance.check_progress(progress_payload=request.progress_payload):
            yield json.dumps(progress_info) + "\n"
    return StreamingResponse(progress_generator(), media_type="application/x-ndjson")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8111)