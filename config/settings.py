import json
import os
import logging

logger = logging.getLogger(__name__)

class Settings:
    """应用程序配置管理类"""

    def __init__(self, config_file="config.json"):
        """
        初始化配置

        Args:
            config_file (str, optional): 配置文件路径. 默认为 "config.json".
        """
        self.config_file = config_file
        self.settings = {
            # 基本设置
            "app_name": "松瓷机电AI助手",
            "language": "zh",
            "theme": "auto",

            # 模型设置
            "model_path": os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "QWEN"),
            "vector_model_path": os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "BAAI"),
            "model_name": "Qwen2.5-7B",
            "vector_model_name": "bge-m3",

            # 模型量化设置
            "enable_auto_quantization": True,  # 是否启用自动量化
            "quantization_level": "AUTO",  # AUTO, NONE, FP16, INT8, INT4
            "quantization_min_vram": {  # 各量化级别所需的最小显存(GB)
                "NONE": 24.0,
                "FP16": 12.0,
                "INT8": 8.0,
                "INT4": 4.0
            },
            "memory_optimization": {
                "low_cpu_mem_usage": True,     # 低CPU内存使用
                "use_offload": True,           # 是否使用显存不足时卸载到CPU
                "offload_folder": "offload_folder"  # 卸载到磁盘的临时文件夹
            },

            # 聊天设置
            "system_prompt": "You are Qwen, created by Alibaba Cloud. You are a helpful assistant.",
            "max_history": 10,
            "temperature": 0.7,
            "top_p": 0.9,
            "top_k": 15,
            "repetition_penalty": 1.1,
            "max_new_tokens": 2048,
            "do_sample": True,

            # 知识库设置
            "kb_path": "data/knowledge",
            "kb_vector_path": "data/kb_vectors",
            "kb_top_k": 15,                    # 知识库问答参考文件上下文数量
            "kb_threshold": 0.7,               # 知识库搜索相似度阈值
            "kb_temperature": 0.6,             # 知识库问答专用温度参数
            "enable_knowledge": True,          # 是否启用知识库问答

            # 术语库设置
            "term_path": "data/terms",
            "term_vector_path": "data/term_vectors",

            # 更新设置
            "auto_check_updates": True,
            "check_updates_on_startup": True,
            "update_check_interval": 24 * 60 * 60,  # 24小时
            "update_check_url": "https://example.com/updates.json",
            "ignored_version": "",  # 用户选择忽略的版本
            "update_channel": "stable",  # 更新渠道: stable/beta
            "auto_install_updates": False,  # 是否自动安装更新
        }

        # 加载配置文件
        self.load()

    def load(self):
        """加载配置文件"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded_settings = json.load(f)
                    # 更新配置，保留默认值
                    for key, value in loaded_settings.items():
                        self.settings[key] = value
                logger.info(f"已加载配置文件: {self.config_file}")
            except Exception as e:
                logger.error(f"加载配置文件失败: {e}")

    def save(self):
        """保存配置文件"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=2)
            logger.info(f"已保存配置文件: {self.config_file}")
        except Exception as e:
            logger.error(f"保存配置文件失败: {e}")

    def get(self, key, default=None):
        """
        获取配置项

        Args:
            key (str): 配置项键名
            default (Any, optional): 默认值. 默认为 None.

        Returns:
            Any: 配置项值
        """
        return self.settings.get(key, default)

    def set(self, key, value):
        """
        设置配置项

        Args:
            key (str): 配置项键名
            value (Any): 配置项值
        """
        self.settings[key] = value

    def get_all(self):
        """
        获取所有配置项

        Returns:
            dict: 所有配置项的字典
        """
        return self.settings