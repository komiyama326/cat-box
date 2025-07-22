from pydantic import BaseModel, HttpUrl
from typing import Optional

class App(BaseModel):
    """
    アプリケーション情報を表現するデータモデル。
    APIレスポンスや内部処理でこのモデルを使用する。
    """
    id: int
    name: str
    version: str
    description: Optional[str] = None
    icon_url: Optional[HttpUrl] = None
    download_url: HttpUrl