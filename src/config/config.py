import yaml
import os
from typing import Dict
from loguru import logger


class Config:
    """配置管理"""
    
    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = config_path
        self.config = self._load_config()
    
    def _load_config(self) -> Dict:
        """加载配置文件"""
        if not os.path.exists(self.config_path):
            # 如果没有配置文件，复制示例配置
            example_path = "config.example.yaml"
            if os.path.exists(example_path):
                import shutil
                shutil.copy(example_path, self.config_path)
                logger.info(f"已自动创建配置文件: {self.config_path}，请修改后重新运行")
            else:
                raise Exception(f"配置文件不存在: {self.config_path} 且示例配置也不存在")
        
        with open(self.config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def get(self, key: str, default=None):
        """获取配置项，支持点分隔符，比如 'global.use_gpu'"""
        keys = key.split('.')
        value = self.config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value
    
    def get_game_config(self, game_key: str) -> Dict:
        """获取指定游戏的配置"""
        game_config = self.get(f"{game_key}", {})
        # 合并全局配置
        global_config = self.get("global", {})
        common_config = self.get("game_common", {})
        merged = {**global_config, **common_config, **game_config}
        return merged
