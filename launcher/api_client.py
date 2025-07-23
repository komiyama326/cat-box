import requests
from typing import List, Dict, Any

# サーバーの公開URL。将来的には設定ファイルなどから読み込むのが望ましい。
# あなたのRender.comのAPIのURLに書き換えてください。
# 例: "https://cat-box-api.onrender.com"
BASE_URL = "https://cat-box-api.onrender.com" 

class ApiClient:
    """
    Cat-box APIと通信するためのクライアントクラス。
    """

    def __init__(self, base_url: str = BASE_URL):
        """
        ApiClientのインスタンスを初期化します。
        
        :param base_url: APIのベースURL
        """
        self.base_url = base_url
        self.session = requests.Session() # セッションを使って効率的に通信する

    def get_app_list(self) -> List[Dict[str, Any]]:
        """
        サーバーからアプリケーションのリストを取得します。

        :return: アプリケーション情報の辞書のリスト
        :raises requests.exceptions.RequestException: 通信に失敗した場合
        """
        try:
            # APIエンドポイントの完全なURLを構築
            url = f"{self.base_url}/api/v1/apps"
            
            # GETリクエストを送信
            response = self.session.get(url, timeout=60) # 10秒でタイムアウト
            
            # ステータスコードが200番台でない場合はエラーを発生させる
            response.raise_for_status()
            
            # レスポンスのJSONボディをPythonの辞書リストに変換して返す
            return response.json()

        except requests.exceptions.RequestException as e:
            # エラーログなどをここに追加することも可能
            print(f"APIへのリクエストに失敗しました: {e}")
            # エラーを呼び出し元に再度投げる
            raise

# このファイルが直接実行された場合に動作テストを行うためのコード
if __name__ == "__main__":
    print("ApiClientの動作テストを開始します...")
    try:
        client = ApiClient()
        apps = client.get_app_list()
        print("正常にアプリリストを取得しました。")
        print(f"取得したアプリの数: {len(apps)}")
        if apps:
            print("最初のアプリ情報:")
            # 見やすく表示
            import json
            print(json.dumps(apps[0], indent=2, ensure_ascii=False))
    except requests.exceptions.RequestException:
        print("テスト中にエラーが発生しました。サーバーが起動しているか、URLが正しいか確認してください。")