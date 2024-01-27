from src import datalist, adddata, chat, segment
import streamlit as st
import warnings

warnings.simplefilter("ignore")

st.set_page_config(layout="wide")
# クエリパラメータを取得
query_params = st.experimental_get_query_params()
page = query_params.get("page", [""])[0]

if page == "datalist":
    datalist.page()

elif page == "add_data":
    adddata.page()

elif page == "chat":
    chat.page()

elif page == "segment":
    segment.page()

else:
    segment.page()
