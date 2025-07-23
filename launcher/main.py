import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QHBoxLayout, QVBoxLayout, QListWidget,
    QTextEdit, QLabel, QPushButton, QSplitter
)
from PySide6.QtCore import Qt

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Cat-box Launcher")
        self.resize(800, 600)

        # --- メインとなるウィジェットとレイアウトの作成 ---
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 水平方向に分割するスプリッター (左:アプリ一覧 | 右:詳細)
        top_splitter = QSplitter(Qt.Horizontal)
        
        # --- 左側のエリア (アプリ一覧) ---
        self.app_list_widget = QListWidget()
        # ダミーデータを追加して見た目を確認
        self.app_list_widget.addItems(["Super Shift App", "Simple Memo Pad", "Weather Cat"])
        top_splitter.addWidget(self.app_list_widget)

        # --- 右側のエリア (アプリ詳細) ---
        app_details_widget = QWidget()
        details_layout = QVBoxLayout(app_details_widget)
        details_layout.setAlignment(Qt.AlignTop) # ウィジェットを上寄せにする
        
        self.app_name_label = QLabel("アプリ名: (アプリを選択してください)")
        self.app_version_label = QLabel("バージョン: ")
        self.app_description_label = QLabel("説明: ")
        self.app_description_label.setWordWrap(True) # 長い説明は折り返す
        
        self.launch_button = QPushButton("起動")
        self.launch_button.setEnabled(False) # 最初は押せないようにしておく
        
        details_layout.addWidget(self.app_name_label)
        details_layout.addWidget(self.app_version_label)
        details_layout.addWidget(self.app_description_label)
        details_layout.addStretch() # スペーサーを入れてボタンを一番下に配置
        details_layout.addWidget(self.launch_button)

        top_splitter.addWidget(app_details_widget)
        
        # スプリッターの初期サイズを設定 (左側が200px, 右側が600px)
        top_splitter.setSizes([200, 600])

        # --- 下部のエリア (ログ) ---
        self.log_text_edit = QTextEdit()
        self.log_text_edit.setReadOnly(True) # ユーザーが編集できないようにする
        self.log_text_edit.setMaximumHeight(150) # 高さを制限
        self.log_text_edit.append("ランチャーを起動しました。")

        # --- 全体のレイアウト (垂直方向) ---
        main_layout = QVBoxLayout(central_widget)
        main_layout.addWidget(top_splitter)
        main_layout.addWidget(self.log_text_edit)


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()