from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, Request, Form, Response
from fastapi.responses import HTMLResponse, RedirectResponse # Response を HTMLResponse に変更しても良い
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm 
from datetime import timedelta 
from typing import List, Optional
import shutil
import os
import zipfile # zipファイル操作のため
import subprocess # 将来のウイルススキャン連携用
import hashlib # ハッシュ値計算のため

# SQLAlchemyのセッション型をインポート
from sqlalchemy.orm import Session

# 作成したモジュールをインポート
from . import crud, models, security
from .database import SessionLocal, engine

# 同じディレクトリにあるmodels.pyからAppモデルをインポート
#from .models import App

# サーバー起動時にテーブルを自動作成する（Alembicを使うので通常は不要だが、開発初期には便利）
# models.Base.metadata.create_all(bind=engine)

# --- 【認証スキームの定義 ---
# この時点ではトークンURLを指定するだけ。実際の検証ロジックは get_current_user で実装。
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/token")

# --- 定数を定義 ---
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB
MAX_FILES_IN_ZIP = 100 # zip内のファイル数上限
ALLOWED_EXTENSIONS = {'.py', '.txt', '.md', '.json', '.ui', '.qss', '.png', '.jpg', '.jpeg', '.gif'} # 許可する拡張子
UPLOAD_DIR = "uploads"

# ダミーのブラックリストDB (本来はデータベースやファイルで管理)
KNOWN_MALWARE_HASHES = {
    "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855" # 空ファイルのSHA-256ハッシュ (テスト用)
}

# サーバー起動時にアップロード用ディレクトリを作成
os.makedirs(UPLOAD_DIR, exist_ok=True)
# --- 定数ここまで ---

# FastAPIアプリケーションのインスタンスを作成
app = FastAPI(title="Cat-box API")

# テンプレート設定 ---
templates = Jinja2Templates(directory="server/templates")

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

# --- DBセッション管理 ---
from .database import SessionLocal

def get_db():
    """
    APIリフクエストのライフサイクル中にデータベースセッションを提供する依存性。
    リクエストの開始時にセッションを生成し、
    リクエストの終了後（成功・失敗問わず）にセッションを閉じる。
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
# --- DBセッション管理ここまで ---

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> Optional[models.User]:
    """
    トークンを検証し、現在のユーザーモデルを返す依存性。
    認証できない場合はNoneを返す。
    """
    # この実装では、Swagger UIのAuthorizeボタンからはうまく動作しないが、
    # Cookieからのトークン取得を優先するため、まずはこの形で実装する。
    # ヘッダーから 'Bearer ' というプレフィックスを削除
    if token.startswith("Bearer "):
        token = token.split("Bearer ")[1]

    email = security.verify_token(token)
    if email is None:
        return None # 認証失敗
    
    user = crud.get_user_by_email(db, email=email)
    return user

async def get_current_user_from_cookie(request: Request, db: Session = Depends(get_db)) -> Optional[models.User]:
    """
    Cookieからアクセストークンを読み取り、現在のユーザーを返す依存性。
    認証できない場合はNoneを返す。
    """
    token = request.cookies.get("access_token")
    if not token:
        return None

    # ヘッダーから 'Bearer ' というプレフィックスを削除
    if token.startswith("Bearer "):
        token = token.split("Bearer ")[1]

    email = security.verify_token(token)
    if email is None:
        return None

    user = crud.get_user_by_email(db, email=email)
    return user

#  Webページ表示用エンドポイント ---

@app.get("/", response_class=HTMLResponse)
def read_root(request: Request, db: Session = Depends(get_db)):
    """
    トップページ (アプリ一覧) を表示する。
    """
    # データベースからアプリ一覧を取得
    apps = crud.get_apps(db)
    
    # テンプレートに渡すデータを準備
    context = {
        "request": request,
        "apps": apps
    }
    # テンプレートを使ってHTMLを生成して返す
    return templates.TemplateResponse("index.html", context)

@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    """ログインページを表示する"""
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login", response_class=HTMLResponse)
async def handle_login(request: Request, db: Session = Depends(get_db), username: str = Form(), password: str = Form()):
    """ログインフォームからの送信を処理する"""
    try:
        # トークン発行APIを呼び出すのと同じロジック
        user = crud.get_user_by_email(db, email=username)
        if not user or not security.verify_password(password, user.hashed_password):
            raise Exception("メールアドレスまたはパスワードが間違っています。")

        # ログイン成功
        access_token_expires = timedelta(minutes=security.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = security.create_access_token(
            data={"sub": user.email}, expires_delta=access_token_expires
        )
        
        # トークンをCookieにセットしてトップページにリダイレクト
        response = templates.TemplateResponse("redirect.html", {"request": request, "message": "ログインに成功しました！", "redirect_url": "/"})
        response.set_cookie(key="access_token", value=f"Bearer {access_token}", httponly=True)
        return response

    except Exception as e:
        # ログイン失敗
        return templates.TemplateResponse("login.html", {"request": request, "error": str(e)})

# 新しく追加するCRUD関数をインポート
from . import crud, models, security

@app.get("/mypage", response_class=HTMLResponse)
async def mypage(request: Request, current_user: Optional[models.User] = Depends(get_current_user_from_cookie)):
    """
    マイページを表示する。
    ログインしていない場合はログインページにリダイレクトする。
    """
    if current_user is None:
        # ログインしていない場合、ログインページへリダイレクト
        return RedirectResponse(url="/login", status_code=302)

    # ログインしている場合、ユーザー情報をテンプレートに渡して表示
    context = {
        "request": request,
        "current_user": current_user
    }
    return templates.TemplateResponse("mypage.html", context)

@app.post("/logout")
async def logout(response: Response):
    """
    ログアウト処理。Cookieを削除してトップページにリダイレクトする。
    """
    response = RedirectResponse(url="/", status_code=302)
    response.delete_cookie(key="access_token")
    return response

@app.get("/api/v1/apps/", response_model=List[models.AppSchema])
def read_apps(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    登録されているアプリケーションのリストをデータベースから取得します。
    """
    apps = crud.get_apps(db, skip=skip, limit=limit)
    return apps

