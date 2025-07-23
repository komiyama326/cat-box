import sys, subprocess
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QHBoxLayout, QVBoxLayout, QListWidget, QListWidgetItem,
    QTextEdit, QLabel, QPushButton, QSplitter
)
from PySide6.QtCore import Qt, QThread, QObject, Signal, Slot

# 作成したAPIクライアントをインポート
from api_client import ApiClient

# --- バックグラウンドでAPI通信を行うワーカークラス ---
class ApiWorker(QObject):
    """API通信を別スレッドで実行するためのワーカー"""
    # シグナルの定義: 成功時にアプリリスト(list)、失敗時にエラーメッセージ(str)を渡す
    succeeded = Signal(list)
    failed = Signal(str)

    def __init__(self, api_client):
        super().__init__()
        self.api_client = api_client

    @Slot()
    def fetch_app_list(self):
        """アプリリストを取得するタスク"""
        try:
            apps = self.api_client.get_app_list()
            self.succeeded.emit(apps)
        except Exception as e:
            self.failed.emit(str(e))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Cat-box Launcher")
        self.resize(800, 600)

        self.apps_data = [] # APIから取得したアプリの全データを保持するリスト

        # --- UIウィジェットのセットアップ (ステップ2-3とほぼ同じ) ---
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        top_splitter = QSplitter(Qt.Horizontal)
        
        # 左側: アプリ一覧
        self.app_list_widget = QListWidget()
        self.app_list_widget.currentItemChanged.connect(self._on_app_selection_changed) # アイテム選択時の処理を接続
        top_splitter.addWidget(self.app_list_widget)

        # 右側: アプリ詳細
        app_details_widget = QWidget()
        details_layout = QVBoxLayout(app_details_widget)
        details_layout.setAlignment(Qt.AlignTop)
        self.app_name_label = QLabel("アプリ名: (アプリを選択してください)")
        self.app_version_label = QLabel("バージョン: ")
        self.app_description_label = QLabel("説明: ")
        self.app_description_label.setWordWrap(True)
        self.launch_button = QPushButton("起動")
        self.launch_button.setEnabled(False)
        self.launch_button.clicked.connect(self._launch_app)
        details_layout.addWidget(self.app_name_label)
        details_layout.addWidget(self.app_version_label)
        details_layout.addWidget(self.app_description_label)
        details_layout.addStretch()
        details_layout.addWidget(self.launch_button)
        top_splitter.addWidget(app_details_widget)
        top_splitter.setSizes([200, 600])

        # 下部: ログ
        self.log_text_edit = QTextEdit()
        self.log_text_edit.setReadOnly(True)
        self.log_text_edit.setMaximumHeight(150)

        # 全体のレイアウト
        main_layout = QVBoxLayout(central_widget)
        main_layout.addWidget(top_splitter)
        main_layout.addWidget(self.log_text_edit)

        # --- 非同期処理のセットアップ ---
        self.setup_api_worker()
        self.log("ランチャーを起動しました。")
        self.fetch_apps() # ランチャー起動時にアプリ取得を開始

    def setup_api_worker(self):
        """ワーカースレッドとシグナル・スロットを設定する"""
        self.thread = QThread()
        api_client = ApiClient()
        self.worker = ApiWorker(api_client)
        self.worker.moveToThread(self.thread)

        # シグナルとスロットを接続
        self.worker.succeeded.connect(self._on_fetch_success)
        self.worker.failed.connect(self._on_fetch_failure)
        self.thread.started.connect(self.worker.fetch_app_list)
        self.worker.succeeded.connect(self.thread.quit)
        self.worker.failed.connect(self.thread.quit)
        
        # メモリリークを防ぐため、スレッド終了後にオブジェクトを削除
        self.thread.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        
    def fetch_apps(self):
        """アプリリストの取得を開始する"""
        self.app_list_widget.clear()
        self.log("アプリリストを取得中...")
        self.thread.start()

    def log(self, message):
        """ログエリアにメッセージを追記する"""
        self.log_text_edit.append(message)

    # --- スロット (シグナルによって呼び出されるメソッド) ---
    @Slot(list)
    def _on_fetch_success(self, apps):
        """アプリ取得成功時の処理"""
        self.log(f"正常にアプリリストを取得しました。({len(apps)}件)")
        self.apps_data = apps
        self.app_list_widget.clear()
        for app_data in self.apps_data:
            # QListWidgetItemに表示名だけでなく、辞書データ全体を関連付ける
            item = QListWidgetItem(app_data['name'])
            item.setData(Qt.UserRole, app_data) # UserRoleにデータを保存
            self.app_list_widget.addItem(item)

    @Slot(str)
    def _on_fetch_failure(self, error_message):
        """アプリ取得失敗時の処理"""
        self.log(f"エラー: {error_message}")

    @Slot(QListWidgetItem)
    def _on_app_selection_changed(self, current_item):
        """アプリ一覧で選択項目が変わった時の処理"""
        if not current_item:
            return

        # アイテムに保存しておいたアプリデータを取得
        app_data = current_item.data(Qt.UserRole)
        self.app_name_label.setText(f"アプリ名: {app_data.get('name', 'N/A')}")
        self.app_version_label.setText(f"バージョン: {app_data.get('version', 'N/A')}")
        self.app_description_label.setText(f"説明: {app_data.get('description', 'N/A')}")
        self.launch_button.setEnabled(True)
        
    @Slot()
    def _launch_app(self):
        """選択されているアプリを起動する"""
        current_item = self.app_list_widget.currentItem()
        if not current_item:
            self.log("エラー: 起動するアプリが選択されていません。")
            return

        app_data = current_item.data(Qt.UserRole)
        app_name = app_data.get('name', 'Unknown App')
        
        # --- ここで実際にプロセスを起動する ---
        # 【重要】将来的には、ダウンロード＆展開したアプリのパスを指定する
        # 今回は、テスト用にダミーのPythonスクリプトを起動する
        # sys.executable は、現在ランチャーを実行しているPythonのパス
        
        # 起動するダミーアプリのパス
        # 注意: このパスはプロジェクトのルートから見た相対パスです。
        # 実行する場所によっては調整が必要になる場合があります。
        dummy_app_path = "dummy_app/run.py" 
        
        try:
            self.log(f"'{app_name}' を起動しようとしています...")
            
            # subprocess.Popenで非同期にプロセスを起動
            # 新しいコンソールウィンドウで実行するために creationflags を設定 (Windowsの場合)
            # Mac/Linuxの場合は、このフラグは不要で、別の方法が必要になることがあります。
            creationflags = 0
            if sys.platform == "win32":
                creationflags = subprocess.CREATE_NEW_CONSOLE

            subprocess.Popen([sys.executable, dummy_app_path, app_name], creationflags=creationflags)
            
            self.log(f"'{app_name}' のプロセスを起動しました。")
        except FileNotFoundError:
            self.log(f"エラー: 実行ファイルが見つかりません: {dummy_app_path}")
        except Exception as e:
            self.log(f"アプリの起動中に予期せぬエラーが発生しました: {e}")            

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()