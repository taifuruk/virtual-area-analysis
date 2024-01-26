import streamlit as st
import pandas as pd
import os
import uuid
from datetime import datetime
import geopandas as gpd
from shapely import wkt


def page() -> None:
    # パス設定
    DATA_DIR = "./input/data/"
    LIST_FILE = "./input/list.parquet"

    # "add_data" ページの場合のみ表示
    st.experimental_set_query_params(page="add_data")
    titlecol, datalist, seg = st.columns([0.5, 0.25, 0.25])

    with titlecol:
        st.title("データ追加")
    with datalist:
        if st.button("データリストに戻る"):
            st.experimental_set_query_params(page="datalist")
    with seg:
        if st.button("分析ページへ戻る"):
            st.experimental_set_query_params(page="segment")

    kind = st.selectbox(
        "データの種類", ["CSV", "GeoJSON", "GTFS", "GBFS", "Webページ（HTML）"]
    )

    if kind == "CSV":
        uploaded_file = st.file_uploader("CSVファイルをアップロード", type="csv")

        if uploaded_file is not None:
            # CSVを読み込む
            df = pd.read_csv(uploaded_file)
            title = st.text_input("データのタイトル")
            description = st.text_area("データの説明")
            use_wkt = st.radio("WKTを使用するか", ("はい", "いいえ"))

            # カラムの説明入力
            column_descriptions = {}
            for column in df.columns:
                col_desc = st.text_input(f"'{column}' カラムの説明", key=column)
                column_descriptions[column] = col_desc if col_desc else None

            if use_wkt == "はい":
                wkt_column = st.selectbox("WKT列の名称", df.columns)
                df["geometry"] = df[wkt_column].map(wkt.loads)
                df = gpd.GeoDataFrame(df, geometry="geometry")
            else:
                latitude_column = st.selectbox("緯度列の名称", df.columns)
                longitude_column = st.selectbox("経度列の名称", df.columns)
                df = gpd.GeoDataFrame(
                    df,
                    geometry=gpd.points_from_xy(
                        df[longitude_column],
                        df[latitude_column],
                        crs="EPSG:4326",
                    ),
                )

            if st.button("データを追加"):
                # ファイル名を生成
                file_name = f"{uuid.uuid4()}.parquet"

                # ファイルを保存
                df.to_parquet(os.path.join(DATA_DIR, file_name), index=False)
                # リストを更新
                new_data = pd.DataFrame(
                    {
                        "データタイプ": [kind],
                        "タイトル": [title],
                        "説明": [description],
                        "パス": [file_name],
                        "アップロード日": [datetime.now()],
                        "カラムの説明": [column_descriptions],
                    }
                )
                data_list = pd.read_parquet(LIST_FILE)
                data_list = pd.concat([data_list, new_data])
                data_list.to_parquet(LIST_FILE)
                st.success("データが追加されました！")

    elif kind == "GTFS":
        url = st.text_input("URLを入力してください")
        title = st.text_input("データのタイトル")
        description = st.text_area("データの説明")
        if st.button("データを追加"):
            new_data = pd.DataFrame(
                {
                    "データタイプ": [kind],
                    "タイトル": [title],
                    "説明": [description],
                    "パス": [url],
                    "アップロード日": [None],
                    "カラムの説明": [
                        {
                            "stop_name": "バス停名",
                            "frequency": '運行頻度。{"行き先":{○時代:運行本数},"行き先":{○時代:運行本数}}という表現で表される',
                        }
                    ],
                }
            )
            data_list = pd.read_parquet(LIST_FILE)
            data_list = pd.concat([data_list, new_data])
            data_list.to_parquet(LIST_FILE)
            st.success("データが追加されました！")

    elif kind == "GBFS":
        url = st.text_input("URLを入力してください(station_information.json)")
        title = st.text_input("データのタイトル")
        description = st.text_area("データの説明")
        if st.button("データを追加"):
            new_data = pd.DataFrame(
                {
                    "データタイプ": [kind],
                    "タイトル": [title],
                    "説明": [description],
                    "パス": [url],
                    "アップロード日": [None],
                    "カラムの説明": [
                        {"name": "シェアサイクルポート名", "vehicle_capacity": "駐輪可能台数"}
                    ],
                }
            )
            data_list = pd.read_parquet(LIST_FILE)
            data_list = pd.concat([data_list, new_data])
            data_list.to_parquet(LIST_FILE)
            st.success("データが追加されました！")

    elif kind == "GeoJSON":
        uploaded_file = st.file_uploader(
            "GeoJSONファイルをアップロード", type=["geojson", "json"]
        )

        if uploaded_file is not None:
            df = gpd.read_file(uploaded_file)
            title = st.text_input("データのタイトル")
            description = st.text_area("データの説明")

            # カラムの説明入力
            column_descriptions = {}
            for column in df.columns[df.columns != "geometry"]:
                col_desc = st.text_input(f"'{column}' カラムの説明", key=column)
                column_descriptions[column] = col_desc if col_desc else None

            if st.button("データを追加"):
                # ファイル名を生成
                file_name = f"{uuid.uuid4()}.parquet"

                # ファイルを保存
                df.to_parquet(os.path.join(DATA_DIR, file_name), index=False)
                # リストを更新
                new_data = pd.DataFrame(
                    {
                        "データタイプ": [kind],
                        "タイトル": [title],
                        "説明": [description],
                        "パス": [file_name],
                        "アップロード日": [datetime.now()],
                        "カラムの説明": [column_descriptions],
                    }
                )
                data_list = pd.read_parquet(LIST_FILE)
                data_list = pd.concat([data_list, new_data])
                data_list.to_parquet(LIST_FILE)
                st.success("データが追加されました！")

    elif kind == "Webページ（HTML）":
        kind = "html"
        url = st.text_input("URLを入力してください")
        title = st.text_input("データのタイトル")
        description = st.text_area("データの説明")
        if st.button("データを追加"):
            new_data = pd.DataFrame(
                {
                    "データタイプ": [kind],
                    "タイトル": [title],
                    "説明": [description],
                    "パス": [url],
                    "アップロード日": [None],
                    "カラムの説明": [None],
                }
            )
            data_list = pd.read_parquet(LIST_FILE)
            data_list = pd.concat([data_list, new_data])
            data_list.to_parquet(LIST_FILE)
            st.success("データが追加されました！")
