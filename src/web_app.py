import streamlit as st
import os
import time
from data_manager import DataManager
from agent import NutritionAgent
from dotenv import load_dotenv

# Load env for Agent
load_dotenv()

st.set_page_config(layout="wide", page_title="FoodFlow Control", page_icon="🥗")

# Initialize
if "dm" not in st.session_state:
    st.session_state.dm = DataManager()
if "agent" not in st.session_state:
    st.session_state.agent = NutritionAgent(st.session_state.dm)
if "messages" not in st.session_state:
    st.session_state.messages = []

dm = st.session_state.dm
agent = st.session_state.agent

# Sidebar: Settings
with st.sidebar:
    st.header("⚙️ Settings")
    
    # Language
    current_settings = dm.get_settings()
    lang_options = {"English": "en", "Russian": "ru", "Spanish": "es"}
    # Reverse lookup for index
    inv_lang = {v: k for k, v in lang_options.items()}
    default_idx = list(lang_options.values()).index(current_settings.get("language", "en"))
    
    selected_lang_name = st.selectbox("Language / Язык", list(lang_options.keys()), index=default_idx)
    selected_lang_code = lang_options[selected_lang_name]
    
    if selected_lang_code != current_settings.get("language", "en"):
        new_settings = current_settings.copy()
        new_settings["language"] = selected_lang_code
        dm.save_settings(new_settings)
        st.success("Language saved! / Язык сохранен!")
        time.sleep(1)
        st.rerun()

    st.markdown("---")
    st.markdown("### About")
    st.info(
        "**FoodFlow** helps you manage your nutrition.\n\n"
        "Use the **Chat** to talk naturally.\n"
        "Use the **Data Editor** to fix or view tables."
    )

st.title("🥗 FoodFlow Command Center")

# Welcome Message
if not st.session_state.messages:
    welcome_text = (
        "Hello! I am ready to help. Please tell me about what you bought, what you ate, "
        "or ask for a meal plan. You can check the tables on the left to see what I know."
        if current_settings.get("language") == "en" else
        "Привет! Я готов помочь. Расскажи мне, что купил, что съел, или спроси план питания. "
        "Слева можно проверить таблицы, чтобы увидеть, что я знаю."
    )
    st.session_state.messages.append({"role": "assistant", "content": welcome_text})

# Main Layout
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("🗃️ Memory / Память")
    
    files = list(dm.SCHEMAS.keys())
    # Human readable tabs
    tabs = st.tabs([f.replace('.csv', '').replace('_', ' ').title() for f in files])
    
    for i, file in enumerate(files):
        with tabs[i]:
            data = dm.read_table(file)
            st.write(f"Editing **{file}**")
            edited_data = st.data_editor(data, num_rows="dynamic", key=f"editor_{file}")
            
            if st.button(f"Save {file}", key=f"save_{file}"):
                dm.save_table(file, edited_data)
                st.success(f"Saved {file}!")
                time.sleep(1)
                st.rerun()

with col2:
    st.subheader("💬 Chat / Чат")
    
    # Render chat history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Chat input
    if prompt := st.chat_input("Say something... / Скажи что-нибудь..."):
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Agent response
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            message_placeholder.markdown("Thinking... 🧠")
            
            # Call Agent
            response_text = agent.process_message(prompt)
            
            message_placeholder.markdown(response_text)
            st.session_state.messages.append({"role": "assistant", "content": response_text})
            
            # Force refresh of left column if tool calls happened (implicit via rerun or let user refresh)
            # Rerun is better to show updates immediately
            st.rerun()
