from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import shutil
import os

# 同じディレクトリにあるmodels.pyからAppモデルをインポート
from .models import App

# --- 定数を定義 ---
# 将来的に設定ファイルに移動することも検討
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB
UPLOAD_DIR = "uploads" # アップロードされたファイルを一時的に保存するディレクトリ

# サーバー起動時にアップロード用ディレクトリを作成
os.makedirs(UPLOAD_DIR, exist_ok=True)
# --- 定数ここまで ---

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
    ファイルサイズとコンテントタイプの検証を追加。
    """
    # Content-Typeの検証
    if file.content_type not in ["application/zip", "application/x-zip-compressed"]:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type: {file.content_type}. Only .zip files are allowed."
        )

    # 一時ファイルに保存してサイズをチェック
    temp_file_path = os.path.join(UPLOAD_DIR, file.filename)
    try:
        # ファイルをチャンクで書き込む
        with open(temp_file_path, "wb") as buffer:
            # shutil.copyfileobjはメモリを大量に消費しないため安全
            shutil.copyfileobj(file.file, buffer)

        file_size = os.path.getsize(temp_file_path)
        if file_size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413, # Payload Too Large
                detail=f"File size {file_size / 1024 / 1024:.2f} MB exceeds the limit of {MAX_FILE_SIZE / 1024 / 1024} MB."
            )

        print(f"Received file: {file.filename}")
        print(f"Content-Type: {file.content_type}")
        print(f"File size: {file_size} bytes")

        # ここに今後、zip内の検証ロジックを追加していく

    finally:
        # FastAPIはUploadFileを自動で閉じるが、shutilで使ったファイルポインタは念のため閉じる
        file.file.close()
        # 一時ファイルを削除（今はまだ検証だけなので）
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)


    return {"filename": file.filename, "content_type": file.content_type, "size": file_size}