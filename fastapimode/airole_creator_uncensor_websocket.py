import os,yaml,aiofiles
from fastapimode.sys_path import project_root
from modules.global_sets_async import roleconf
dir_path = project_root
# dir_path = os.path.dirname(os.path.realpath(__file__))
yaml_dir_path = os.path.join(dir_path, 'config', 'personas')

class airole:
    def __init__(self,roleselector,username,usergender): 
        self.roleselector = roleselector
        self.user_role_name = username
        self.user_role_gender = usergender
        
    async def async_init(self):
        self.ai_speaker = roleconf[f'{self.roleselector}']['ai_speaker']
        self.ai_speaker_en = roleconf[f'{self.roleselector}']['ai_speaker_en']
        self.ai_if_uncensored = roleconf[f'{self.roleselector}']['if_uncensored'] 
        self.ai_role_name = roleconf[f'{self.roleselector}']['ai_name']
        self.yaml_file_path = os.path.join(yaml_dir_path, self.roleselector+'.yaml')
        async with aiofiles.open(self.yaml_file_path, mode="r") as f:
            contents = await f.read()
            persona_data = yaml.safe_load(contents)
        self.ai_system_role = persona_data['description']
        self.welcome_text_dec = persona_data['firstwords']
        self.char_looks = persona_data['char_looks']
        self.char_avatar = persona_data['char_avatar']
        self.backgroundImg = persona_data['default_bg']
        self.chapters = persona_data['chapters']
        self.custom_comp_data = persona_data['completions_data'] if 'completions_data' in persona_data else False
        self.generate_dynamic_picture = persona_data['generate_dynamic_picture'] if 'generate_dynamic_picture' in persona_data else True
        self.model_to_load = persona_data['model_to_load'] if 'model_to_load' in persona_data else False
        self.prompt_to_load = persona_data['prompt_to_load'] if 'prompt_to_load' in persona_data else False
        self.match_words_cata = persona_data['match_words_cata'] if 'match_words_cata' in persona_data else "SFW"
        self.char_outfit = persona_data['char_outfit'] if 'char_outfit' in persona_data else None