import sys, subprocess, os, zipfile, venv
import requests
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
    @Slot()
    def _on_launch_button_clicked(self):
        """「起動」ボタンが押されたときのメインロジック"""
        current_item = self.app_list_widget.currentItem()
        if not current_item:
            return

        app_data = current_item.data(Qt.UserRole)
        app_name = app_data['name']
        app_version = app_data['version']
        
        # 実行すべきアプリのパスを決定
        base_dir = os.path.join(os.getenv('APPDATA'), 'Cat-box', 'apps')
        app_dir = os.path.join(base_dir, app_name, app_version)
        entry_point_relative = os.path.join('dummy_app', 'run.py') # zipの中の構造に依存
        executable_path = os.path.join(app_dir, entry_point_relative)

        # 既に展開済みのアプリが存在するかチェック
        if os.path.exists(executable_path):
            self.log(f"'{app_name}' は既に存在します。直接起動します。")
            try:
                # 存在するアプリを直接実行
                creationflags = 0
                if sys.platform == "win32":
                    creationflags = subprocess.CREATE_NEW_CONSOLE
                subprocess.Popen([sys.executable, executable_path, app_name], creationflags=creationflags)
            except Exception as e:
                self.log(f"既存アプリの起動中にエラー: {e}")
        else:
            # 存在しない場合はダウンロードを開始
            self.log(f"'{app_name}' が見つかりません。ダウンロードを開始します。")
            download_url = app_data.get('download_url')
            if not download_url:
                self.log("エラー: このアプリにはダウンロードURLがありません。")
                return
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
        
        current_item = self.app_list_widget.currentItem()
        if not current_item:
            self.log("エラー: アプリ情報が見つかりません。")
            self.launch_button.setEnabled(True)
            return

        app_data = current_item.data(Qt.UserRole)
        
        try:
            # zipファイルを展開し、実行する
            self._unzip_and_execute(file_path, app_data)
        except Exception as e:
            self.log(f"アプリの展開または実行中にエラー: {e}")
        finally:
            # 成功・失敗にかかわらずボタンを再度有効化
            self.launch_button.setEnabled(True)
        
        # 次のステップ: ここでzip展開と実行を行う
        self.log("次のステップで、このファイルを展開・実行します。")

    # MainWindowクラスの中に追加
    # 古い _unzip_and_execute をこれで置き換える
    def _unzip_and_execute(self, zip_path, app_data):
        """zipファイルを展開し、専用の仮想環境を構築してアプリを実行する"""
        app_name = app_data['name']
        app_version = app_data['version']

        # 1. アプリケーションデータディレクトリを決定
        base_dir = os.path.join(os.getenv('APPDATA'), 'Cat-box', 'apps')
        app_dir = os.path.join(base_dir, app_name, app_version)
        
        self.log(f"'{app_name}' を '{app_dir}' に展開します...")
        os.makedirs(app_dir, exist_ok=True)

        # 2. Zipファイルを展開
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(app_dir)
        self.log("展開が完了しました。")

        # 3. 専用の仮想環境(venv)を構築 (ステップ3-5の核心)
        venv_dir = os.path.join(app_dir, '.venv')
        self.log(f"専用の仮想環境を '{venv_dir}' に作成します...")
        try:
            # venv.create(venv_dir, with_pip=True)
            # 上記はブロッキングなので、subprocessで非同期に実行する方がUIに優しい
            # ここではシンプルさのためにブロッキングで実装するが、将来的にはこれもスレッド化の候補
            venv.create(venv_dir, with_pip=True)
            self.log("仮想環境の作成が完了しました。")
        except Exception as e:
            self.log(f"仮想環境の作成に失敗しました: {e}")
            raise

        # 4. 依存ライブラリをインストール
        requirements_path = os.path.join(app_dir, 'dummy_app', 'requirements.txt') # zip内の構造に依存
        
        # OSによってpipとpythonのパスが異なるため、パスを正しく解決
        if sys.platform == "win32":
            pip_executable = os.path.join(venv_dir, 'Scripts', 'pip.exe')
            python_executable = os.path.join(venv_dir, 'Scripts', 'python.exe')
        else: # macOS, Linux
            pip_executable = os.path.join(venv_dir, 'bin', 'pip')
            python_executable = os.path.join(venv_dir, 'bin', 'python')

        if os.path.exists(requirements_path):
            self.log(f"'requirements.txt' に基づいてライブラリをインストールします...")
            try:
                # subprocess.runで同期的にコマンドを実行し、完了を待つ
                result = subprocess.run(
                    [pip_executable, 'install', '-r', requirements_path],
                    capture_output=True, text=True, check=True
                )
                self.log("ライブラリのインストールが完了しました。")
                # 詳細なログが必要な場合は以下を有効化
                # self.log(f"pip output:\n{result.stdout}")
            except subprocess.CalledProcessError as e:
                self.log(f"ライブラリのインストールに失敗しました。")
                self.log(f"pip error:\n{e.stderr}")
                raise
        else:
            self.log("'requirements.txt' が見つかりませんでした。スキップします。")

        # 5. アプリの実行
        entry_point_relative = os.path.join('dummy_app', 'run.py')
        executable_path = os.path.join(app_dir, entry_point_relative)
        self.log(f"'{executable_path}' を実行します...")

        if not os.path.exists(executable_path):
            self.log(f"エラー: 実行ファイルが見つかりません: {executable_path}")
            return
        
        try:
            creationflags = 0
            if sys.platform == "win32":
                creationflags = subprocess.CREATE_NEW_CONSOLE
            
            # 【重要】作成した仮想環境のPythonを使ってスクリプトを実行する
            subprocess.Popen([python_executable, executable_path, app_name], creationflags=creationflags)
            self.log(f"'{app_name}' のプロセスを起動しました。")
        except Exception as e:
            self.log(f"アプリの起動中に予期せぬエラーが発生しました: {e}")
            raise
        """zipファイルを展開し、アプリを実行する"""
        app_name = app_data['name']
        app_version = app_data['version']

        # 1. アプリケーションデータディレクトリを決定 (ステップ3-5)
        # APPDATA/Cat-box/apps/アプリ名/バージョン/
        base_dir = os.path.join(os.getenv('APPDATA'), 'Cat-box', 'apps')
        app_dir = os.path.join(base_dir, app_name, app_version)
        
        self.log(f"'{app_name}' を '{app_dir}' に展開します...")
        os.makedirs(app_dir, exist_ok=True)

        # 2. Zipファイルを展開 (ステップ3-6)
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(app_dir)
        
        self.log("展開が完了しました。")

        # 3. 実行ロジック (ステップ3-6)
        # 【重要】zipファイル内のどのファイルを実行するかを決める必要がある
        # 今回は、zipを展開した直下にある 'run.py' を実行するルールとする
        # dummy_app.zipを展開すると、'dummy_app'フォルダができるので、その中の'run.py'を指定
        entry_point_relative = os.path.join('dummy_app', 'run.py')
        executable_path = os.path.join(app_dir, entry_point_relative)

        self.log(f"実行ファイルパス: {executable_path}")

        if not os.path.exists(executable_path):
            self.log(f"エラー: 実行ファイルが見つかりません: {executable_path}")
            return

        try:
            self.log(f"'{app_name}' を起動します...")
            
            creationflags = 0
            if sys.platform == "win32":
                creationflags = subprocess.CREATE_NEW_CONSOLE

            # 展開されたアプリを実行する
            subprocess.Popen([sys.executable, executable_path, app_name], creationflags=creationflags)
            
            self.log(f"'{app_name}' のプロセスを起動しました。")
        except Exception as e:
            self.log(f"アプリの起動中に予期せぬエラーが発生しました: {e}")
            raise # エラーを呼び出し元に伝播させる
def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()