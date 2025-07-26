from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from typing import List

# 同じディレクトリにあるmodels.pyからAppモデルをインポート
from .models import App

# FastAPIアプリケーションのインスタンスを作成
app = FastAPI(title="Cat-box API")

# app = FastAPI(...) の下に追記

# --- CORS設定 ---
# 開発中にローカルのフロントエンドやランチャーからアクセスできるようにするため、
# 特定のオリジンからのリクエストを許可する。
origins = [
    "http://localhost",
    "http://localhost:3000", # 一般的なフロントエンド開発サーバー
    "http://localhost:8080", # 一般的なフロントエンド開発サーバー
    # 必要に応じて、将来のWebサイトのドメインなどもここに追加する
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"], # 全てのHTTPメソッドを許可 (GET, POST, etc.)
    allow_headers=["*"], # 全てのヘッダーを許可
)
# --- CORS設定ここまで ---

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
        download_url="https://cat-box-apps-19940623.s3.ap-northeast-1.amazonaws.com/dummy_app.zip"
    ),
    App(
        id=2,
        name="Simple Memo Pad",
        version="0.9.1",
        description="A very simple memo pad. That's it.",
        icon_url="https://placekitten.com/201/201",
        download_url="https://cat-box-apps-19940623.s3.ap-northeast-1.amazonaws.com/dummy_app.zip"
    ),
    App(
        id=3,
        name="Weather Cat",
        version="1.2.0",
        description=None, # OptionalなフィールドはNoneでもOK
        icon_url="https://placekitten.com/202/202",
        download_url="https://cat-box-apps-19940623.s3.ap-northeast-1.amazonaws.com/dummy_app.zip"
    ),
]
# --- ダミーデータここまで ---


@app.get("/api/v1/apps", response_model=List[App])
async def get_apps():
    """
    登録されている全てのアプリケーションのリストを取得します。
    """
    return dummy_apps_db

@app.post("/api/v1/apps/upload")
async def upload_app(file: UploadFile = File(...)):
    """
    アプリケーションのzipファイルをアップロードします。
    ステップ4-1の時点では、ファイルを受け取って情報を表示するだけです。
    """
    print(f"Received file: {file.filename}")
    print(f"Content-Type: {file.content_type}")

    # ここに今後、ファイルの検証ロジックを追加していく

    return {"filename": file.filename, "content_type": file.content_type}