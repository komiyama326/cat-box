from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QLabel, QMessageBox, QTabWidget, QWidget
)
from PySide6.QtCore import Signal, Slot

# api_client.py をインポート
from api_client import ApiClient

class AuthDialog(QDialog):
    """ユーザー登録とログインのためのダイアログ"""

    # 認証成功シグナル（将来のログイン機能のために用意）
    # authenticated = Signal(str) # トークンを渡す想定

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("アカウント")
        self.setModal(True) # 他のウィンドウを操作できなくする

        self.api_client = ApiClient()

        # --- UI要素の作成 ---
        # ユーザー名入力
        self.username_label = QLabel("ユーザー名:")
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("半角英数")

        # メールアドレス入力
        self.email_label = QLabel("メールアドレス:")
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("user@example.com")
        
        # パスワード入力
        self.password_label = QLabel("パスワード:")
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password) # パスワードを隠す

        # 登録ボタン
        self.register_button = QPushButton("登録")

        # --- レイアウト設定 ---
        layout = QVBoxLayout(self)
        layout.addWidget(self.username_label)
        layout.addWidget(self.username_input)
        layout.addWidget(self.email_label)
        layout.addWidget(self.email_input)
        layout.addWidget(self.password_label)
        layout.addWidget(self.password_input)
        layout.addWidget(self.register_button)

        # --- シグナルとスロットの接続 ---
        self.register_button.clicked.connect(self.on_register_clicked)


    @Slot()
    def on_register_clicked(self):
        """「登録」ボタンがクリックされたときの処理"""
        username = self.username_input.text()
        email = self.email_input.text()
        password = self.password_input.text()

        # 簡単な入力チェック
        if not all([username, email, password]):
            QMessageBox.warning(self, "入力エラー", "すべての項目を入力してください。")
            return

        try:
            # APIクライアントを呼び出してユーザー登録
            user_data = self.api_client.create_user(username, email, password)
            QMessageBox.information(self, "成功", f"ユーザー '{user_data['username']}' の登録が完了しました。")
            self.accept() # ダイアログを閉じる
        except Exception as e:
            # APIクライアントから送出された例外をキャッチして表示
            QMessageBox.critical(self, "登録エラー", str(e))