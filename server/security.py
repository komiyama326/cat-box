from passlib.context import CryptContext
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
import os

# JWTの設定
# このSECRET_KEYは非常に重要です。本来は.envファイルから読み込むべきです。
# openssl rand -hex 32 などで生成したランダムな文字列を使用します。
SECRET_KEY = os.getenv("SECRET_KEY", "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# パスワードのハッシュ化と検証を行うためのコンテキストを作成
# schemes=["bcrypt"]で、bcryptアルゴリズムを使用することを指定
# deprecated="auto"は、将来bcryptより安全なアルゴリズムが出た場合に自動で移行を促す設定
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """平文のパスワードとハッシュ化されたパスワードを比較する"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """平文のパスワードをハッシュ化する"""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """アクセストークンを生成する"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        # デフォルトの有効期限を設定
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> Optional[str]:
    """アクセストークンを検証し、ペイロード（sub=email）を返す"""
    try:
        # トークンをデコード
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        # ペイロードからemailを取得
        email: str = payload.get("sub")
        if email is None:
            # emailがなければ無効
            return None
        return email
    except JWTError:
        # デコードに失敗したら無効
        return None