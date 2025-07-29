from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

# .envファイルから環境変数を読み込む
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# データベースエンジンを作成
# 'check_same_thread'はSQLiteの場合のみ必要。PostgreSQLでは不要。
engine = create_engine(DATABASE_URL)

# データベースセッションを作成するためのクラス
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# モデルクラス（テーブル定義）が継承するためのベースクラス
Base = declarative_base()