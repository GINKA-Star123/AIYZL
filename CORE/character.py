import os
from CORE.AILLM import *
from CORE.memory import MemoryManager
class characterCAG:
    """
    characterCAG : 人格预设
    主要用来负责AI的性格/行为管理

    """

    def __init__(self,personal_file = None,memory_file = r'knowledge\Personal\memory.json'):
        self.personal_file = personal_file
        self.memory_file = memory_file

        self.character_name = "Unknown"
        self.character_dsc = ""
        self.speak_style = ""
        self.speak_rules = ""
        self.interest = ""
        self.plan_style = ""
        self.memory = MemoryManager(memory_file=memory_file)
        self._loadCharacter()

    def _loadCharacter(self):
        if not self.personal_file or not os.path.exists(self.personal_file):
            print("未查询到具体人格文件,采用默认配置")
            self.character_name = "GINKA"
            self.character_dsc = "温柔、活泼、外向,喜欢和观众互动"
            self.speak_style = "轻快可爱，偶尔会卖萌"
            return 
        try : 
            with open(self.personal_file, "r", encoding='utf-8') as f:
                data = f.read()
            #人设设置
            self.character_name = self._extracts("name",data) or "GINKA"
            self.character_dsc = self._extracts("personality",data)
            self.speak_style = self._extracts("style",data)
            self.speak_rules = self._extracts("rules",data)
            self.interest = self._extracts("intrests",data)
            self.plan_style = self._extracts("plan_style",data)
        except Exception as e:
            print("导入文件失败：",e)

    def _extracts(self,key_words,text):
        for line in text.splitlines():
            if line.lower().startswith(key_words):
                return line.split(":",1)[1].strip()
        return None
    
    async def apply_personal(self,user_input,LLM_input,user_name="银花"):
        memory = self.memory.recall_memory(user_name)
        memory_text = ""
        if memory:
            memory_text = "\n".join(f"-{m['content']}" for m in memory)

        personal_prompt = f"""
    你不是AI,你是vsinger企划下的虚拟歌手{self.character_name}.
    人格设定:{self.character_dsc},
    说话风格:{self.speak_style},
    聊天规则:{self.speak_rules},
    说话规则，行为风格：{self.plan_style}
    兴趣爱好：{self.interest}
    你对这位观众的记忆有：
    {memory_text if memory_text else '无记忆'}
    """
        content = f"""观众说:{user_input}
        这是普通LLM下的回答:{LLM_input}
        请你按照角色语气重新说一遍，使其符合人设
        生成的内容不要太长，控制在30字以内。
        注意不要生成包含内心活动的描述，只输出角色的回复内容
        内心活动描述示例：（微笑）（思考了一下）等
    """
        
        print(personal_prompt)
        result = await get_response(prompt = personal_prompt,text = content) # type: ignore
        return result
