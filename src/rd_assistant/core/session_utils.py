from datetime import datetime
from typing import Any, Dict
import json
import logging
from pathlib import Path

class SessionUtils:
    """セッションデータの処理とログ出力を管理するユーティリティクラス"""
    
    def __init__(self, log_dir: str = "logs"):
        self._setup_logging(log_dir)
        self.logger = logging.getLogger('session_manager')

    def _setup_logging(self, log_dir: str):
        """ログ出力の設定"""
        log_dir = Path(log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        
        log_file = log_dir / 'session_manager.log'

        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)

        logger = logging.getLogger('session_manager')
        logger.setLevel(logging.INFO)
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    def serialize_datetime(self, obj: Any) -> Any:
        """オブジェクトのシリアライズ処理"""
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f'Type {type(obj)} is not JSON serializable')

    def deserialize_datetime(self, data: Dict) -> Dict:
        """JSON データ内の日時文字列を datetime オブジェクトに変換"""
        for key, value in data.items():
            if isinstance(value, str):
                try:
                    # ISO形式の日時文字列を検出して変換
                    datetime.fromisoformat(value)
                    data[key] = datetime.fromisoformat(value)
                except ValueError:
                    pass
            elif isinstance(value, dict):
                data[key] = self.deserialize_datetime(value)
            elif isinstance(value, list):
                data[key] = [
                    self.deserialize_datetime(item) if isinstance(item, dict) else item 
                    for item in value
                ]
        return data

    def dump_json(self, data: Dict, file_path: Path) -> None:
        """JSONデータをファイルに保存"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, default=self.serialize_datetime, 
                         ensure_ascii=False, indent=2)
            self.logger.info(f'Successfully saved session to {file_path}')
        except Exception as e:
            self.logger.error(f'Failed to save session: {str(e)}', exc_info=True)
            raise

    def load_json(self, file_path: Path) -> Dict:
        """JSONファイルからデータを読み込み"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            converted_data = self.deserialize_datetime(data)
            self.logger.info(f'Successfully loaded session from {file_path}')
            return converted_data
        except Exception as e:
            self.logger.error(f'Failed to load session: {str(e)}', exc_info=True)
            raise