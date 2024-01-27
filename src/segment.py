import streamlit as st
import geopandas as gpd
import folium
from streamlit_folium import folium_static
import openai
import os
import pandas as pd
from src import gtfs
import json
import requests
import html2text
from bs4 import BeautifulSoup


def load_data(shapefile_path):
    gdf = gpd.read_file(shapefile_path)
    gdf_cleaned = gdf[gdf["S_NAME"].notnull()]
    return gdf_cleaned


def generate_map(gdf, pref, city, s_name):
    selected_area = gdf[
        (gdf["PREF_NAME"] == pref)
        & (gdf["CITY_NAME"] == city)
        & (gdf["S_NAME"] == s_name)
    ]
    merged_geom = selected_area.dissolve(by="S_NAME")["geometry"].iloc[0]
    m = folium.Map(
        location=[merged_geom.centroid.y, merged_geom.centroid.x],
        zoom_start=13,
    )
    folium.GeoJson(merged_geom).add_to(m)
    return m, merged_geom, selected_area


# Streamlitアプリのメイン関数
def page() -> None:
    DATA_DIR = "./input/data/"
    LIST_FILE = "./input/list.parquet"

    if not os.path.exists(LIST_FILE):
        empty_df = pd.DataFrame(
            columns=["データタイプ", "タイトル", "説明", "パス", "アップロード日", "カラムの説明"]
        )
        empty_df.to_parquet(LIST_FILE)

    titlecol, datalist = st.columns([0.7, 0.3])
    with titlecol:
        st.title("バーチャル地域分析")
    with datalist:
        if st.button("外部データリスト"):
            st.experimental_set_query_params(page="datalist")

    # ZIPファイルを一時ディレクトリに保存
    zip_path = "input/base/s_area.zip"
    # ZIPファイルを解凍し、Shapeファイルを読み込む
    if "gdf" not in st.session_state:
        st.session_state.gdf = load_data(zip_path)

    gdf = st.session_state.gdf

    # ドロップダウンメニューで選択肢を提供
    col1, col2 = st.columns(2)
    with col1:
        pref = st.selectbox("都道府県を選択", gdf["PREF_NAME"].unique())
        city = st.selectbox(
            "市区町村を選択", gdf[gdf["PREF_NAME"] == pref]["CITY_NAME"].unique()
        )
        s_name = st.selectbox(
            "地区を選択",
            gdf[(gdf["PREF_NAME"] == pref) & (gdf["CITY_NAME"] == city)][
                "S_NAME"
            ].unique(),
        )
        suppl = st.text_area("この地区の情報")
        demand = st.text_area("どんなバーチャル住民を出力したいか")
    with col2:
        if "api_key" not in st.session_state:
            st.session_state.api_key = st.text_input('OpenAI API Key')
        else:
            st.session_state.api_key = st.text_input('OpenAI API Key',st.session_state.api_key)

        map_fig, merged_geom, tgdf = generate_map(gdf, pref, city, s_name)
        folium_static(map_fig, width=700)

    if st.button("バーチャル住民を生成"):
        with st.spinner("データに基づきバーチャル住民を生成中です"):
            openai.api_key = st.session_state.api_key

            df_pop = pd.read_csv(
                "./input/base/h03.csv", encoding="shift_jis", header=4
            )
            df_pop = df_pop[
                (df_pop["市区町村コード"] != "-") & (df_pop["町丁字コード"] != "-")
            ]
            df_pop["uid"] = (
                df_pop["市区町村コード"].astype(int).astype(str)
                + df_pop["町丁字コード"].astype(int).astype(str)
                + "00"
            )
            tgdf["uid"] = (
                tgdf["PREF"].astype(int).astype(str)
                + tgdf["CITY"].astype(int).astype(str)
                + tgdf["S_AREA"].astype(int).astype(str)
            )

            df_pop = df_pop.merge(tgdf[["uid"]], on="uid", how="inner")

            system = """
あなたは敏腕マーケターです。あらゆる情報やデータを見てそれらから重要なペルソナを読み解くことが非常に得意です。これから以下の入力フォーマットに則ってある地域の情報やデータを投稿します。その情報やデータをもとにその地域を代表するペルソナを5つ作成して，以下の出力フォーマットに則ってJSONで出力してください。

【入力フォーマット】
# 地域名
都道府県,市町村,町丁・字等

# 情報
ここに地域の情報が入ります

# 出力してほしいペルソナ
特にどんなペルソナを出力してほしいか，ユーザーの要望が入ります

# 外部データ
## データのタイトル
* データの説明
* カラムの説明
データの内容

【入力フォーマット】
{
    "ペルソナ①のタイトル（例: 移動に不便を抱えている高齢者）":{
        "性別":"男か女かその他",
        "年齢":"10代区切り（0代,10代,20代・・・）",
        "職業":"想定される職業",
        "年収":"想定される年収",
        "家族構成":"想定される家族構成",
        "どのような人物か":"どんなペルソナかを説明してください",
        "悩み":"ペルソナが抱えているであろう悩み",
        "画像生成用プロンプト":"このペルソナを表現可能なある一場面を英語で表現してください。"
    },
    "ペルソナ②のタイトル（例: 移動に不便を抱えている高齢者）":{
        "性別":"男か女かその他",
        "年齢":"10代区切り（0代,10代,20代・・・）",
        "職業":"想定される職業",
        "年収":"想定される年収",
        "家族構成":"想定される家族構成",
        "どのような人物か":"どんなペルソナかを説明してください",
        "悩み":"ペルソナが抱えているであろう悩み",
        "画像生成用プロンプト":"このペルソナを表現可能なある一場面を英語で表現してください。"
    }
    ・・・
}
            """

            df_input = pd.read_parquet("./input/list.parquet")

            data = ""

            for i in df_input[
                ["データタイプ", "タイトル", "説明", "パス", "カラムの説明"]
            ].values.tolist():
                if i[0] == "GTFS":
                    gdf = gtfs.get(i[3])
                    gdf = gdf.loc[gdf.within(merged_geom)]
                    data += f"""
## データのタイトル: {i[1]}
* データの説明: {i[2]}
* カラムの説明: {",".join([key + ": " + i[4][key] for key in i[4] if i[4][key] is not None])}
{gdf[gdf.columns[gdf.columns != 'geometry']].to_csv(index=False)}

                    """
                elif i[0] == "GBFS":
                    d = requests.get(i[3]).json()
                    gdf = pd.DataFrame(d["data"]["stations"])[
                        ["name", "vehicle_capacity", "lat", "lon"]
                    ]
                    gdf = gpd.GeoDataFrame(
                        gdf,
                        geometry=gpd.points_from_xy(
                            gdf["lon"], gdf["lat"], crs="EPSG:4326"
                        ),
                    )
                    gdf = gdf.loc[gdf.within(merged_geom)][
                        ["name", "vehicle_capacity", "geometry"]
                    ]
                    data += f"""
## データのタイトル: {i[1]}
* データの説明: {i[2]}
* カラムの説明: {",".join([key + ": " + i[4][key] for key in i[4] if i[4][key] is not None])}
{gdf[gdf.columns[gdf.columns != 'geometry']].to_csv(index=False)}

                    """

                elif i[0] == "html":

                    def extract_tags(html_content, tags=["p", "a"]):
                        # BeautifulSoupを使ってHTMLを解析
                        soup = BeautifulSoup(
                            html_content, features="html.parser"
                        )

                        # 'main' タグを探す
                        main_tag = soup.find("main")

                        # mainが存在する場合にのみ、その中の 'p' と 'a' タグを抽出
                        if main_tag:
                            # 'p' と 'a' タグを抽出
                            p_and_a_tags = main_tag.find_all(["p", "a"])
                        else:
                            # mainタグがない場合は空のリストを返す
                            p_and_a_tags = []

                        # 抽出したタグを1つのHTMLとして結合
                        extracted_html = "".join(
                            str(tag) for tag in p_and_a_tags
                        )

                        return extracted_html

                    def get_html(url):
                        response = requests.get(url)
                        response.encoding = response.apparent_encoding
                        response.raise_for_status()  # Check that the request was successful
                        return response.text

                    def html_to_markdown(html_content):
                        # BeautifulSoupを使ってHTMLを解析
                        extracted_html_content = extract_tags(
                            html_content, tags=["p", "a"]
                        )

                        # html2textを使ってHTMLをMarkdownに変換
                        text_maker = html2text.HTML2Text()
                        text_maker.ignore_links = True
                        text_maker.bypass_tables = True
                        markdown_content = text_maker.handle(
                            extracted_html_content
                        )

                        return markdown_content

                    def get_content(url) -> str:
                        # WebからHTMLを取得
                        url = "https://www.city.yokohama.lg.jp/kurashi/kosodate-kyoiku/hoiku-yoji/shisetsu/ikea-hoiku/ikeahoiku_support.html"
                        html_content = get_html(url)
                        # HTMLをMarkdownに大換
                        markdown_content = html_to_markdown(html_content)

                        # 結果を出力
                        return markdown_content

                    content = get_content(i[3])
                    data += f"""
## データのタイトル: {i[1]}
* データの説明: {i[2]}
* カラムの説明: 文章データのためカラムなし
{content}

                    """

                else:
                    gdf = gpd.read_parquet(f"./input/data/{i[3]}")
                    gdf = gdf.loc[gdf.within(merged_geom)]
                    data += f"""
## データのタイトル: {i[1]}
* データの説明: {i[2]}
* カラムの説明: {",".join([key + ": " + i[4][key] for key in i[4] if i[4][key] is not None])}
{gdf[gdf.columns[gdf.columns != 'geometry']].to_csv(index=False)}

                    """

            user = f"""
# 地域名
{pref},{city},{s_name}

# 情報
{suppl}

# 出力してほしいペルソナ
{demand}

# 外部データ
## データのタイトル: 人口構成
* データの説明: 年代別・男女別の人口構成
* カラムの説明: 各カラムの意味はカラム名のままです。
{df_pop.to_csv(index=False)}

{data}
            """

            res = openai.chat.completions.create(
                model="gpt-4-0125-preview",
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            )

            res = res.choices[0].message.content

            # JSONデータを辞書に変換
            personas = json.loads(res)

            def images(prompt):
                response = openai.images.generate(
                    model="dall-e-3",
                    prompt=prompt,
                    size="1024x1024",
                    quality="standard",
                    n=1,
                )
                image_url = response.data[0].url
                return image_url

            for persona in personas:
                personas[persona]["images"] = images(
                    personas[persona]["画像生成用プロンプト"]
                )

            def display_persona(persona_data):
                for key, value in persona_data.items():
                    if key != "画像生成用プロンプト":  # 画像生成用プロンプトは表示しない
                        if key != "images":
                            st.write(f"{key}: {value}")

        # 5カラムの作成
        col1, col2, col3, col4, col5 = st.columns(5)
        persona_list = list(personas.items())

        def chat_persona(
            title, gender, age, occ, money, family, details, worries, image
        ):
            st.session_state.system = [
                {
                    "role": "system",
                    "content": f"""
あなたはアンケートの回答者に選ばれた住民の一人です。以下のプロフィールの住民になりきって，質問に答えてください。

* 居住地：{pref}{city}{s_name}
* 性別：{gender}
* 年齢：{age}
* 職業：{occ}
* 年収：{money}
* 家族構成：{family}
* どのような人物か：{details}
* 悩み事：{worries}

この住民が住む地域に関する情報や外部データは以下のとおりです。この情報や外部データも参考にしてやりとりをしてください。
# 情報
{suppl}

# 外部データ
## データのタイトル: 人口構成
* データの説明: 年代別・男女別の人口構成
* カラムの説明: 各カラムの意味はカラム名のままです。
{df_pop.to_csv(index=False)}

{data}

外部データに関しては，人口などのデータに載っている数字をそのまま出力することは禁止です。
""",
                }
            ]

            st.session_state.title = title
            st.session_state.image = image
            st.experimental_set_query_params(page="chat")
            # st.rerun()

        with col1:
            st.subheader(persona_list[0][0], divider="gray")
            st.image(persona_list[0][1]["images"])
            display_persona(persona_list[0][1])
            st.button(
                f"このバーチャル住民と話す",
                on_click=chat_persona,
                args=(
                    persona_list[0][0],
                    persona_list[0][1]["性別"],
                    persona_list[0][1]["年齢"],
                    persona_list[0][1]["職業"],
                    persona_list[0][1]["年収"],
                    persona_list[0][1]["家族構成"],
                    persona_list[0][1]["どのような人物か"],
                    persona_list[0][1]["悩み"],
                    persona_list[0][1]["images"],
                ),
                key=0,
            )

        with col2:
            st.subheader(persona_list[1][0], divider="gray")
            st.image(persona_list[1][1]["images"])
            display_persona(persona_list[1][1])
            st.button(
                f"このバーチャル住民と話す",
                on_click=chat_persona,
                args=(
                    persona_list[1][0],
                    persona_list[1][1]["性別"],
                    persona_list[1][1]["年齢"],
                    persona_list[1][1]["職業"],
                    persona_list[1][1]["年収"],
                    persona_list[1][1]["家族構成"],
                    persona_list[1][1]["どのような人物か"],
                    persona_list[1][1]["悩み"],
                    persona_list[1][1]["images"],
                ),
                key=1,
            )

        with col3:
            st.subheader(persona_list[2][0], divider="gray")
            st.image(persona_list[2][1]["images"])
            display_persona(persona_list[2][1])
            st.button(
                f"このバーチャル住民と話す",
                on_click=chat_persona,
                args=(
                    persona_list[2][0],
                    persona_list[2][1]["性別"],
                    persona_list[2][1]["年齢"],
                    persona_list[2][1]["職業"],
                    persona_list[2][1]["年収"],
                    persona_list[2][1]["家族構成"],
                    persona_list[2][1]["どのような人物か"],
                    persona_list[2][1]["悩み"],
                    persona_list[2][1]["images"],
                ),
                key=2,
            )

        with col4:
            st.subheader(persona_list[3][0], divider="gray")
            st.image(persona_list[3][1]["images"])
            display_persona(persona_list[3][1])
            st.button(
                f"このバーチャル住民と話す",
                on_click=chat_persona,
                args=(
                    persona_list[3][0],
                    persona_list[3][1]["性別"],
                    persona_list[3][1]["年齢"],
                    persona_list[3][1]["職業"],
                    persona_list[3][1]["年収"],
                    persona_list[3][1]["家族構成"],
                    persona_list[3][1]["どのような人物か"],
                    persona_list[3][1]["悩み"],
                    persona_list[3][1]["images"],
                ),
                key=3,
            )

        with col5:
            st.subheader(persona_list[4][0], divider="gray")
            st.image(persona_list[4][1]["images"])
            display_persona(persona_list[4][1])
            st.button(
                f"このバーチャル住民と話す",
                on_click=chat_persona,
                args=(
                    persona_list[4][0],
                    persona_list[4][1]["性別"],
                    persona_list[4][1]["年齢"],
                    persona_list[4][1]["職業"],
                    persona_list[4][1]["年収"],
                    persona_list[4][1]["家族構成"],
                    persona_list[4][1]["どのような人物か"],
                    persona_list[4][1]["悩み"],
                    persona_list[4][1]["images"],
                ),
                key=4,
            )
