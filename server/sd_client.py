import httpx, json, base64, io, os
from PIL import Image, ImageTk
import asyncio
import uuid
import tkinter as tk
from tkinter import scrolledtext
from tqdm import tqdm


def clear_screen():
    # 针对不同操作系统的清屏命令
    if os.name == "nt":  # Windows
        _ = os.system("cls")
    else:  # Mac and Linux
        _ = os.system("clear")


clear_screen()

img_width = 512
img_height = 768
scale = 2
txt2img_payload = {
    "negative_prompt": "score_4, score_5, score_6, pony, Muscular, bad hand, NSFW",
    "hr_scale": scale,
    "seed": -1,
    "enable_hr": True,
    "width": img_width,
    "height": img_height,
    "hr_upscaler": "Latent (nearest-exact)",
    "sampler_name": "Euler a",
    "scheduler": "karras",
    "cfg_scale": 4,
    "denoising_strength": 0.7,
    "steps": 50,
    "restore_faces": False,
    "prompt": """score_9_up, socore_8_up, score_7_up, night street, lady, middle aged, chocolate skin, curly ponytail, super big eyes, thick black lips, Extra Long Eyelashes, look at viewer, slutry expression, police black suits, police badge, tatoo marks, slender body,
squre belt buckle, handgun:1.2, handgun holster, Walkie-Talkie""",
    "override_settings": {
        "face_restoration_model": "CodeFormer",
        "code_former_weight": 0.99,
        "face_restoration_unload": False,
        "sd_vae": "Automatic",
        "sd_model_checkpoint": "atomixPony3DXL_v10",
        "CLIP_stop_at_last_layers": 2
    },
    "override_settings_restore_afterwards": True,
}
process_payload = {"id_live_preview": -1, "live_preview": True}


async def generate_image(task_id: str):
    async with httpx.AsyncClient(timeout=300.0) as client:
        response = await client.post(
            "http://127.0.0.1:8111/generate-image",
            json={
                "txt2img_payload": {"force_task_id": task_id, **txt2img_payload},
            },
        )
        return response.json()


async def check_progress(task_id: str):
    async with httpx.AsyncClient(timeout=300.0) as client:
        try:
            async with client.stream(
                "POST",
                "http://127.0.0.1:8111/check-progress",
                json={"progress_payload": {"id_task": task_id, **process_payload}},
            ) as response:
                try:
                    pbar = tqdm(total=100, desc=f"Generating Image")
                    async for line in response.aiter_lines():
                        last_id_live_preview = process_payload.get(
                            "id_live_preview", -1
                        )
                        if line is not None:
                            progress_info = json.loads(line)
                            if progress_info is not None:
                                pbar.n = int(progress_info.get("progress", 0) * 100)
                                pbar.refresh()
                                # print(progress_info.get("id_live_preview", 0))
                                current_id_live_preview = progress_info.get(
                                    "id_live_preview", -1
                                )
                                global root
                                if root is not None:
                                    root.title(f"Image Generating Progress: {pbar.n}%")
                                if current_id_live_preview != -1:
                                    if (
                                        progress_info.get("live_preview") is not None
                                        and current_id_live_preview
                                        != last_id_live_preview
                                    ):
                                        uri = progress_info.get("live_preview")
                                        await update_image(uri.split(",")[1])
                                        process_payload["id_live_preview"] = (
                                            current_id_live_preview
                                        )
                            if progress_info.get("completed", False):
                                pbar.close()
                                break
                except Exception as e:
                    print(f"Error processing progress stream: {e}")
        except (httpx.RequestError, json.JSONDecodeError) as e:
            print(f"Error checking progress: {e}")


async def update_image(image_data):
    image_data = base64.b64decode(image_data)
    image = Image.open(io.BytesIO(image_data))
    global ratio
    ratio = image.width / image.height
    img_width = int(root.winfo_width())
    img_height = int(img_width / ratio)
    image = image.resize((img_width,img_height), Image.Resampling.BICUBIC)
    tk_image = ImageTk.PhotoImage(image)
    label.config(image=tk_image)
    label.image = tk_image
    label.current_image = image 
    root.bind("<Configure>", lambda event: resize_image(event, ratio))


async def main():
    task_id = str(uuid.uuid4())
    result, _ = await asyncio.gather(generate_image(task_id), check_progress(task_id))
    image_data = base64.b64decode(result.get("images")[0])
    image = Image.open(io.BytesIO(image_data))
    img_width = int(root.winfo_width())
    img_height = int(img_width / ratio)
    image = image.resize((img_width,img_height), Image.Resampling.BICUBIC)
    tk_image = ImageTk.PhotoImage(image)
    label.config(image=tk_image)
    label.image = tk_image
    label.current_image = image

    # root.geometry(f"{int(image.width)}x{int(image.height)}")
    # global ratio
    # ratio = image.width / image.height
    # root.bind("<Configure>", lambda event: resize_image(event, ratio))
    print(json.loads(result.get("info")).get("infotexts")[0])


def resize_image(event, ratio):
    prompt_text.config(width=int(root.winfo_width()))
    new_width = event.width
    new_height = int(new_width / ratio)
    if hasattr(label, "current_image"):
        resized_image = label.current_image.resize(
            (new_width, new_height), Image.Resampling.BICUBIC
        )
        new_tk_image = ImageTk.PhotoImage(resized_image)
        label.config(image=new_tk_image)
        label.image = new_tk_image


# 绑定窗口大小调整事件到 resize_image 函数
def run_asyncio_loop():
    asyncio.run(main())


import threading
def start_gen():
    txt2img_payload["prompt"] = prompt_text.get("1.0", tk.END).strip()
    thread = threading.Thread(target=run_asyncio_loop)
    thread.daemon = True
    thread.start()

ratio = 512 / 768
root = tk.Tk()
root.geometry(f"{int(img_width*scale)}x{int(img_height*scale)}")
root.resizable(True, True)
root.title("SD Image Viewer")
root.configure(bg="#000000")
root.bind("<Configure>", lambda event: resize_image(event, ratio))
label = tk.Label(root,background=root["bg"])
label.pack(fill=tk.BOTH, expand=True)
# 添加多行输入框
prompt_label = tk.Label(root, text="Prompt:", font=("Arial", 16),background=root["bg"],foreground="white")
prompt_label.pack(pady=5)
prompt_text = scrolledtext.ScrolledText(root, width=int(root.winfo_width()), height=5)
prompt_text.pack(pady=5)
prompt_text.insert(tk.INSERT, txt2img_payload.get("prompt"))

# 添加生成图像的按钮
generate_button = tk.Button(root, text="Generate Image", command=start_gen)
generate_button.pack(pady=20)
root.mainloop()
