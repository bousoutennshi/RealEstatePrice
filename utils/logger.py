"""ロガーユーティリティ"""
import logging
import os
from datetime import datetime


def setup_logger(name: str, log_file: str = None, level=logging.INFO):
    """
    ロガーをセットアップする
    
    Args:
        name: ロガー名
        log_file: ログファイルのパス（Noneの場合はコンソールのみ）
        level: ログレベル
    
    Returns:
        logging.Logger: 設定されたロガー
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # フォーマッターの設定
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # コンソールハンドラー
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # ファイルハンドラー（オプション）
    if log_file:
        # ログディレクトリの作成
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def get_logger(name: str):
    """
    既存のロガーを取得する
    
    Args:
        name: ロガー名
    
    Returns:
        logging.Logger: ロガー
    """
    return logging.getLogger(name)
