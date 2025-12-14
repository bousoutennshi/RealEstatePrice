import os
import json
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

# 設定ファイルの読み込み
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config", "config.json")
DATA_BASE_DIR = os.path.join(os.path.dirname(__file__), "data")

def load_config():
    """設定ファイルを読み込む"""
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)

@app.get("/api/properties")
async def get_properties():
    """登録されているマンション一覧を取得する"""
    try:
        config = load_config()
        properties = []
        for prop in config['properties']:
            properties.append({
                'id': prop['id'],
                'name': prop['name'],
                'area': prop['area'],
                'layouts': prop['layouts']
            })
        return {'properties': properties}
    except Exception as e:
        return {'error': str(e), 'properties': []}

@app.get("/api/properties/{property_id}/listings")
async def get_property_listings(property_id: str):
    """特定のマンションの物件データを取得する
    
    Args:
        property_id: マンションID（例: "BranzTowerToyosu"）
    """
    # データファイルのパス
    filepath = os.path.join(DATA_BASE_DIR, property_id, "processed", "latest.json")
    
    if not os.path.exists(filepath):
        return {"error": f"No data found for property: {property_id}", "listings": [], "total_listings": 0}
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except Exception as e:
        return {"error": str(e), "listings": [], "total_listings": 0}

@app.get("/api/listings")
async def get_listings():
    """旧エンドポイント（後方互換性のため）- デフォルトマンションのデータを返す"""
    config = load_config()
    if config['properties']:
        default_property_id = config['properties'][0]['id']
        return await get_property_listings(default_property_id)
    return {"error": "No properties configured", "listings": [], "total_listings": 0}

# FileResponseのインポート
from starlette.responses import FileResponse

@app.get("/")
async def root():
    """ルートページ（マンション一覧）を返す"""
    index_path = os.path.join(os.path.dirname(__file__), "web", "index.html")
    return FileResponse(index_path)

@app.get("/{property_id}")
async def property_page(property_id: str):
    """マンション詳細ページを返す
    
    Args:
        property_id: マンションID（例: "BranzTowerToyosu"）
    """
    property_html_path = os.path.join(os.path.dirname(__file__), "web", "property.html")
    return FileResponse(property_html_path)

# 静的ファイルの配信（CSS, JS, 画像など）
if os.path.exists("web"):
    app.mount("/static", StaticFiles(directory="web"), name="static")

if __name__ == "__main__":
    import uvicorn
    import os
    # Railway環境ではPORT環境変数を使用、ローカルでは8000
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=True)
