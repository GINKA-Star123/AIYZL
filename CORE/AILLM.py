from openai import OpenAI
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from local import *

client = OpenAI(
    api_key=SILICONFLOW_API,
    base_url="https://api.siliconflow.cn/v1") 

async def get_response(prompt,text):
    try:
        response = client.chat.completions.create(
            model="Qwen/Qwen3-VL-32B-Instruct",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": text},
            ],
            stream=False
        )
        return response.choices[0].message.content
    except : 
        print("请求失败")
