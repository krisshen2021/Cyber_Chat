import os, yaml, aiofiles, sys
from pathlib import Path

# from fastapimode.sys_path import project_root
project_root = str(Path(__file__).parents[1])
if project_root not in sys.path:
    sys.path.append(project_root)
from modules.global_sets_async import roleconf, logging
from modules.AiRoleOperator import AiRoleOperator as ARO

dir_path = project_root
# dir_path = os.path.dirname(os.path.realpath(__file__))
yaml_dir_path = os.path.join(dir_path, "config", "personas")


class airole:
    def __init__(self, roleselector, username, usergender):
        self.roleselector = roleselector
        self.user_role_name = username
        self.user_role_gender = usergender

    async def async_init(self):
        self.ai_speaker = roleconf[f"{self.roleselector}"]["ai_speaker"]
        self.ai_speaker_en = roleconf[f"{self.roleselector}"]["ai_speaker_en"]
        self.ai_if_uncensored = roleconf[f"{self.roleselector}"]["if_uncensored"]
        self.ai_role_name = roleconf[f"{self.roleselector}"]["ai_name"]
        role_result = await ARO.fetch_airole(ai_Name=self.roleselector)
        # logging.info(role_result)
        role_desc = f"""
# Prologue
        
{role_result['Prologue']}
        
# Characters Persona

{{{{char}}}}'s Persona:       
{role_result['Char_Persona']}

{{{{user}}}}'s Persona:       
{role_result['User_Persona']}
        
# Story
<|Current Chapter|>
"""
        self.ai_system_role = role_desc
        self.welcome_text_dec = role_result["Firstwords"]
        self.char_looks = role_result["Char_looks"]
        self.char_avatar = role_result["Char_avatar"]
        self.backgroundImg = role_result["Default_bg"]
        self.chapters = role_result["json_Chapters"]
        self.custom_comp_data = role_result["json_Completions_data"]
        self.generate_dynamic_picture = role_result["is_Gen_DynaPic"]
        self.model_to_load = (
            role_result["Model_to_load"] if "Model_to_load" in role_result else False
        )
        self.prompt_to_load = (
            role_result["Prompt_to_load"] if "Prompt_to_load" in role_result else False
        )
        self.match_words_cata = role_result["Match_words_cata"]
        self.char_outfit = (
            role_result["json_Char_outfit"]
            if "json_Char_outfit" in role_result
            else None
        )
