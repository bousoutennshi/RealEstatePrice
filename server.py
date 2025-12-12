import os
import json
import glob
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any

app = FastAPI(title="Real Estate Scraper Viewer")

# CORS設定（開発用）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# データディレクトリの設定
DATA_DIR = os.path.join(os.path.dirname(__file__), "data", "processed")

@app.get("/api/listings")
async def get_listings():
    """最新の物件データを取得する"""
    # 最新の統合データファイルを探す
    files = glob.glob(os.path.join(DATA_DIR, "merged_*.json"))
    if not files:
        return {"error": "No data found", "listings": [], "total_listings": 0}
    
    # タイムスタンプ順にソートして最新を取得
    latest_file = max(files, key=os.path.getctime)
    
    try:
        with open(latest_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except Exception as e:
        return {"error": str(e), "listings": [], "total_listings": 0}

@app.get("/api/history")
async def get_history():
    """過去のデータ収集履歴を取得する（未実装）"""
    return {"message": "Not implemented yet"}

# 静的ファイルの配信（フロントエンド）
# webディレクトリが存在する場合のみマウント
if os.path.exists("web"):
    app.mount("/", StaticFiles(directory="web", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    # リロード機能を有効にしてサーバー起動
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
