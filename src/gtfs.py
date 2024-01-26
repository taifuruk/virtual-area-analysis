#%%
import pandas as pd
import zipfile
import json
from collections import defaultdict
from datetime import datetime
import requests
import io
from collections import defaultdict
import geopandas as gpd


def get(url) -> gpd.GeoDataFrame:
    def load_gtfs_data(zip_file_path):
        # GTFSデータを読み込む関数
        with zipfile.ZipFile(zip_file_path, "r") as zip_ref:
            # stops.txt からバス停のデータを読み込む
            with zip_ref.open("stops.txt") as file:
                stops = pd.read_csv(file)

            # stop_times.txt から停留所ごとの時間データを読み込む
            with zip_ref.open("stop_times.txt") as file:
                stop_times = pd.read_csv(file)

            # trips.txt から各トリップ（バス便）の詳細を読み込む
            with zip_ref.open("trips.txt") as file:
                trips = pd.read_csv(file)

            # routes.txt から各ルート（バス路線）の詳細を読み込む
            with zip_ref.open("routes.txt") as file:
                routes = pd.read_csv(file)

        return stops, stop_times, trips, routes

    def adjust_time_format_extended(time_str):
        """時間形式を調整する関数。'24:00:00'以降の時間を調整する。"""
        try:
            time_parts = [int(part) for part in time_str.split(":")]
            if time_parts[0] >= 24:
                time_parts[0] -= 24  # 時間部分を24減らす
            adjusted_time = "{:02d}:{:02d}:{:02d}".format(*time_parts)
            return adjusted_time
        except ValueError:
            # 時間形式が不正な場合は元の文字列を返す
            return time_str

    def calculate_frequencies_adjusted(stop_times, trips, routes):
        """各停留所での頻度データを計算する関数（時間形式を拡張調整）"""

        # tripsとroutesを結合して、各トリップの行先情報を取得
        trip_details = pd.merge(trips, routes, on="route_id")

        # stop_timesとtrip_detailsを結合して、各停留所ごとのトリップの時間を取得
        stop_times_detailed = pd.merge(stop_times, trip_details, on="trip_id")

        # 頻度データを格納するための辞書
        frequencies = defaultdict(
            lambda: defaultdict(lambda: defaultdict(int))
        )

        for _, row in stop_times_detailed.iterrows():
            adjusted_time = adjust_time_format_extended(row["arrival_time"])
            hour = datetime.strptime(adjusted_time, "%H:%M:%S").hour
            frequencies[row["stop_id"]][row["stop_headsign"]][hour] += 1

        # JSON形式で返す
        return {k: v for k, v in frequencies.items()}

    def download_and_load_gtfs_data(url):
        response = requests.get(url)
        if response.status_code == 200:
            with zipfile.ZipFile(io.BytesIO(response.content)) as zip_ref:
                with zip_ref.open("stops.txt") as file:
                    stops = pd.read_csv(file)
                with zip_ref.open("stop_times.txt") as file:
                    stop_times = pd.read_csv(file)
                with zip_ref.open("trips.txt") as file:
                    trips = pd.read_csv(file)
                with zip_ref.open("routes.txt") as file:
                    routes = pd.read_csv(file)
            return stops, stop_times, trips, routes
        else:
            raise Exception("データのダウンロードに失敗しました。")

    stops, stop_times, trips, routes = download_and_load_gtfs_data(url)

    # 頻度データを計算
    frequencies = calculate_frequencies_adjusted(stop_times, trips, routes)

    # stopsデータフレームにfrequencyデータを追加
    stops["frequency"] = stops["stop_id"].map(frequencies)

    # 必要な列のみを選択
    result_table = stops[["stop_name", "stop_lat", "stop_lon", "frequency"]]

    result_table = gpd.GeoDataFrame(
        result_table,
        geometry=gpd.points_from_xy(
            result_table["stop_lon"], result_table["stop_lat"], crs="EPSG:4326"
        ),
    )

    # 結果の最初の数行を表示（全データを表示するには非常に大きい可能性があるため）
    return result_table
    # %%
