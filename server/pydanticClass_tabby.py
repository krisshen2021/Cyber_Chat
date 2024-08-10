from typing import Optional, List, Dict, Union
from pydantic import BaseModel

class CompletionsParam(BaseModel):
    prompt: str  # string
    max_tokens: Optional[int] = None  # 150
    min_tokens: Optional[int] = None  # 0
    generate_window: Optional[int] = None  # 512
    stop: Optional[Union[str, List[str]]] = None  # string
    banned_strings: Optional[str] = None  # string
    banned_tokens: Optional[List[int]] = None  # [128, 330]
    token_healing: Optional[bool] = None  # true
    temperature: Optional[Union[int, float]] = None  # 1
    temperature_last: Optional[bool] = None  # true
    smoothing_factor: Optional[float] = None  # 0
    top_k: Optional[int] = None  # 0
    top_p: Optional[Union[int, float]] = None  # 1
    top_a: Optional[Union[int, float]] = None  # 0
    min_p: Optional[Union[int, float]] = None  # 0
    tfs: Optional[Union[int, float]] = None  # 1
    typical: Optional[Union[int, float]] = None  # 1
    skew: Optional[Union[int, float]] = None  # 0
    frequency_penalty: Optional[Union[int, float]] = None  # 0
    presence_penalty: Optional[Union[int, float]] = None  # 0
    repetition_penalty: Optional[Union[int, float]] = None  # 1
    penalty_range: Optional[Union[int, float]] = None  # 0
    repetition_decay: Optional[Union[int, float]] = None  # 0
    mirostat_mode: Optional[Union[int, float]] = None  # 0
    mirostat_tau: Optional[Union[int, float]] = None  # 1.5
    mirostat_eta: Optional[Union[int, float]] = None  # 0.3
    add_bos_token: Optional[bool] = None  # true
    ban_eos_token: Optional[bool] = None  # false
    skip_special_tokens: Optional[bool] = None  # true
    logit_bias: Optional[Dict[str, int]] = None  # { "1": 10, "2": 50 }
    negative_prompt: Optional[str] = None  # string
    json_schema: Optional[str] = None  # string
    regex_pattern: Optional[str] = None  # string
    grammar_string: Optional[str] = None  # string
    speculative_ngram: Optional[bool] = None  # true
    cfg_scale: Optional[Union[int, float]] = None  # 1
    max_temp: Optional[Union[int, float]] = None  # 1
    min_temp: Optional[Union[int, float]] = None  # 1
    temp_exponent: Optional[Union[int, float]] = None  # 1
    model: Optional[str] = None  # string
    stream: Optional[bool] = False  # false
    stream_options: Optional[Dict[str, bool]] = None  # { "include_usage": false }
    logprobs: Optional[int] = None  # 0
    response_format: Optional[Dict[str, str]] = None  # { "type": "text" }
    n: Optional[Union[int, float]] = None  # 0
    best_of: Optional[Union[int, float]] = None  # 0
    echo: Optional[bool] = None  # false
    suffix: Optional[str] = None  # string
    user: Optional[str] = None  # string

class ChatCompletionParam(CompletionsParam):
    prompt: Optional[str] = None  # Overriding to make prompt optional
    messages: str  # Making messages a required field
    prompt_template: Optional[str] = None  # string
    add_generation_prompt: Optional[bool] = None  # true
    template_vars: Optional[Dict] = None  # {}
    response_prefix: Optional[str] = None  # string

class Draft(BaseModel):
    draft_model_name: Optional[str] = None  # "string"
    draft_rope_scale: Optional[Union[int, float]] = None  # 0
    draft_rope_alpha: Optional[Union[int, float]] = None  # 1
    draft_cache_mode: Optional[str] = None  # "string"

class LoadModelParam(BaseModel):
    name: str  # "string"
    max_seq_len: Optional[int] = None  # 4096
    override_base_seq_len: Optional[int] = None  # 4096
    cache_size: Optional[int] = None  # 4096
    gpu_split_auto: Optional[bool] = None  # true
    autosplit_reserve: Optional[List[Union[int, float]]] = None  # [0]
    gpu_split: Optional[List[Union[int, float]]] = None  # [24, 20]
    rope_scale: Optional[Union[int, float]] = None  # 1
    rope_alpha: Optional[Union[int, float]] = None  # 1
    cache_mode: Optional[str] = None  # "string"
    chunk_size: Optional[int] = None  # 0
    prompt_template: Optional[str] = None  # "string"
    num_experts_per_token: Optional[int] = None  # 0
    fasttensors: Optional[bool] = None  # true
    draft: Optional[Draft] = None  # Draft instance
    skip_queue: Optional[bool] = None  # false
    
