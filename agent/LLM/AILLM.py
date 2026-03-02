from openai import OpenAI
import os
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()

# 设置代理
client = OpenAI(
    api_key=os.getenv("SILICONFLOW_API"),
    base_url="https://api.siliconflow.cn/v1") 

# 生成相关回复

async def get_response(prompt,text):
    try:
        response = client.chat.completions.create(
            model="Pro/MiniMaxAI/MiniMax-M2.5",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": text},
            ],
            stream=False
        )
        return response.choices[0].message.content
    except : 
        print("请求失败")
