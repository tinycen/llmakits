import streamlit as st

# 设置标题和欢迎信息
st.title('LLM_Chat')
st.write('大模型对话 服务')

models_config = st.text_input("模型(任务组) - yaml 文件路径")
keys_config = st.text_input("模型keys - yaml 文件路径")
global_config = st.text_input("全局对话配置 - yaml 文件路径")
system_prompt_path = st.text_input("系统提示词 - md 文件路径")
