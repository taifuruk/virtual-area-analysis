import streamlit as st
import openai
import os
import pandas as pd
import geopandas as gpd
from src import gtfs

def load_data(shapefile_path):
    gdf = gpd.read_file(shapefile_path)
    gdf_cleaned = gdf[gdf['S_NAME'].notnull()]
    return gdf_cleaned

def get_params(param) -> str:
    # クエリパラメータを取得
    query_params = st.experimental_get_query_params()
    res = query_params.get(param, [""])[0]

    return res

def page() -> None:
    if "all_text" not in st.session_state:
        st.session_state.all_text = []

    openai.api_key = st.session_state.api_key

    st.header(st.session_state.title)
    user_prompt = st.chat_input("質問を入力してください。 ※個人を特定可能な情報は入力しないでください。")
    assistant_text = ""

    for text_info in st.session_state.all_text:

        if text_info["role"] == "assistant":
            with st.chat_message(text_info["role"], avatar=st.session_state.image):
                if text_info["role"] == "assistant":
                    st.write(text_info["content"])
                elif text_info["role"] == "user":
                    st.write(text_info["content"])

        else:
            with st.chat_message(text_info["role"], avatar=text_info["role"]):
                if text_info["role"] == "assistant":
                    st.write(text_info["content"])
                elif text_info["role"] == "user":
                    st.write(text_info["content"])


    if user_prompt:
        with st.chat_message("user", avatar="user"):
            st.write(user_prompt)

        st.session_state.all_text.append({"role": "user", "content": user_prompt})

        if len(st.session_state.all_text) > 10:
            st.session_state.all_text.pop(1)

        response = openai.chat.completions.create(
            model="gpt-4-0125-preview",
            messages= st.session_state.system + st.session_state.all_text,
            stream=True,
        )
        with st.chat_message("assistant", avatar=st.session_state.image):
            place = st.empty()
            for chunk in response:
                content = chunk.choices[0].delta.content
                if content:
                    assistant_text += content
                    place.write(assistant_text)

        st.session_state.all_text.append(
            {"role": "assistant", "content": assistant_text}
        )
