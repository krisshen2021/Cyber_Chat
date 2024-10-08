from modules.global_sets_async import getGlobalConfig
import asyncio

config_data = asyncio.run(getGlobalConfig("config_data"))

sd_payload = {
    "hr_negative_prompt": "",
    "negative_prompt": "",
    "hr_prompt": "",
    "hr_scale": 1.5,
    "hr_second_pass_steps": 40,
    "seed": -1,
    "enable_hr": False,
    "width": 256,
    "height": 256,
    "hr_upscaler": config_data["hr_upscaler"],
    "sampler_name": config_data["sampler_name"],
    "cfg_scale": 1.5,
    "denoising_strength": 0.7,
    "steps": 40,
    "prompt": "a cat",
    "override_settings": {
        "sd_vae": "Automatic",
        "sd_model_checkpoint": config_data["sd_model_checkpoint"],
    },
    "override_settings_restore_afterwards": True,
}

sd_payload_for_vram = {
    "high": {
        "hr_second_pass_steps": 10,
        "steps": 30,
        "cfg_scale": 7,
        "denoising_strength": 0.55
    },
    "low": {
        "hr_second_pass_steps": 10,
        "steps": 12,
        "cfg_scale": 2,
        "denoising_strength": 0.7
    },
}

room_state = {
    "openai_api_chat_base": config_data["openai_api_chat_base"],
    "tappyapi_api_key": config_data["api_key"],
    "tappyapi_admin_key": config_data["admin_key"],
    "SDAPI_url": config_data["SDAPI_url"],
    "prompt_template": "Alpaca_RP",
    "char_name": "",
    "user_name": "",
    # completions data
    "max_seq_len": 4096,
    "max_tokens": 300,
    "top_k": 50,
    "top_p": 1,
    "min_p": 0.05,
    "tfs": 0.95,
    "frequency_penalty": 0,
    "presence_penalty": 0.4,
    "repetition_penalty": 1.1,
    "mirostat_mode": 0,
    "mirostat_tau": 1.5,
    "mirostat_eta": 0.1,
    "temperature_last": True,
    "ban_eos_token": False,
    "custom_stop_string": ["###", "</s>", "<|eot_id|>"],
    "temperature": 1,
    # other settings
    "translate": True,
    "char_looks": "",
    "char_outfit": None,
    "char_avatar": "",
    "env_setting": "",
    "conversation_id": "",
    "generate_dynamic_picture": True,
    "match_words_cata": "",
    "prompts_templates": {},
}
# "model": "",
# "best_of": 0,
# "echo": False,
# "logprobs": 0,
# "n": 1,
# "suffix": "string",
# "user": "string",
completions_data = {
    "stream": False,
    "stop": ["###"],
    "max_tokens": 150,
    "token_healing": True,
    "temperature": 0.7,
    # "temperature_last": True,
    # "top_k": 0,
    # "top_p": 1,
    # "top_a": 0,
    # "typical": 1,
    # "min_p": 0.01,
    # "tfs": 0.95,
    "frequency_penalty": 0,
    "presence_penalty": 1.2,
    "repetition_penalty": 1.1,
    # "repetition_decay": 0,
    "mirostat_mode": 0,
    "mirostat_tau": 1.5,
    "mirostat_eta": 0.1,
    "add_bos_token": True,
    "ban_eos_token": False,
    # "repetition_range": -1,
    # "smoothing_factor":0.95,
    "prompt": "Output: 'No input'",
}
model_load_data = {
    "name": "",
    "max_seq_len": 4096,
    # "override_base_seq_len": 0,
    "gpu_split_auto": True,
    "gpu_split": [0],
    # "rope_scale": 1,
    # "rope_alpha": 0,
    # "cache_mode": "FP16",
    "prompt_template": "string",
    # "num_experts_per_token": 0,
    # "draft": {
    #     "draft_model_name": "string",
    #     "draft_rope_scale": 1,
    #     "draft_rope_alpha": 0
    # }
}
