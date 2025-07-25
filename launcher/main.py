import sys, subprocess, os, zipfile
import requests
import sys, subprocess, os, zipfile
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

# --- バックグラウンドでダウンロードを行うワーカークラス ---
class DownloadWorker(QObject):
    """ファイルをダウンロードするためのワーカー"""
    progress = Signal(int)       # 進捗(%)を通知
    finished = Signal(str)       # 完了時に保存先パスを通知
    failed = Signal(str)         # 失敗時にエラーメッセージを通知

    def __init__(self, url, save_path):
        super().__init__()
        self.url = url
        self.save_path = save_path

    @Slot()
    def run(self):
        """ダウンロードを実行する"""
        try:
            response = requests.get(self.url, stream=True, timeout=60)
            response.raise_for_status()

            total_size = int(response.headers.get('content-length', 0))
            downloaded_size = 0
            
            # 保存先ディレクトリがなければ作成
            os.makedirs(os.path.dirname(self.save_path), exist_ok=True)

            with open(self.save_path, 'wb') as f:
                # データを少しずつ（チャンクごと）に書き込む
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    downloaded_size += len(chunk)
                    if total_size > 0:
                        # 進捗を計算してシグナルで通知
                        percentage = int((downloaded_size / total_size) * 100)
                        self.progress.emit(percentage)
            
            # 100%を確実に通知
            self.progress.emit(100)
            self.finished.emit(self.save_path)

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
        self.launch_button.clicked.connect(self._on_launch_button_clicked)
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
    def _on_launch_button_clicked(self):
        """「起動」ボタンが押されたときのメインロジック"""
        current_item = self.app_list_widget.currentItem()
        if not current_item:
            return

        app_data = current_item.data(Qt.UserRole)
        download_url = app_data.get('download_url')
        if not download_url:
            self.log("エラー: このアプリにはダウンロードURLがありません。")
            return
        
        # 将来的には、ここでダウンロード済みかチェックする
        # 今は毎回ダウンロードを実行する
        self._start_download(app_data)

    def _start_download(self, app_data):
        """ダウンロードスレッドを開始する"""
        download_url = app_data['download_url']
        app_name = app_data['name']
        
        # 一時的な保存先パスを決定
        # APPDATA環境変数を使い、安全な場所に保存する
        temp_dir = os.path.join(os.getenv('APPDATA'), 'Cat-box', 'temp')
        save_path = os.path.join(temp_dir, os.path.basename(download_url))

        self.log(f"'{app_name}'のダウンロードを開始します...")
        self.log(f"URL: {download_url}")
        self.log(f"保存先: {save_path}")

        # UIをロックして二重クリックなどを防ぐ
        self.launch_button.setEnabled(False)

        self.download_thread = QThread()
        self.download_worker = DownloadWorker(download_url, save_path)
        self.download_worker.moveToThread(self.download_thread)

        # シグナルとスロットを接続
        self.download_thread.started.connect(self.download_worker.run)
        self.download_worker.progress.connect(self.on_download_progress)
        self.download_worker.failed.connect(self.on_download_failed)
        self.download_worker.finished.connect(self.on_download_finished)

        # スレッドが終了したらクリーンアップ
        self.download_worker.finished.connect(self.download_thread.quit)
        self.download_worker.failed.connect(self.download_thread.quit)
        self.download_thread.finished.connect(self.download_worker.deleteLater)
        self.download_thread.finished.connect(self.download_thread.deleteLater)
        
        self.download_thread.start()

    # --- ダウンロード関連のスロット ---
    @Slot(int)
    def on_download_progress(self, percentage):
        """ダウンロード進捗の更新"""
        # ログが流れすぎないように、10%ごとか100%の時だけ表示
        if percentage % 10 == 0 or percentage == 100:
            self.log(f"ダウンロード中... {percentage}%")

    @Slot(str)
    def on_download_failed(self, error_message):
        """ダウンロード失敗時の処理"""
        self.log(f"ダウンロード失敗: {error_message}")
        self.launch_button.setEnabled(True) # ボタンを再度有効化

    @Slot(str)
    def on_download_finished(self, file_path):
        """ダウンロード完了時の処理"""
        self.log(f"ダウンロード完了: {file_path}")
        self.launch_button.setEnabled(True) # ボタンを再度有効化
        
        # 次のステップ: ここでzip展開と実行を行う
        self.log("次のステップで、このファイルを展開・実行します。")
def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()