# 既存の @app.post("/api/v1/users/", ... ) の前にこのエンドポイントを置く

# --- ヘルパー関数 ---
def run_virus_scan(file_path: str) -> bool:
    """
    指定されたファイルに対してウイルススキャンを実行する（という想定のダミー関数）。
    将来的にはここでClamAVなどのスキャンコマンドを呼び出す。
    
    :param file_path: スキャン対象のファイルパス
    :return: 安全であればTrue, ウイルスが検出されればFalseを返す
    """
    print(f"--- Running dummy virus scan on {file_path} ---")
    # 【本番実装の例】
    # try:
    #     result = subprocess.run(
    #         ['clamscan', '--stdout', '--no-summary', file_path],
    #         capture_output=True, text=True, check=True
    #     )
    #     # "OK" という文字列が含まれていれば安全とみなす
    #     if "OK" in result.stdout:
    #         print("--- Scan result: OK ---")
    #         return True
    #     else:
    #         print(f"--- Scan result: VIRUS DETECTED --- \n{result.stdout}")
    #         return False
    # except FileNotFoundError:
    #     print("--- WARNING: clamscan command not found. Skipping virus scan. ---")
    #     return True # 開発環境ではスキャンをスキップ
    # except subprocess.CalledProcessError as e:
    #     # clamscanはウイルスを検知すると終了コードが1になるため、ここで検知する
    #     if e.returncode == 1:
    #         print(f"--- Scan result: VIRUS DETECTED --- \n{e.stdout}")
    #         return False
    #     else:
    #         print(f"--- ERROR: Virus scan failed with code {e.returncode} --- \n{e.stderr}")
    #         # スキャン自体が失敗した場合は、安全のためNGとするか、管理者に通知する
    #         return False
    
    # 【現在のダミー実装】
    # 常に安全であると仮定してTrueを返す
    print("--- Scan result: OK (Dummy) ---")
    return True

# --- ヘルパー関数に追記 ---
def check_file_hash(file_path: str) -> bool:
    """
    ファイルのSHA-256ハッシュを計算し、ブラックリストに存在しないか確認する。
    
    :param file_path: チェック対象のファイルパス
    :return: ブラックリストに含まれていなければTrue, 含まれていればFalse
    """
    print(f"--- Checking file hash for {file_path} ---")
    sha256_hash = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            # メモリを効率的に使うため、ファイルをチャンクで読み込む
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        
        file_hex_hash = sha256_hash.hexdigest()
        print(f"--- File hash (SHA-256): {file_hex_hash} ---")

        if file_hex_hash in KNOWN_MALWARE_HASHES:
            print("--- HASH MATCH: Known malicious file detected! ---")
            return False
        else:
            print("--- HASH OK: File is not on the blacklist. ---")
            return True

    except IOError as e:
        print(f"--- ERROR: Could not read file for hashing: {e} ---")
        return False # ファイルが読めないなど問題があれば安全側に倒す

