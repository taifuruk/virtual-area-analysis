import streamlit as st
import pandas as pd
import os

def page() -> None:
    # パス設定
    DATA_DIR = "./input/data/"
    LIST_FILE = "./input/list.parquet"

    titlecol, seg = st.columns([0.7, 0.3])
    with titlecol:
        st.title("データリスト")
    with seg:
        if st.button("分析ページへ戻る"):
            st.experimental_set_query_params(page="segment")

    # list.parquetが存在しない場合は空のDataFrameを作成
    if not os.path.exists(LIST_FILE):
        empty_df = pd.DataFrame(columns=['データタイプ','タイトル', '説明', 'パス', 'アップロード日', 'カラムの説明'])
        empty_df.to_parquet(LIST_FILE)

    # list.parquetを読み込む
    data_list = pd.read_parquet(LIST_FILE)
    # 削除するデータのパスを保存するためのリスト
    delete_paths = []

    # データ一覧を表示
    for index, row in data_list.iterrows():
        col1, col2 = st.columns([0.1, 0.9])
        with col1:
            # チェックボックスのキーをデータのパスに設定
            delete = st.checkbox("削除", key=row['パス'])
            if delete:
                delete_paths.append(row['パス'])

        with col2:
            if row['データタイプ'] == 'CSV' or row['データタイプ'] == 'GeoJSON':
                st.markdown(f"* {row['タイトル']} - {row['説明']} - 追加日:{row['アップロード日']}")
            elif row['データタイプ'] == 'GTFS' or row['データタイプ'] == 'html' or row['データタイプ'] == 'GBFS':
                st.markdown(f"* {row['タイトル']} - {row['説明']} - URL:{row['パス']}")

    # 選択されたデータの削除
    if st.button("選択したデータを削除"):
        for delete_path in delete_paths:
            # ファイルの削除
            if os.path.exists(os.path.join(DATA_DIR, delete_path)):
                os.remove(os.path.join(DATA_DIR, delete_path))

            # DataFrameから行を削除
            data_list = data_list[data_list['パス'] != delete_path]

        # 更新されたDataFrameを保存
        data_list.to_parquet(LIST_FILE)
        # 削除後のリストを表示
        st.write("削除完了")
        st.rerun()

    def move2add_data():
        st.experimental_set_query_params(page="add_data")
        # st.rerun()

    # データ追加ページへのリンク
    st.button("データの追加", on_click=move2add_data)

