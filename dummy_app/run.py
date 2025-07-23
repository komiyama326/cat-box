# dummy_app/run.py
import time
import sys

# 引数があればそれを表示する
app_name = sys.argv[1] if len(sys.argv) > 1 else "Dummy App"

print(f"'{app_name}' を起動しました！")
print("このウィンドウは10秒後に自動で閉じます...")
time.sleep(10)