@app.post("/api/v1/apps/upload")
async def upload_app(file: UploadFile = File(...)):
    """
    アプリケーションのzipファイルをアップロードします。
    ファイルサイズ、コンテントタイプ、zip内部の検証を追加。
    """
    if file.content_type not in ["application/zip", "application/x-zip-compressed"]:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type: {file.content_type}. Only .zip files are allowed."
        )

    temp_file_path = os.path.join(UPLOAD_DIR, file.filename)
    try:
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        file_size = os.path.getsize(temp_file_path)
        if file_size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"File size {file_size / 1024 / 1024:.2f} MB exceeds the limit of {MAX_FILE_SIZE / 1024 / 1024} MB."
            )

        # --- ここからzip内部の検証ロジック ---
        print(f"Inspecting zip file: {temp_file_path}")
        try:
            with zipfile.ZipFile(temp_file_path, 'r') as zip_ref:
                # 1. ファイル数の検証
                file_list = zip_ref.infolist()
                if len(file_list) > MAX_FILES_IN_ZIP:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Too many files in zip. Exceeds the limit of {MAX_FILES_IN_ZIP} files."
                    )
                
                # 2. 拡張子の検証
                for file_info in file_list:
                    # ディレクトリはスキップ
                    if file_info.is_dir():
                        continue
                    
                    # ファイル名から拡張子を取得
                    _, extension = os.path.splitext(file_info.filename)
                    if not extension or extension.lower() not in ALLOWED_EXTENSIONS:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Disallowed file type found in zip: {file_info.filename}"
                        )
                        
                print("Zip file inspection passed.")

        except zipfile.BadZipFile:
            raise HTTPException(status_code=400, detail="Invalid zip file.")
        # --- zip内部の検証ロジックここまで ---

        # --- ここからウイルススキャン ---
        if not run_virus_scan(temp_file_path):
            raise HTTPException(
                status_code=400,
                detail="A virus was detected in the uploaded file."
            )
        # --- ウイルススキャンここまで ---

        # --- ここからハッシュ値チェック ---
        if not check_file_hash(temp_file_path):
            raise HTTPException(
                status_code=400,
                detail="The uploaded file is on the blacklist."
            )
        # --- ハッシュ値チェックここまで ---

        print(f"Received file: {file.filename}")
        print(f"Content-Type: {file.content_type}")
        print(f"File size: {file_size} bytes")
        
        # 検証が終わったら、本来はここでファイルを永続的なストレージ(S3など)に移動する
        # 今はまだ何もしない

    finally:
        file.file.close()
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

    return {"filename": file.filename, "content_type": file.content_type, "size": file_size, "inspection_status": "passed", "virus_scan_status": "passed", "hash_check_status": "passed"}

# (upload_app エンドポイントの下に追記)

@app.post("/api/v1/users/", response_model=models.UserSchema)
def create_user(user: models.UserCreate, db: Session = Depends(get_db)):
    """
    新しいユーザーを作成（ユーザー登録）
    """
    # 既に同じメールアドレスのユーザーがいないかチェック
    db_user = crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    # 既に同じユーザー名のユーザーがいないかチェック
    db_user_by_username = crud.get_user_by_username(db, username=user.username)
    if db_user_by_username:
        raise HTTPException(status_code=400, detail="Username already registered")

    # 新しいユーザーをデータベースに作成
    return crud.create_user(db=db, user=user)    

@app.post("/api/v1/token")
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """
    ユーザー名とパスワードで認証し、アクセストークンを発行する。
    """
    # ユーザーをメールアドレス（ユーザー名として使用）で検索
    user = crud.get_user_by_email(db, email=form_data.username)
    
    # ユーザーが存在しない、またはパスワードが間違っている場合
    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=401, # Unauthorized
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # アクセストークンを生成
    access_token_expires = timedelta(minutes=security.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    
    # トークンを返す
    return {"access_token": access_token, "token_type": "bearer"}