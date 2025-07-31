# SQLAlchemy関連のインポート
from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Text, Enum
from sqlalchemy.orm import relationship

# データベース設定をインポート
from .database import Base

# Pydanticモデル関連のインポート
from pydantic import BaseModel, HttpUrl
from typing import Optional, List

# ======== SQLAlchemy Models (データベースのテーブル定義) ========

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    
    plan = Column(Enum('basic', 'premium', name='plan_enum'), default='basic', nullable=False)
    points = Column(Integer, default=0, nullable=False)

    # UserとAppのリレーションシップを定義
    apps = relationship("App", back_populates="owner")


class App(Base):
    __tablename__ = "apps"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    version = Column(String, nullable=False)
    description = Column(Text)
    
    download_url = Column(String, nullable=False)
    icon_url = Column(String)
    
    owner_id = Column(Integer, ForeignKey("users.id"))

    # AppとUserのリレーションシップを定義
    owner = relationship("User", back_populates="apps")

    app_type = Column(Enum('basic', 'premium', name='app_type_enum'), default='basic', nullable=False)
    status = Column(Enum('public', 'private', 'reported', name='status_enum'), default='public', nullable=False)


# ======== Pydantic Schemas (APIのデータ形式定義) ========
# これらはAPIの入出力に使われ、パスワードなどの公開すべきでない情報を含まないようにする

class AppBase(BaseModel):
    name: str
    version: str
    description: Optional[str] = None
    icon_url: Optional[HttpUrl] = None

class AppCreate(AppBase):
    pass

class AppSchema(AppBase):
    id: int
    owner_id: int
    download_url: HttpUrl

    class Config:
        orm_mode = True # SQLAlchemyモデルをPydanticモデルに変換できるようにする

class UserBase(BaseModel):
    email: str
    username: str

class UserCreate(UserBase):
    password: str

class UserSchema(UserBase):
    id: int
    is_active: bool
    apps: List[AppSchema] = []

    class Config:
        orm_mode = True