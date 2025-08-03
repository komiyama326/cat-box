from passlib.context import CryptContext

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