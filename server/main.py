from fastapi import FastAPI
from typing import List

# 先ほど作成したmodels.pyからAppモデルをインポート
from .models import App

# FastAPIアプリケーションのインスタンスを作成
app = FastAPI(title="Cat-box API")

# --- ダミーデータ ---
# ステップ1-2で定義したAppモデルに従った、ハードコードされたデータ。
# 本来はデータベースから取得するが、今は仮のデータを用意する。
dummy_apps_db = [
    App(
        id=1,
        name="Super Shift App",
        version="1.0.0",
        description="A revolutionary application for managing your work shifts with ease.",
        icon_url="https://placekitten.com/200/200", # かわいい猫のダミー画像
        download_url="http://example.com/downloads/shift_app_v1.0.0.zip"
    ),
    App(
        id=2,
        name="Simple Memo Pad",
        version="0.9.1",
        description="A very simple memo pad. That's it.",
        icon_url="https://placekitten.com/201/201",
        download_url="http://example.com/downloads/simple_memo_v0.9.1.zip"
    ),
    App(
        id=3,
        name="Weather Cat",
        version="1.2.0",
        description=None, # OptionalなフィールドはNoneでもOK
        icon_url="https://placekitten.com/202/202",
        download_url="http://example.com/downloads/weather_cat_v1.2.0.zip"
    ),
]
# --- ダミーデータここまで ---


@app.get("/api/v1/apps", response_model=List[App])
async def get_apps():
    """
    登録されている全てのアプリケーションのリストを取得します。
    """
    return dummy_apps_db