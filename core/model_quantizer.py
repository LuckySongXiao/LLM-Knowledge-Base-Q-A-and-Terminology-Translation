import os
import torch
import logging
from enum import Enum, auto

# 配置日志
logger = logging.getLogger(__name__)

class QuantizationLevel(Enum):
    """量化级别枚举"""
    AUTO = auto()   # 自动选择
    NONE = 0        # 不进行量化，使用原始精度
    FP16 = 1        # 半精度浮点数 (16位)
    INT8 = 2        # 8位整数量化
    INT4 = 3        # 4位整数量化

class ModelQuantizer:
    """模型量化管理器，根据GPU资源自动选择合适的量化级别"""

    def __init__(self, settings=None):
        """初始化量化管理器"""
        self.settings = settings or {}

        # 默认设置 - 根据实际测试调整的显存需求
        self.min_vram_gb = {
            QuantizationLevel.NONE: 12.0,  # 不量化需要至少12GB显存（根据实际测试调整）
            QuantizationLevel.FP16: 8.0,   # FP16需要至少8GB显存
            QuantizationLevel.INT8: 6.0,   # INT8需要至少6GB显存
            QuantizationLevel.INT4: 4.0    # INT4需要至少4GB显存（提高要求确保稳定）
        }

        # 模型大小估算（GB）- 用于更精确的显存需求计算
        self.model_size_estimates = {
            "qwen2.5-3b": 3.0,    # Qwen2.5-3B模型大小约3GB
            "qwen2.5-7b": 7.0,    # Qwen2.5-7B模型大小约7GB
            "qwen2.5-14b": 14.0,  # Qwen2.5-14B模型大小约14GB
            "default": 3.0        # 默认假设3B模型
        }

        # 根据设置覆盖默认值
        if settings:
            user_min_vram = settings.get('quantization_min_vram', {})
            for level_name, gb in user_min_vram.items():
                try:
                    level = QuantizationLevel[level_name]
                    self.min_vram_gb[level] = float(gb)
                except (KeyError, ValueError):
                    logger.warning(f"无效的量化级别设置: {level_name}={gb}")

        # 检测可用的显存
        self.available_vram_gb = self._detect_available_vram()
        logger.info(f"检测到可用显存: {self.available_vram_gb:.2f} GB")

        # 自动选择量化级别
        self.auto_level = self._auto_select_level()
        logger.info(f"自动选择的量化级别: {self.auto_level.name}")

    def _detect_available_vram(self):
        """检测可用的GPU显存"""
        try:
            if not torch.cuda.is_available():
                logger.info("CUDA不可用，将使用CPU模式")
                return 0.0

            # 获取当前设备
            device = torch.cuda.current_device()

            # 获取总显存
            total_memory = torch.cuda.get_device_properties(device).total_memory
            total_memory_gb = total_memory / (1024 ** 3)

            # 获取已分配的显存
            allocated_memory = torch.cuda.memory_allocated(device)
            allocated_memory_gb = allocated_memory / (1024 ** 3)

            # 获取缓存的显存
            reserved_memory = torch.cuda.memory_reserved(device)
            reserved_memory_gb = reserved_memory / (1024 ** 3)

            # 计算可用显存(GB)
            free_memory = total_memory - allocated_memory - reserved_memory
            free_memory_gb = free_memory / (1024 ** 3)

            # 详细的显存信息日志
            logger.info(f"GPU显存详情:")
            logger.info(f"  总显存: {total_memory_gb:.2f} GB")
            logger.info(f"  已分配: {allocated_memory_gb:.2f} GB")
            logger.info(f"  已缓存: {reserved_memory_gb:.2f} GB")
            logger.info(f"  可用显存: {free_memory_gb:.2f} GB")

            # 保留一些显存作为安全边际（10%）
            safe_memory_gb = free_memory_gb * 0.9
            logger.info(f"  安全可用显存: {safe_memory_gb:.2f} GB")

            return safe_memory_gb

        except Exception as e:
            logger.error(f"检测显存时出错: {e}")
            return 0.0

    def estimate_model_memory_requirement(self, model_path, model_name=None):
        """估算模型的显存需求"""
        try:
            # 尝试从模型名称推断大小
            if model_name:
                model_name_lower = model_name.lower()
                for key, size in self.model_size_estimates.items():
                    if key in model_name_lower:
                        logger.info(f"根据模型名称 '{model_name}' 估算模型大小: {size} GB")
                        return size

            # 尝试从路径推断大小
            if model_path:
                path_lower = model_path.lower()
                for key, size in self.model_size_estimates.items():
                    if key in path_lower:
                        logger.info(f"根据模型路径 '{model_path}' 估算模型大小: {size} GB")
                        return size

            # 尝试通过检查模型文件大小估算
            if model_path and os.path.exists(model_path):
                total_size = 0
                for root, _, files in os.walk(model_path):
                    for file in files:
                        if file.endswith(('.bin', '.safetensors', '.pt', '.pth')):
                            file_path = os.path.join(root, file)
                            if os.path.exists(file_path):
                                total_size += os.path.getsize(file_path)

                if total_size > 0:
                    size_gb = total_size / (1024 ** 3)
                    logger.info(f"根据文件大小估算模型大小: {size_gb:.2f} GB")
                    return size_gb

            # 默认估算
            default_size = self.model_size_estimates["default"]
            logger.info(f"使用默认模型大小估算: {default_size} GB")
            return default_size

        except Exception as e:
            logger.error(f"估算模型大小时出错: {e}")
            return self.model_size_estimates["default"]

    def recommend_quantization_level(self, model_path=None, model_name=None):
        """智能推荐量化级别"""
        try:
            # 估算模型大小
            estimated_model_size = self.estimate_model_memory_requirement(model_path, model_name)

            # 计算不同量化级别下的显存需求
            memory_requirements = {}

            # 定义具体的量化级别（排除AUTO）
            quantization_levels = [
                QuantizationLevel.NONE,
                QuantizationLevel.FP16,
                QuantizationLevel.INT8,
                QuantizationLevel.INT4
            ]

            for level in quantization_levels:
                # 根据量化级别计算显存需求（基于实际测试数据优化）
                if level == QuantizationLevel.NONE:
                    # 不量化：基于实际测试，5.75GB模型需要约7.6GB显存
                    # 计算比例：7.6/5.75 ≈ 1.32，为安全起见使用1.4
                    required_memory = estimated_model_size * 1.4
                elif level == QuantizationLevel.FP16:
                    # FP16：模型大小的70% + 40%的额外开销（基于实际经验）
                    required_memory = estimated_model_size * 0.7 * 1.4
                elif level == QuantizationLevel.INT8:
                    # INT8：模型大小的40% + 30%的额外开销
                    required_memory = estimated_model_size * 0.4 * 1.3
                elif level == QuantizationLevel.INT4:
                    # INT4：模型大小的25% + 25%的额外开销
                    required_memory = estimated_model_size * 0.25 * 1.25

                memory_requirements[level] = required_memory

            # 记录显存需求分析
            logger.info(f"模型显存需求分析:")
            logger.info(f"  估算模型大小: {estimated_model_size:.2f} GB")
            logger.info(f"  可用显存: {self.available_vram_gb:.2f} GB")
            logger.info(f"  各量化级别显存需求:")

            # 找到最佳的量化级别
            recommended_level = QuantizationLevel.INT4  # 默认最保守的选择

            # 从最低量化到最高量化检查
            for level in quantization_levels:
                required = memory_requirements[level]
                can_fit = self.available_vram_gb >= required

                logger.info(f"    {level.name}: {required:.2f} GB ({'✓' if can_fit else '✗'})")

                if can_fit:
                    recommended_level = level
                    break

            logger.info(f"  推荐量化级别: {recommended_level.name}")
            return recommended_level

        except Exception as e:
            logger.error(f"推荐量化级别时出错: {e}")
            return QuantizationLevel.INT4

    def _auto_select_level(self):
        """根据可用显存自动选择量化级别"""
        # 如果有用户设置的级别，优先使用
        user_level = None
        if self.settings and hasattr(self.settings, 'get'):
            # 使用get方法从Settings对象获取配置
            level_name = self.settings.get('quantization_level')
            if level_name:
                # 如果设置为AUTO，使用自动选择
                if level_name == "AUTO":
                    user_level = QuantizationLevel.AUTO
                else:
                    try:
                        user_level = QuantizationLevel[level_name]
                    except KeyError:
                        logger.warning(f"无效的量化级别设置: {level_name}，将自动选择")

        # 如果是自动选择或没有指定，根据显存决定
        if not user_level or user_level == QuantizationLevel.AUTO:
            # 根据可用显存自动选择
            if not torch.cuda.is_available():
                # 如果CUDA不可用，使用INT8量化减轻CPU负担
                return QuantizationLevel.INT8

            # 从最低量化到最高量化依次检查
            for level in sorted(QuantizationLevel, key=lambda x: x.value if isinstance(x.value, int) else 999):
                # 跳过AUTO级别
                if level == QuantizationLevel.AUTO:
                    continue

                if self.available_vram_gb >= self.min_vram_gb[level]:
                    return level

            # 如果显存不足，使用最高级别的量化
            return QuantizationLevel.INT4
        else:
            # 使用用户指定的级别
            return user_level

    def get_quantization_config(self, model_type=None):
        """根据自动选择的级别获取量化配置"""
        level = self.auto_level

        # 如果是AUTO级别，根据显存再次自动选择
        if level == QuantizationLevel.AUTO:
            # 根据可用显存自动选择
            if not torch.cuda.is_available():
                level = QuantizationLevel.INT8
            else:
                # 从最低量化到最高量化依次检查
                for lvl in sorted(QuantizationLevel, key=lambda x: x.value if isinstance(x.value, int) else 999):
                    # 跳过AUTO级别
                    if lvl == QuantizationLevel.AUTO:
                        continue

                    if self.available_vram_gb >= self.min_vram_gb[lvl]:
                        level = lvl
                        break
                else:
                    # 如果显存不足，使用最高级别的量化
                    level = QuantizationLevel.INT4

            logger.info(f"AUTO级别自动选择为: {level.name}")

        # 基本配置
        config = {
            "level": level,
            "device_map": "auto",
            "torch_dtype": torch.float32,  # 默认使用float32
            "load_in_8bit": False,
            "load_in_4bit": False,
            "quantization_config": None
        }

        # 根据级别设置详细配置
        if level == QuantizationLevel.FP16:
            config["torch_dtype"] = torch.float16
        elif level == QuantizationLevel.INT8:
            config["load_in_8bit"] = True

            # 高级8位量化配置
            from transformers import BitsAndBytesConfig
            config["quantization_config"] = BitsAndBytesConfig(
                load_in_8bit=True,
                llm_int8_threshold=6.0,
                llm_int8_has_fp16_weight=False
            )
        elif level == QuantizationLevel.INT4:
            config["load_in_4bit"] = True

            # 高级4位量化配置
            from transformers import BitsAndBytesConfig
            config["quantization_config"] = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_use_double_quant=True,
                bnb_4bit_quant_type="nf4"
            )

        # 特定模型的优化
        if model_type and "qwen" in model_type.lower():
            # Qwen模型特定配置
            if level == QuantizationLevel.NONE:
                # 即使不量化，也使用半精度浮点数加载Qwen模型
                config["torch_dtype"] = torch.float16

        return config

    def get_memory_optimization_config(self):
        """获取内存优化配置"""
        config = {}

        # 根据量化级别设置内存优化
        if self.auto_level in [QuantizationLevel.INT8, QuantizationLevel.INT4]:
            config["low_cpu_mem_usage"] = True

            # 如果有CUDA，设置显存管理策略
            if torch.cuda.is_available():
                # 确定显存容量
                gb = self.available_vram_gb

                if gb < 6:  # 对于低显存设备，更激进的优化
                    config["max_memory"] = {0: f"{int(gb * 0.9)}GiB"}
                    config["offload_folder"] = "offload_folder"
                elif gb < 12:  # 中等显存
                    config["max_memory"] = {0: f"{int(gb * 0.95)}GiB"}
                else:  # 高显存
                    config["max_memory"] = {0: f"{int(gb * 0.98)}GiB"}

        return config

    def quantize_model(self, model, level=None):
        """对已加载的模型进行量化（后量化）"""
        if not level:
            level = self.auto_level

        if not model:
            return None

        try:
            if level == QuantizationLevel.FP16:
                # 将模型转换为FP16
                model = model.half()
                logger.info("模型已转换为FP16精度")
            elif level == QuantizationLevel.INT8:
                # 检查是否支持INT8量化
                if hasattr(torch.nn, 'quantize_dynamic'):
                    # 动态量化到INT8
                    model = torch.nn.quantize_dynamic(
                        model, {torch.nn.Linear}, dtype=torch.qint8
                    )
                    logger.info("模型已动态量化为INT8精度")
                else:
                    logger.warning("当前PyTorch版本不支持动态量化，尝试转换为FP16")
                    model = model.half()
            elif level == QuantizationLevel.INT4:
                logger.warning("已加载模型不支持转换为INT4，请在加载时应用量化配置")

            return model
        except Exception as e:
            logger.error(f"量化模型失败: {e}")
            return model  # 返回原始模型