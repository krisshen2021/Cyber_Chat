import os, sys, asyncio
from pathlib import Path

# from fastapimode.sys_path import project_root
project_root = str(Path(__file__).parents[1])
if project_root not in sys.path:
    sys.path.append(project_root)
from modules.global_sets_async import init_memory
from modules.AiRoleOperator import AiRoleOperator as ARO

dir_path = project_root
# dir_path = os.path.dirname(os.path.realpath(__file__))
yaml_dir_path = os.path.join(dir_path, "config", "personas")


class airole:
    def __init__(
        self,
        char_uid: str,
        user_uid: str,
        username: str,
        usergender: str,
    ):
        self.char_uid = char_uid
        self.user_uid = user_uid
        self.username = username
        self.usergender = usergender

    async def async_init(self, ai_is_memory_mode: bool = False):
        if ai_is_memory_mode is True:
            self.cyberchat_memory = await init_memory()
        else:
            self.cyberchat_memory = None
        role_result = await ARO.fetch_airole(ai_Name=self.char_uid)
        self.ai_speaker = role_result["Ai_speaker"]
        self.ai_speaker_en = role_result["Ai_speaker_en"]
        self.ai_if_uncensored = role_result["is_Uncensored"]
        self.ai_role_name = role_result["Ai_name"]
        self.story_intro = role_result["json_Story_intro"]
        self.prologue = role_result["Prologue"]
        role_desc = f"""<Plot_of_the_RolePlay>
{role_result['Prologue']}
</Plot_of_the_RolePlay>

<Characters_Persona>

<Persona_of_{{{{char}}}}>      
{role_result['Char_Persona']}
</Persona_of_{{{{char}}}}>

<Persona_of_{{{{user}}}}>    
{role_result['User_Persona']}
</Persona_of_{{{{user}}}}>

</Characters_Persona>

# Role play start:
<|Current Chapter|>

"""
        self.ai_system_role = role_desc
        # fetch the first words of the role base on memory mode
        if ai_is_memory_mode is True:
            previous_summary = await self.cyberchat_memory.fetch_previous_summary(
                char_uid=self.char_uid,
                user_uid=self.user_uid,
                owner=self.ai_role_name,
                user_name=self.username,
                vector_name="memory_vector",
            )
            if previous_summary is not None:
                self.welcome_text_dec = f"*{previous_summary['previous_summary_owner']}*\n\n**Your last words:**\n\n{previous_summary['the_latest_words_user'].strip()}\n\n**My Reply:**\n\n{previous_summary['the_latest_words_owner'].strip()}"
            else:
                self.welcome_text_dec = role_result["Firstwords"]
            await asyncio.sleep(0.2)
            await self.cyberchat_memory.close_client()
        else:
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
