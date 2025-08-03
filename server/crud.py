from sqlalchemy.orm import Session

# 同じディレクトリの models と security をインポート
from . import models, security

def get_user_by_email(db: Session, email: str):
    """メールアドレスでユーザーを検索する"""
    return db.query(models.User).filter(models.User.email == email).first()

def get_user_by_username(db: Session, username: str):
    """ユーザー名でユーザーを検索する"""
    return db.query(models.User).filter(models.User.username == username).first()

def get_apps(db: Session, skip: int = 0, limit: int = 100):
    """
    アプリケーションのリストをデータベースから取得する
    """
    return db.query(models.App).offset(skip).limit(limit).all()

def create_user(db: Session, user: models.UserCreate):
    """新しいユーザーを作成する"""
    hashed_password = security.get_password_hash(user.password)
    # Pydanticモデルからパスワードを除外し、ハッシュ化済みパスワードを追加してDBモデルを作成
    db_user = models.User(
        email=user.email,
        username=user.username,
        hashed_password=hashed_password
    )
    db.add(db_user) # 新しいユーザーオブジェクトをセッションに追加
    db.commit()      # データベースにコミット（書き込み）
    db.refresh(db_user) # DBから最新の状態（自動採番されたIDなど）を再取得
    return db_user