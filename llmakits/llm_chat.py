import streamlit as st
from .dispatcher import ModelDispatcher

# 设置标题和欢迎信息
st.title('LLM_batch_chat')
st.write('大模型批量对话服务')

# 模型配置文件路径
models_config = st.text_input("模型(任务组) - yaml 文件路径")
keys_config = st.text_input("模型keys - yaml 文件路径")
global_config = st.text_input("全局对话配置 - csv 文件路径")
system_prompt_path = st.text_input("系统提示词 - md 文件路径")

# 添加载入模型按钮
if st.button("载入模型和配置"):
    # 读取系统提示词文件
    with open(system_prompt_path, 'r', encoding='utf-8') as file:
        # 读取文件内容
        system_prompt = file.read()

    # 初始化模型调度器
    dispatcher = ModelDispatcher(models_config, keys_config, global_config)

    # 保存到session state供后续使用
    st.session_state.system_prompt = system_prompt
    st.session_state.dispatcher = dispatcher
    st.session_state.model_loaded = True
    st.success("模型载入成功！")

# 如果模型已载入，显示模型选择界面
if st.session_state.get('model_loaded', False):
    dispatcher = st.session_state.dispatcher

    group_name = st.selectbox(
        "选择模型组：",
        dispatcher.model_group_names,
    )

    models = dispatcher.model_groups[group_name]
    model_info = models[0]

    provider = model_info.get('sdk_name', 'unknown_sdk')
    model_name = model_info.get('model_name', 'unknown_model')
    st.write("You selected:", provider, model_name)

    # 初始化聊天输入框
    user_input = st.chat_input("Say something")
    user_message = st.chat_message("user")
    assistant_message = st.chat_message("assistant")

    if user_input:
        user_message.write(user_input)
        message_info = {
            "system_prompt": st.session_state.system_prompt,
            "user_text": user_input,
        }
        res, total_tokens = model_info["model"].send_message([], message_info)
        assistant_message.write(res)
