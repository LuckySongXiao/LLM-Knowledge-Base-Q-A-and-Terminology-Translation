import sys
import os
import torch  # 添加torch导入

# 添加typing补丁 - 这必须在导入任何其他模块前
try:
    import typing_patch
except ImportError:
    # 如果找不到补丁文件，动态创建一个
    with open('typing_patch.py', 'w') as f:
        f.write("""import sys
import typing

# 检查是否已经有Self定义
if not hasattr(typing, 'Self'):
    # 为旧版本Python添加Self类型
    typing.Self = typing.TypeVar('Self', bound=object)
    # 将此类型添加到typing模块的__all__
    if hasattr(typing, '__all__'):
        typing.__all__ += ['Self']
    print("已添加typing.Self兼容补丁")
""")
    import typing_patch

# 尝试导入PySide6，如果失败则说明在web环境中运行
try:
    from PySide6.QtWidgets import QApplication
    from ui.main_window import MainWindow
    from ui.chat_panel import ChatPanel
    WEB_MODE = False
except ImportError:
    # 在web环境中运行，不需要GUI组件
    QApplication = None
    MainWindow = None
    ChatPanel = None
    WEB_MODE = True

# 导入核心模块
try:
    from config.settings import Settings
except ImportError:
    # 如果无法导入，可能是在web环境中，尝试相对导入
    import sys
    import os
    # 确保项目根目录在路径中
    project_root = os.path.dirname(os.path.abspath(__file__))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    from config.settings import Settings

from core.ai_engine import AIEngine
from core.vector_db import VectorDB
from core.knowledge_base import KnowledgeBase
from core.term_base import TermBase
from core.translator import Translator
from core.text_monitor import TextMonitor
from utils.i18n import I18n
from core.term_vector_db import TermVectorDB
import time
from modelscope.hub.snapshot_download import snapshot_download

# 导入自动更新器
try:
    from auto_updater import AutoUpdater
except ImportError:
    AutoUpdater = None

# 添加环境变量设置
os.environ["TRANSFORMERS_NO_ADVISORY_WARNINGS"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "max_split_size_mb:512"

class AIAssistant:
    """桌面端松瓷机电AI助手应用的主类"""

    def __init__(self, web_mode=None):
        # 如果没有明确指定web_mode，则根据WEB_MODE全局变量判断
        if web_mode is None:
            web_mode = WEB_MODE

        self.web_mode = web_mode

        # 检查transformers版本
        try:
            import transformers
            version = transformers.__version__
            print(f"当前transformers版本: {version}")

            # 确保使用兼容的版本
            if version < "4.37.0":
                print("警告：当前transformers版本过低，需要升级到4.37.0或更高版本")
                print("请运行: pip install --upgrade transformers>=4.37.0")
                if not web_mode:  # 只在非web模式下退出
                    sys.exit(1)
        except ImportError:
            print("未安装transformers，请安装4.37.0或更高版本")
            print("请运行: pip install transformers>=4.37.0")
            if not web_mode:  # 只在非web模式下退出
                sys.exit(1)

        # 检查必要的依赖
        self.check_dependencies()

        # 只在非web模式下创建QApplication
        if not web_mode and QApplication is not None:
            self.app = QApplication(sys.argv)
        else:
            self.app = None

        # 初始化配置
        self.settings = Settings()
        # 初始化国际化
        self.i18n = I18n(self.settings.get('language', 'zh'))

        # 初始化核心组件
        self.initialize_components()

        # 手动测试并加载向量模型
        self.test_and_load_vector_model()

        # 初始化向量数据库
        if hasattr(self, 'vector_db'):
            self.vector_db.initialize()

        # 加载模型
        self.load_models()

        # 初始化自动更新器（只在非web模式下）
        if not web_mode:
            self.init_auto_updater()

        # 只在非web模式下初始化UI
        if not web_mode and MainWindow is not None:
            self.main_window = MainWindow(self)
        else:
            self.main_window = None

        # 确保知识库中的所有条目都有向量
        if hasattr(self, 'knowledge_base') and self.knowledge_base:
            print("确保所有知识条目都有对应的向量...")
            self.knowledge_base.ensure_vectors()

    def initialize_components(self):
        """初始化应用程序核心组件"""
        # 初始化AI引擎
        self.ai_engine = AIEngine(self.settings)

        # 初始化向量数据库 (知识库使用)
        if not hasattr(self, 'vector_db'):
            from core.vector_db import VectorDB
            self.vector_db = VectorDB(self.settings)

        # 确保BGE-M3模型文件完整
        bge_m3_path = os.path.join('BAAI', 'bge-m3')
        self.ensure_model_files('BAAI/bge-m3', bge_m3_path)

        # 添加术语库专用向量数据库
        if not hasattr(self, 'term_vector_db'):
            from core.term_vector_db import TermVectorDB
            self.term_vector_db = TermVectorDB(self.settings)
            # 共享知识库的向量模型
            if hasattr(self.vector_db, 'model') and self.vector_db.model:
                self.term_vector_db.model = self.vector_db.model

        # 初始化知识库
        if not hasattr(self, 'knowledge_base'):
            from core.knowledge_base import KnowledgeBase
            self.knowledge_base = KnowledgeBase(self.vector_db, self.settings)

        # 初始化术语库 - 使用专用向量数据库
        if not hasattr(self, 'term_base'):
            from core.term_base import TermBase
            self.term_base = TermBase(self.term_vector_db, self.settings)

        # 初始化翻译引擎
        self.translator = Translator(self.ai_engine, self.term_base, self.settings)

        # 初始化文本监控
        self.text_monitor = TextMonitor(self.translator)

        # 初始化模型管理器
        self.init_model_manager()

    def _ensure_dependencies(self):
        """确保必要的依赖已安装"""
        try:
            # 检查是否有BGE-M3模型
            vector_model_path = self.settings.get('vector_model_path', '')
            if "bge-m3" in vector_model_path.lower():
                try:
                    # 尝试导入FlagEmbedding
                    import importlib
                    flagembedding = importlib.import_module('FlagEmbedding')
                    print(f"已安装FlagEmbedding库 {flagembedding.__version__ if hasattr(flagembedding, '__version__') else '(版本未知)'}")
                except ImportError:
                    print("未安装FlagEmbedding库，正在安装...")
                    import subprocess
                    subprocess.run(["pip", "install", "FlagEmbedding>=1.2.0"], check=True)
                    print("FlagEmbedding库安装完成")

            # 检查是否有sentence-transformers依赖
            try:
                import sentence_transformers
                print(f"已安装sentence-transformers库 {sentence_transformers.__version__ if hasattr(sentence_transformers, '__version__') else '(版本未知)'}")
            except ImportError:
                print("未安装sentence-transformers库，正在安装...")
                import subprocess
                subprocess.run(["pip", "install", "sentence-transformers"], check=True)
                print("sentence-transformers库安装完成")

        except Exception as e:
            print(f"安装依赖时出错: {e}")

        # 添加这段代码确保术语库正确初始化
        print("检查术语库初始化状态...")
        if hasattr(self, 'term_base'):
            print(f"术语库类型: {type(self.term_base).__name__}")
            print(f"术语库向量数据库: {type(self.term_base.vector_db).__name__ if hasattr(self.term_base, 'vector_db') else 'None'}")
        else:
            print("警告: 术语库未初始化!")
            # 尝试强制初始化
            try:
                from core.term_base import TermBase
                if hasattr(self, 'term_vector_db'):
                    self.term_base = TermBase(self.term_vector_db, self.settings)
                    print("术语库已手动初始化")
                else:
                    print("错误: 术语向量数据库未初始化，无法创建术语库")
            except Exception as e:
                print(f"术语库初始化失败: {e}")

    def init_model_manager(self):
        """初始化模型管理器"""
        from core.model_manager import ModelManager

        # 创建模型管理器
        self.model_manager = ModelManager(self.settings)

        # 连接下载信号
        self.model_manager.download_progress.connect(self.on_model_download_progress)
        self.model_manager.download_complete.connect(self.on_model_download_complete)
        self.model_manager.download_error.connect(self.on_model_download_error)

        # 获取当前已有的模型
        available_models = {
            ModelManager.MODEL_TYPE_LLM: self.model_manager.detect_models(
                self.model_manager.get_model_path(ModelManager.MODEL_TYPE_LLM),
                ModelManager.MODEL_TYPE_LLM
            ),
            ModelManager.MODEL_TYPE_EMBEDDING: self.model_manager.detect_models(
                self.model_manager.get_model_path(ModelManager.MODEL_TYPE_EMBEDDING),
                ModelManager.MODEL_TYPE_EMBEDDING
            )
        }

        # 输出检测到的模型
        for model_type, models in available_models.items():
            for model in models:
                print(f"检测到{model_type}模型: {model['name']} - {model['path']}")

    def init_auto_updater(self):
        """初始化自动更新器"""
        # 检查是否安装了自动更新器模块
        if AutoUpdater is None:
            print("警告: 未找到自动更新器模块，自动更新功能将不可用")
            return

        try:
            # 获取配置的更新检查URL
            check_url = self.settings.get('update_check_url', '')

            if not check_url:
                # 如果未配置，使用默认URL
                check_url = "https://example.com/updates.json"
                print(f"未配置更新检查URL，使用默认URL: {check_url}")

            # 创建自动更新器实例
            self.auto_updater = AutoUpdater(
                app_name=self.settings.get('app_name', '松瓷机电AI助手'),
                check_url=check_url,
                on_progress=self.on_update_progress
            )

            print("自动更新器初始化成功")

            # 设置最后检查时间
            self.last_update_check = 0

            # 如果设置为自动检查更新，启动检查
            if self.settings.get('auto_check_updates', True):
                # 延迟10秒后检查更新，让应用先完成启动
                if hasattr(self, 'app'):
                    self.app.processEvents()
                    timer_id = self.app.startTimer(10000)
                    self.app.timerEvent = lambda event: self.check_for_updates_if_needed(event, timer_id)

        except Exception as e:
            print(f"初始化自动更新器失败: {e}")
            import traceback
            traceback.print_exc()

    def check_for_updates_if_needed(self, event=None, timer_id=None):
        """如果需要，检查更新"""
        # 如果是定时器事件，停止定时器
        if event and timer_id and event.timerId() == timer_id:
            self.app.killTimer(timer_id)

        # 检查是否已初始化自动更新器
        if not hasattr(self, 'auto_updater'):
            return

        # 获取当前时间
        current_time = time.time()

        # 获取检查间隔（默认24小时）
        check_interval = self.settings.get('update_check_interval', 24 * 60 * 60)

        # 如果距离上次检查时间超过了检查间隔，则检查更新
        if current_time - self.last_update_check > check_interval:
            self.check_for_updates()

    def check_for_updates(self):
        """检查更新"""
        # 检查是否已初始化自动更新器
        if not hasattr(self, 'auto_updater'):
            print("自动更新器未初始化，无法检查更新")
            return

        print("正在检查更新...")

        # 更新最后检查时间
        self.last_update_check = time.time()

        try:
            # 检查更新
            has_update, current_version, latest_version = self.auto_updater.check_for_updates()

            if has_update:
                print(f"发现新版本: {latest_version} (当前版本: {current_version})")

                # 显示更新提示对话框
                self.show_update_dialog(current_version, latest_version)
            else:
                print(f"当前已是最新版本: {current_version}")
        except Exception as e:
            print(f"检查更新失败: {e}")

    def show_update_dialog(self, current_version, latest_version):
        """显示更新提示对话框"""
        from PySide6.QtWidgets import QMessageBox, QCheckBox

        # 创建消息框
        msgBox = QMessageBox(self.main_window)
        msgBox.setWindowTitle("软件更新")
        msgBox.setText(f"发现新版本: {latest_version}")
        msgBox.setInformativeText(f"当前版本: {current_version}\n是否立即更新?")
        msgBox.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msgBox.setDefaultButton(QMessageBox.Yes)

        # 添加"不再提醒"复选框
        dontAskCheckBox = QCheckBox("不再提醒此版本", msgBox)
        msgBox.setCheckBox(dontAskCheckBox)

        # 显示对话框
        ret = msgBox.exec()

        # 处理用户选择
        if ret == QMessageBox.Yes:
            # 用户选择更新
            self.download_and_apply_update()
        elif dontAskCheckBox.isChecked():
            # 用户选择不再提醒此版本
            self.settings.set('ignored_version', latest_version)
            self.settings.save()

    def download_and_apply_update(self):
        """下载并应用更新"""
        # 显示更新进度对话框
        from PySide6.QtWidgets import QProgressDialog
        from PySide6.QtCore import Qt

        # 创建进度对话框
        self.progress_dialog = QProgressDialog("准备更新...", "取消", 0, 100, self.main_window)
        self.progress_dialog.setWindowTitle("正在更新")
        self.progress_dialog.setWindowModality(Qt.WindowModal)
        self.progress_dialog.setAutoClose(False)
        self.progress_dialog.setAutoReset(False)
        self.progress_dialog.canceled.connect(self.cancel_update)
        self.progress_dialog.show()

        # 开始下载更新
        self.auto_updater.download_updates()

    def cancel_update(self):
        """取消更新"""
        if hasattr(self, 'auto_updater'):
            self.auto_updater.is_updating = False
            print("更新已取消")

    def on_update_progress(self, progress, message):
        """更新进度回调函数"""
        if hasattr(self, 'progress_dialog'):
            # 更新进度对话框
            self.progress_dialog.setValue(int(progress * 100))
            self.progress_dialog.setLabelText(message)

            # 如果更新完成，提示用户重启
            if progress >= 1.0:
                self.progress_dialog.close()

                from PySide6.QtWidgets import QMessageBox
                result = QMessageBox.question(
                    self.main_window,
                    "更新完成",
                    "更新已完成，需要重启应用程序以应用更新。\n是否立即重启?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes
                )

                if result == QMessageBox.Yes:
                    # 用户选择立即重启
                    self.auto_updater.restart_application()

    def load_models(self):
        """加载所有检测到的模型"""
        # 使用简化的模型加载方法
        success = self._load_models_efficiently()

        if not success:
            print("模型加载失败，尝试使用原始加载方法")

            # 回退到传统加载方法
            from core.model_loader import ModelLoader
            from ui.loading_screen import LoadingScreen

            # 创建加载界面
            self.loading_screen = LoadingScreen()

            # 创建模型加载器
            self.model_loader = ModelLoader(self.model_manager)

            # 连接信号
            self.model_loader.loading_progress.connect(self.loading_screen.update_progress)
            self.model_loader.loading_complete.connect(self.loading_screen.set_complete)
            self.model_loader.loading_error.connect(self.loading_screen.set_error)
            self.model_loader.all_models_loaded.connect(lambda: self.loading_screen.close_after_delay())

            # 开始加载模型
            self.model_loader.load_models()

            # 显示加载界面
            self.loading_screen.exec()

            # 更新AI引擎的模型设置
            llm_model = self.model_loader.get_loaded_model(self.model_manager.MODEL_TYPE_LLM)
            if llm_model:
                print(f"设置AI引擎模型: {llm_model['name']}")
                self.ai_engine.set_model(llm_model)

            # 更新向量数据库的模型设置
            embedding_model = self.model_loader.get_loaded_model(self.model_manager.MODEL_TYPE_EMBEDDING)
            if embedding_model:
                print(f"设置向量数据库模型: {embedding_model['name']}")
                success = self.vector_db.set_model(embedding_model)
                if not success:
                    print("向量模型设置失败，尝试直接加载...")
                    self._load_bge_m3_model(os.path.join(self.settings.get('vector_model_path', ''), "bge-m3"))
            else:
                print("警告: 没有加载向量模型，尝试直接加载...")
                self._load_bge_m3_model(os.path.join(self.settings.get('vector_model_path', ''), "bge-m3"))

        print("模型加载过程完成")

        # 如果配置了自动检查更新并且可以在启动后立即检查
        if hasattr(self, 'auto_updater') and self.settings.get('check_updates_on_startup', False):
            print("启动时检查更新...")
            self.check_for_updates()

    def _load_models_efficiently(self):
        """优化的模型加载过程"""
        try:
            # 定义模型根目录
            base_dir = os.path.dirname(os.path.abspath(__file__))

            # 1. 检测和加载LLM模型
            llm_path = self.settings.get('model_path', os.path.join(base_dir, "QWEN"))
            if not os.path.exists(llm_path):
                os.makedirs(llm_path, exist_ok=True)

            # 检测LLM模型
            llm_models = self.model_manager.detect_models(llm_path, self.model_manager.MODEL_TYPE_LLM)
            if llm_models:
                # 选择最优模型（通常是第一个检测到的）
                llm_model = llm_models[0]
                print(f"使用现有LLM模型: {llm_model['name']}")

                try:
                    # 使用Qwen2.5官方推荐的方式加载模型
                    from transformers import AutoModelForCausalLM, AutoTokenizer
                    import torch
                    from core.model_quantizer import ModelQuantizer

                    print(f"加载Qwen2.5模型: {llm_model['path']}")

                    # 强制检查CUDA是否可用并输出详细信息
                    print("==== 设备检测开始 ====")
                    cuda_available = torch.cuda.is_available()
                    print(f"CUDA是否可用: {cuda_available}")

                    if cuda_available:
                        device = "cuda"
                        print(f"CUDA版本: {torch.version.cuda}")
                        gpu_count = torch.cuda.device_count()
                        print(f"GPU数量: {gpu_count}")

                        # 打印每个GPU的信息
                        for i in range(gpu_count):
                            print(f"GPU #{i} - {torch.cuda.get_device_name(i)}")
                            print(f"  显存总量: {torch.cuda.get_device_properties(i).total_memory / 1024 / 1024 / 1024:.2f} GB")
                            print(f"  当前显存占用: {torch.cuda.memory_allocated(i) / 1024 / 1024 / 1024:.2f} GB")
                            print(f"  当前缓存: {torch.cuda.memory_reserved(i) / 1024 / 1024 / 1024:.2f} GB")

                        # 清理显存缓存
                        torch.cuda.empty_cache()
                        print("已清理GPU缓存")
                    else:
                        device = "cpu"
                        # 获取CPU信息
                        import platform
                        import multiprocessing
                        print(f"CPU信息: {platform.processor()}")
                        print(f"CPU架构: {platform.machine()}")
                        print(f"CPU核心数: {multiprocessing.cpu_count()}")

                    print(f"将使用设备: {device}")
                    print("==== 设备检测结束 ====")

                    # 初始化量化管理器
                    print("初始化模型量化管理器...")
                    quantizer = ModelQuantizer(self.settings)

                    # 智能推荐量化级别
                    print("分析模型和GPU资源，智能推荐量化级别...")
                    recommended_level = quantizer.recommend_quantization_level(
                        model_path=llm_model['path'],
                        model_name=llm_model['name']
                    )

                    # 更新量化管理器的自动级别为推荐级别
                    quantizer.auto_level = recommended_level
                    print(f"智能推荐的量化级别: {recommended_level.name}")
                    print(f"可用显存: {quantizer.available_vram_gb:.2f} GB")

                    # 获取量化配置
                    quant_config = quantizer.get_quantization_config("qwen")
                    mem_config = quantizer.get_memory_optimization_config()

                    # 加载tokenizer
                    print("加载tokenizer...")
                    tokenizer = AutoTokenizer.from_pretrained(
                        llm_model['path'],
                        trust_remote_code=True
                    )
                    print("tokenizer加载成功")

                    # 合并所有配置
                    model_kwargs = {
                        "device_map": quant_config["device_map"],
                        "trust_remote_code": True,
                        "torch_dtype": quant_config["torch_dtype"],
                    }

                    # 添加量化配置
                    if quant_config["quantization_config"]:
                        model_kwargs["quantization_config"] = quant_config["quantization_config"]

                    # 添加内存优化配置
                    for key, value in mem_config.items():
                        model_kwargs[key] = value

                    print(f"使用以下配置加载模型:")
                    for key, value in model_kwargs.items():
                        if key != "quantization_config":  # 量化配置太复杂，不打印详情
                            print(f"  - {key}: {value}")
                        else:
                            print(f"  - {key}: [已配置]")

                    # 加载模型
                    print(f"正在加载模型...")
                    model = AutoModelForCausalLM.from_pretrained(
                        llm_model['path'],
                        **model_kwargs
                    )

                    # 输出模型信息
                    print(f"模型设备: {next(model.parameters()).device}")
                    print(f"模型类型: {model.__class__.__name__}")

                    # 输出显存使用情况
                    if torch.cuda.is_available():
                        allocated_gb = torch.cuda.memory_allocated() / (1024**3)
                        print(f"当前显存占用: {allocated_gb:.2f} GB")

                    # 创建模型信息字典
                    model_info = {
                        "name": llm_model['name'],
                        "path": llm_model['path'],
                        "model": model,
                        "tokenizer": tokenizer,
                        "type": "transformer",
                        "device": str(next(model.parameters()).device)
                    }

                    # 直接设置chat_engine的属性，避免使用set_model引起重复加载
                    self.ai_engine.chat_engine.model = model_info
                    self.ai_engine.chat_engine.tokenizer = tokenizer
                    self.ai_engine.chat_engine.model_path = llm_model['path']

                    # 共享模型到其他引擎
                    self.ai_engine.knowledge_engine.model = model_info
                    self.ai_engine.knowledge_engine.tokenizer = tokenizer
                    self.ai_engine.knowledge_engine.model_path = llm_model['path']

                    self.ai_engine.translation_engine.model = model_info
                    self.ai_engine.translation_engine.tokenizer = tokenizer
                    self.ai_engine.translation_engine.model_path = llm_model['path']

                    print(f"成功加载LLM模型: {llm_model['name']}")

                    # 如果是CPU模式，打印内存使用情况
                    if "cpu" in str(next(model.parameters()).device):
                        import psutil
                        process = psutil.Process(os.getpid())
                        memory_gb = process.memory_info().rss / 1024 / 1024 / 1024
                        print(f"当前进程内存使用: {memory_gb:.2f} GB")

                    return True
                except Exception as e:
                    print(f"加载LLM模型失败: {e}")
                    import traceback
                    traceback.print_exc()
            else:
                print("未检测到可用的LLM模型")

            # 2. 检测和加载向量模型
            embedding_path = self.settings.get('vector_model_path', os.path.join(base_dir, "BAAI"))
            if not os.path.exists(embedding_path):
                os.makedirs(embedding_path, exist_ok=True)

            # 检测向量模型
            embedding_models = self.model_manager.detect_models(embedding_path, self.model_manager.MODEL_TYPE_EMBEDDING)
            if embedding_models:
                # 选择最优模型
                embedding_model = embedding_models[0]
                print(f"使用现有向量模型: {embedding_model['name']}")

                # 直接使用sentence-transformers加载向量模型
                try:
                    from sentence_transformers import SentenceTransformer
                    import torch

                    # 向量模型强制使用CPU
                    device = "cpu"
                    print(f"将向量模型强制加载到CPU设备")

                    # 加载向量模型到CPU
                    print(f"将向量模型加载到设备: {device}")
                    vector_model = SentenceTransformer(embedding_model['path'], device=device)
                    print(f"成功加载向量模型: {embedding_model['name']} 到 {device}")

                    # 更新向量数据库的模型
                    if hasattr(self, 'vector_db'):
                        self.vector_db.set_model({
                            "name": embedding_model['name'],
                            "path": embedding_model['path'],
                            "model": vector_model,
                            "device": device
                        })

                        # 共享向量模型到术语库
                        if hasattr(self, 'term_vector_db'):
                            self.term_vector_db.model = vector_model
                except Exception as e:
                    print(f"加载向量模型失败: {e}")
                    import traceback
                    traceback.print_exc()
            else:
                print("未检测到向量模型，无法加载")

            return True
        except Exception as e:
            print(f"模型加载过程中出错: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _load_embedding_model(self, model_info):
        """加载向量模型"""
        try:
            model_path = model_info['path']
            print(f"加载向量模型: {model_info['name']} ({model_path})")

            # 根据模型类型采用不同的加载方式
            if "bge-m3" in model_path.lower():
                return self._load_bge_m3_model(model_path)
            else:
                # 通用向量模型加载方式
                from sentence_transformers import SentenceTransformer
                model = SentenceTransformer(model_path)

                # 更新向量数据库的模型
                self.vector_db.set_model({
                    "name": model_info['name'],
                    "path": model_path,
                    "model": model
                })
                return True
        except Exception as e:
            print(f"加载向量模型失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    def ensure_model_files(self, model_id, local_path):
        """确保模型文件完整，如果不完整则从ModelScope下载"""
        try:
            print(f"检查模型 {model_id} 在 {local_path} 的文件完整性...")

            # 检查目录是否存在
            if not os.path.exists(local_path):
                print(f"模型目录不存在: {local_path}")
                os.makedirs(local_path, exist_ok=True)
                print(f"已创建模型目录")

            # modelscope所需的必要文件
            required_files = [
                'config.json',
                'pytorch_model.bin',
                'tokenizer_config.json',
                'tokenizer.json'
            ]

            # 检查文件是否存在
            missing_files = []
            for file in required_files:
                file_path = os.path.join(local_path, file)
                if not os.path.exists(file_path):
                    missing_files.append(file)

            if missing_files:
                print(f"发现缺失文件: {missing_files}")
                print(f"从ModelScope下载模型: {model_id}")
                try:
                    # 使用snapshot_download下载模型
                    downloaded_path = snapshot_download(model_id, cache_dir=os.path.dirname(local_path))
                    print(f"模型下载完成，保存在: {downloaded_path}")

                    # 如果下载的路径与目标路径不同，复制文件
                    if downloaded_path != local_path:
                        import shutil
                        for file in required_files:
                            src = os.path.join(downloaded_path, file)
                            dst = os.path.join(local_path, file)
                            if os.path.exists(src):
                                shutil.copy2(src, dst)
                                print(f"复制文件: {file}")
                except Exception as e:
                    print(f"从ModelScope下载失败: {e}")
                    print("请确保手动下载完整的模型文件并放置在正确的目录中")
            else:
                print("模型文件完整，无需下载")

            return local_path

        except Exception as e:
            print(f"检查/下载模型文件时出错: {e}")
            import traceback
            traceback.print_exc()
            return local_path

    def _load_bge_m3_model(self, model_path):
        """使用FlagEmbedding加载BGE-M3模型"""
        try:
            print(f"使用高级方法加载BGE-M3模型: {model_path}")

            # 检查路径是否存在
            if not os.path.exists(model_path):
                print(f"错误: 模型路径不存在: {model_path}")
                # 尝试其他位置
                possible_paths = [
                    os.path.join(os.path.dirname(os.path.abspath(__file__)), "BAAI", "bge-m3"),
                    os.path.join("BAAI", "bge-m3"),
                    os.path.join("D:", "AI_project", "vllm_模型应用", "BAAI", "bge-m3")
                ]

                for path in possible_paths:
                    if os.path.exists(path):
                        print(f"找到备用模型路径: {path}")
                        model_path = path
                        break
                else:
                    print("无法找到有效的BGE-M3模型路径")
                    return None

            # 检查必要文件
            required_files = ["modules.json", "tokenizer.json", "config.json"]
            missing_files = []
            for file in required_files:
                if not os.path.exists(os.path.join(model_path, file)):
                    missing_files.append(file)

            if missing_files:
                print(f"模型目录中缺少必要文件: {', '.join(missing_files)}")
                return None

            # 向量模型强制使用CPU
            device = "cpu"
            print(f"向量模型强制使用CPU加载，节省GPU资源")

            # 尝试多种加载方法
            model = None

            # 方法1: 使用sentence-transformers加载
            try:
                from sentence_transformers import SentenceTransformer
                print(f"尝试使用SentenceTransformer加载模型到{device}...")
                model = SentenceTransformer(model_path, device=device)
                print("成功使用sentence-transformers加载BGE-M3模型")
            except Exception as e1:
                print(f"SentenceTransformer加载失败: {e1}")

                # 方法2: 尝试安装依赖并重新加载
                try:
                    print('尝试安装sentence-transformers依赖并重新加载...')
                    import subprocess
                    subprocess.run(["pip", "install", "--upgrade", "sentence-transformers"], check=True)
                    from sentence_transformers import SentenceTransformer
                    model = SentenceTransformer(model_path, device=device)
                    print("重新安装依赖后成功加载BGE-M3模型")
                except Exception as e2:
                    print(f"安装依赖并重新加载失败: {e2}")

                    # 方法3: 尝试使用FlagEmbedding
                    try:
                        print('尝试使用FlagEmbedding加载...')
                        try:
                            from FlagEmbedding import BGEM3FlagModel
                            model = BGEM3FlagModel(model_path, device=device)
                            print("成功使用FlagEmbedding加载BGE-M3模型")
                        except ImportError:
                            print('FlagEmbedding未安装，尝试安装...')
                            subprocess.run(["pip", "install", "FlagEmbedding>=1.2.0"], check=True)
                            from FlagEmbedding import BGEM3FlagModel
                            model = BGEM3FlagModel(model_path, device=device)
                            print("安装后成功使用FlagEmbedding加载BGE-M3模型")
                    except Exception as e3:
                        print(f"所有加载方法都失败: {e3}")
                        return None

            # 更新向量数据库的模型
            if hasattr(self, 'vector_db') and model is not None:
                print("正在更新向量数据库模型...")
                success = self.vector_db.set_model({
                    "name": "bge-m3",
                    "path": model_path,
                    "model": model,
                    "device": device
                })

                if success:
                    print("向量数据库模型设置成功")

                    # 同步术语向量数据库
                    if hasattr(self, 'term_vector_db'):
                        print("同步术语向量数据库...")
                        self.term_vector_db.model = model
                else:
                    print("向量数据库模型设置失败")

            # 测试模型是否有效
            if model is not None:
                try:
                    print("测试向量模型...")
                    test_text = "这是一个测试句子"
                    embedding = model.encode(test_text)
                    print(f"向量测试成功，维度: {len(embedding)}")

                    # 重新创建知识库向量
                    if hasattr(self, 'knowledge_base'):
                        print("重新计算知识库向量...")
                        self.knowledge_base.ensure_vectors()
                except Exception as e:
                    print(f"向量模型测试失败: {e}")
                    return None

            return model

        except Exception as e:
            print(f"加载BGE-M3模型失败: {e}")
            import traceback
            traceback.print_exc()
            return None

    def check_dependencies(self):
        """检查必要的依赖库"""
        try:
            import modelscope
            print(f"已安装modelscope库 {modelscope.__version__}")
        except ImportError:
            print("警告: 未安装modelscope库，语音功能将不可用")
            print("请运行: pip install modelscope")

    def run(self):
        """运行应用"""
        self.main_window.show()
        return self.app.exec()

    def shutdown(self):
        """关闭应用，保存配置"""
        self.settings.save()
        self.knowledge_base.save()
        self.term_base.save()

    def chat(self, message, history=None, system_prompt=None):
        """处理聊天请求"""
        try:
            # 创建会话消息列表
            messages = []

            # 添加系统提示
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            elif self.settings.get('system_prompt'):
                messages.append({"role": "system", "content": self.settings.get('system_prompt')})
            else:
                # 默认系统提示
                messages.append({"role": "system", "content": "You are Qwen, created by Alibaba Cloud. You are a helpful assistant."})

            # 添加历史对话
            if history:
                for entry in history:
                    if isinstance(entry, dict) and 'role' in entry and 'content' in entry:
                        messages.append(entry)
                    elif isinstance(entry, list) and len(entry) >= 2:
                        messages.append({"role": "user", "content": entry[0]})
                        messages.append({"role": "assistant", "content": entry[1]})

            # 添加当前消息
            if isinstance(message, dict) and 'role' in message and 'content' in message:
                messages.append(message)
            else:
                messages.append({"role": "user", "content": str(message)})

            # 使用Qwen2.5的聊天模板
            if hasattr(self.ai_engine, 'model') and self.ai_engine.model:
                tokenizer = self.ai_engine.model.get('tokenizer')
                model = self.ai_engine.model.get('model')

                if tokenizer and model:
                    # 确保模型在GPU上
                    device = model.device
                    print(f"模型当前设备: {device}")

                    # 如果模型不在GPU上但GPU可用，则尝试将模型移到GPU
                    if 'cuda' not in str(device) and torch.cuda.is_available():
                        print("检测到模型不在GPU上，正在尝试将模型移至GPU...")
                        try:
                            model = model.to('cuda')
                            print(f"模型已成功移至GPU: {model.device}")
                        except Exception as e:
                            print(f"将模型移至GPU失败: {e}")

                    # 使用apply_chat_template格式化对话
                    text = tokenizer.apply_chat_template(
                        messages,
                        tokenize=False,
                        add_generation_prompt=True
                    )

                    # 转换为模型输入
                    model_inputs = tokenizer([text], return_tensors="pt").to(model.device)

                    # 生成回复
                    generated_ids = model.generate(
                        **model_inputs,
                        max_new_tokens=512
                    )

                    # 提取生成的部分
                    generated_ids = [
                        output_ids[len(input_ids):] for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
                    ]

                    # 解码生成的回复
                    response = tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]

                    return response
                else:
                    # 传统方式生成回复
                    return self.ai_engine.generate_response(messages)
            else:
                # 基础回退方法
                return self.ai_engine.generate_response(messages)

        except Exception as e:
            print(f"AI对话出错: {e}")
            import traceback
            traceback.print_exc()
            return f"抱歉，处理您的请求时出现错误: {str(e)}"

    def chat_with_knowledge(self, message, history=None, system_prompt=None):
        """使用知识库辅助的聊天请求"""
        try:
            # 首先尝试从知识库获取相关信息
            knowledge_text = ""
            if hasattr(self, 'knowledge_base') and self.knowledge_base:
                try:
                    # 搜索相关知识
                    knowledge_results = self.knowledge_base.search(message, top_k=5)
                    if knowledge_results:
                        knowledge_items = []
                        for result in knowledge_results:
                            if isinstance(result, dict):
                                # 处理字典类型的结果
                                content = result.get('content', '')
                                metadata = result.get('metadata', {})

                                # 如果是问答对类型，格式化显示
                                if metadata.get('type') == 'qa_group':
                                    question = metadata.get('question', '')
                                    answer = metadata.get('answer', '')
                                    knowledge_items.append(f"问题：{question}\n答案：{answer}")
                                else:
                                    knowledge_items.append(content)
                            else:
                                # 处理字符串类型的结果
                                knowledge_items.append(str(result))

                        if knowledge_items:
                            knowledge_text = "\n\n".join(knowledge_items[:3])  # 最多使用3个知识条目
                except Exception as e:
                    print(f"知识库搜索失败: {e}")

            # 构建严格的知识库问答消息
            if knowledge_text:
                enhanced_message = f"""请严格按照以下知识库内容回答问题，不要添加任何额外的解释、扩展或补充说明：

知识库内容：
{knowledge_text}

用户问题：{message}

回答要求：
1. 只能基于上述知识库内容回答
2. 不得添加知识库中没有的信息
3. 不得进行推测或扩展说明
4. 如果知识库内容不足以回答问题，请直接说"知识库中没有相关的答案"
5. 回答要简洁准确，直接引用知识库内容

请回答："""
            else:
                enhanced_message = "知识库中没有相关的答案"

            # 调用普通聊天方法
            return self.chat(enhanced_message, history, system_prompt)

        except Exception as e:
            print(f"知识库辅助对话出错: {e}")
            import traceback
            traceback.print_exc()
            # 如果知识库辅助失败，回退到普通对话
            return self.chat(message, history, system_prompt)

    def send_message(self):
        # 在chat方法或相关回复生成方法中，移除语音处理部分
        # 例如以下代码可以被注释掉或删除：
        """
        # 如果语音模式开启，朗读回复
        if getattr(self, 'speech_mode', False) and self.assistant and hasattr(self.assistant, 'tts_engine'):
            try:
                print("准备朗读AI回复...")
                self.assistant.tts_engine.speak_text(reply)
            except Exception as e:
                print(f"朗读AI回复失败: {e}")
        """

    def on_model_download_progress(self, model_id, progress):
        """处理模型下载进度信号"""
        print(f"下载模型 {model_id} 进度: {progress:.1%}")

    def on_model_download_complete(self, model_id):
        """处理模型下载完成信号"""
        print(f"模型 {model_id} 下载完成")

    def on_model_download_error(self, model_id, error_msg):
        """处理模型下载错误信号"""
        print(f"模型 {model_id} 下载失败: {error_msg}")

    def diagnose_term_base(self):
        """诊断术语库系统的问题"""
        print("\n===== 术语库系统诊断 =====")

        # 检查组件是否初始化
        print("1. 检查组件初始化状态:")
        if not hasattr(self, 'term_vector_db'):
            print("  [错误] 术语向量数据库未初始化")
            return False
        else:
            print(f"  [正常] 术语向量数据库已初始化 ({type(self.term_vector_db).__name__})")

        if not hasattr(self, 'term_base'):
            print("  [错误] 术语库组件未初始化")
            return False
        else:
            print(f"  [正常] 术语库组件已初始化 ({type(self.term_base).__name__})")

        # 检查向量模型
        print("\n2. 检查向量模型状态:")
        if not hasattr(self.term_vector_db, 'model') or self.term_vector_db.model is None:
            print("  [警告] 术语向量模型未加载")

            # 检查主向量模型
            if hasattr(self, 'vector_db') and hasattr(self.vector_db, 'model') and self.vector_db.model:
                print("  [修复] 从主向量数据库复制模型")
                self.term_vector_db.model = self.vector_db.model
            else:
                print("  [错误] 主向量模型也未加载，无法执行术语向量化")
                return False
        else:
            print("  [正常] 术语向量模型已加载")

        # 检查文件系统
        print("\n3. 检查术语存储目录:")
        term_path = self.term_base.term_path if hasattr(self.term_base, 'term_path') else 'data/terms'
        term_vector_path = self.term_vector_db.vector_path if hasattr(self.term_vector_db, 'vector_path') else 'data/term_vectors'

        if not os.path.exists(term_path):
            print(f"  [警告] 术语库目录不存在: {term_path}")
            try:
                os.makedirs(term_path)
                print(f"  [修复] 已创建术语库目录: {term_path}")
            except Exception as e:
                print(f"  [错误] 无法创建术语库目录: {e}")
                return False
        else:
            print(f"  [正常] 术语库目录存在: {term_path}")

        if not os.path.exists(term_vector_path):
            print(f"  [警告] 术语向量库目录不存在: {term_vector_path}")
            try:
                os.makedirs(term_vector_path)
                print(f"  [修复] 已创建术语向量库目录: {term_vector_path}")
            except Exception as e:
                print(f"  [错误] 无法创建术语向量库目录: {e}")
                return False
        else:
            print(f"  [正常] 术语向量库目录存在: {term_vector_path}")

        # 检查术语库数据
        print("\n4. 检查术语库数据:")
        if not hasattr(self.term_base, 'terms') or self.term_base.terms is None:
            print("  [错误] 术语库数据结构不存在")

            # 尝试重新初始化
            try:
                self.term_base.terms = {}
                print("  [修复] 已重新初始化空术语库")
            except Exception as e:
                print(f"  [错误] 无法初始化术语库: {e}")
                return False
        else:
            print(f"  [正常] 术语库数据结构已存在，包含 {len(self.term_base.terms)} 个术语")

        # 尝试添加测试术语
        print("\n5. 尝试添加测试术语:")
        try:
            test_term = f"测试术语_{int(time.time())}"
            result = self.term_base.add_term(test_term, "Test Term", "zh", "en")
            if result:
                print(f"  [正常] 成功添加测试术语: {test_term}")

                # 确认术语已添加到内存
                if test_term in self.term_base.terms:
                    print("  [正常] 术语已添加到内存")
                else:
                    print("  [错误] 术语未添加到内存，可能存在数据结构问题")
                    return False

                # 尝试保存
                save_result = self.term_base.save()
                if save_result:
                    print("  [正常] 术语库成功保存")
                else:
                    print("  [错误] 术语库保存失败")
                    return False
            else:
                print("  [错误] 无法添加测试术语")
                return False
        except Exception as e:
            print(f"  [错误] 添加测试术语时出错: {e}")
            import traceback
            traceback.print_exc()
            return False

        print("\n===== 术语库诊断完成 =====")
        print("结论: 术语库系统运行正常，可以正常添加和保存术语")
        return True

    def initialize_term_base(self):
        """初始化术语库"""
        try:
            print("[INFO] 初始化术语库...")

            # 确保术语向量数据库已初始化
            if not hasattr(self, 'term_vector_db'):
                from core.term_vector_db import TermVectorDB
                self.term_vector_db = TermVectorDB(self.settings)
                print("[INFO] 术语向量数据库初始化，路径:", self.term_vector_db.vector_path)

            # 初始化术语库
            from core.term_base import TermBase
            self.term_base = TermBase(self.term_vector_db, self.settings)
            print(f"[INFO] 术语库初始化完成，加载了 {len(self.term_base.terms)} 个术语条目")
            return True

        except Exception as e:
            print(f"[ERROR] 初始化术语库失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    def unload_local_model(self):
        """卸载本地LLM模型以释放GPU资源"""
        try:
            print("[INFO] 开始卸载本地LLM模型...")

            if hasattr(self, 'ai_engine') and self.ai_engine:
                # 卸载AI引擎中的所有模型
                engines_to_clean = ['chat_engine', 'knowledge_engine', 'translation_engine']

                for engine_name in engines_to_clean:
                    if hasattr(self.ai_engine, engine_name):
                        engine = getattr(self.ai_engine, engine_name)
                        if engine and hasattr(engine, 'model') and engine.model:
                            model_info = engine.model

                            if isinstance(model_info, dict):
                                model = model_info.get('model')
                                tokenizer = model_info.get('tokenizer')

                                # 清理模型
                                if model is not None:
                                    try:
                                        if hasattr(model, 'cpu'):
                                            model.cpu()
                                        del model
                                        print(f"[INFO] {engine_name}模型已卸载")
                                    except Exception as e:
                                        print(f"[WARNING] 卸载{engine_name}模型失败: {e}")

                                # 清理tokenizer
                                if tokenizer is not None:
                                    try:
                                        del tokenizer
                                        print(f"[INFO] {engine_name}tokenizer已卸载")
                                    except Exception as e:
                                        print(f"[WARNING] 卸载{engine_name}tokenizer失败: {e}")

                            # 重置模型引用
                            engine.model = None
                            if hasattr(engine, 'tokenizer'):
                                engine.tokenizer = None

                # 清理AI引擎的模型引用
                if hasattr(self.ai_engine, 'model'):
                    self.ai_engine.model = None

            # 强制清理GPU缓存
            try:
                import torch
                if torch.cuda.is_available():
                    # 获取卸载前的显存使用情况
                    allocated_before = torch.cuda.memory_allocated() / (1024**3)
                    print(f"[INFO] 卸载前显存占用: {allocated_before:.2f} GB")

                    # 清理缓存
                    torch.cuda.empty_cache()
                    torch.cuda.synchronize()

                    # 获取卸载后的显存使用情况
                    allocated_after = torch.cuda.memory_allocated() / (1024**3)
                    freed_memory = allocated_before - allocated_after
                    print(f"[INFO] 卸载后显存占用: {allocated_after:.2f} GB")
                    print(f"[INFO] 释放显存: {freed_memory:.2f} GB")
                    print("[INFO] GPU缓存已清理")
            except Exception as e:
                print(f"[WARNING] 清理GPU缓存失败: {e}")

            # 强制垃圾回收
            import gc
            gc.collect()

            print("[INFO] 本地LLM模型卸载完成")
            return True

        except Exception as e:
            print(f"[ERROR] 卸载本地模型失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    def reload_local_model(self):
        """重新加载本地LLM模型"""
        try:
            print("[INFO] 开始重新加载本地LLM模型...")

            # 检查是否已有模型加载
            if (hasattr(self, 'ai_engine') and self.ai_engine and
                hasattr(self.ai_engine, 'chat_engine') and self.ai_engine.chat_engine and
                hasattr(self.ai_engine.chat_engine, 'model') and self.ai_engine.chat_engine.model):
                print("[INFO] 本地模型已经加载，无需重新加载")
                return True

            # 在重新加载前清理GPU缓存
            try:
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                    print("[INFO] 已清理GPU缓存，准备重新加载模型")
            except Exception as e:
                print(f"[WARNING] 清理GPU缓存失败: {e}")

            # 重新加载模型
            success = self._load_models_efficiently()

            if success:
                print("[INFO] 本地LLM模型重新加载成功")
                return True
            else:
                print("[ERROR] 本地LLM模型重新加载失败")
                return False

        except Exception as e:
            print(f"[ERROR] 重新加载本地模型失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    def test_and_load_vector_model(self):
        """手动测试并加载向量模型"""
        print("\n===== 开始手动测试并加载向量模型 =====")

        # 定义可能的模型路径
        current_dir = os.path.dirname(os.path.abspath(__file__))
        possible_paths = [
            os.path.join(current_dir, "BAAI", "bge-m3"),
            os.path.join("BAAI", "bge-m3"),
            os.path.join("D:", "AI_project", "vllm_模型应用", "BAAI", "bge-m3")
        ]

        # 找到有效的模型路径
        valid_path = None
        for path in possible_paths:
            if os.path.exists(path) and os.path.isdir(path):
                # 检查关键文件
                if (os.path.exists(os.path.join(path, "modules.json")) and
                    os.path.exists(os.path.join(path, "tokenizer.json")) and
                    os.path.exists(os.path.join(path, "config.json"))):
                    valid_path = path
                    print(f"找到有效的BGE-M3模型路径: {valid_path}")
                    break

        if not valid_path:
            print("❌ 未找到有效的BGE-M3模型路径")
            return False

        # 尝试直接加载并测试
        try:
            # 设置路径到配置
            self.settings.set('vector_model_path', os.path.dirname(valid_path))

            # 检查依赖
            try:
                import torch
                print(f"PyTorch版本: {torch.__version__}")
                print(f"CUDA是否可用: {torch.cuda.is_available()}")
                device = "cpu"  # 强制使用CPU
                print(f"向量模型将使用CPU设备")
            except ImportError:
                print("未安装PyTorch，尝试安装...")
                import subprocess
                subprocess.run([sys.executable, "-m", "pip", "install", "torch"], check=True)
                import torch
                device = "cpu"  # 强制使用CPU

            # 确保安装sentence-transformers
            try:
                from sentence_transformers import SentenceTransformer
                print("sentence-transformers已安装")
            except ImportError:
                print("安装sentence-transformers...")
                import subprocess
                subprocess.run([sys.executable, "-m", "pip", "install", "sentence-transformers>=2.2.2"], check=True)
                from sentence_transformers import SentenceTransformer

            # 加载模型
            print(f"加载向量模型: {valid_path}")
            model = SentenceTransformer(valid_path, device=device)
            print("✓ 模型加载成功!")

            # 测试编码
            test_text = "这是一个测试句子，用来检查向量模型是否能够正确工作。"
            print(f"测试向量编码: '{test_text}'")
            embedding = model.encode(test_text)
            print(f"✓ 向量编码成功，维度: {len(embedding)}")

            # 初始化向量数据库
            if hasattr(self, 'vector_db'):
                print("更新向量数据库模型...")
                self.vector_db.set_model({
                    "name": "bge-m3",
                    "path": valid_path,
                    "model": model,
                    "device": device
                })

                # 同步术语库向量数据库
                if hasattr(self, 'term_vector_db'):
                    print("同步术语库向量数据库...")
                    self.term_vector_db.model = model

                print("✓ 向量模型已成功应用到向量数据库")
                return True
            else:
                print("❌ 向量数据库未初始化")
                return False

        except Exception as e:
            print(f"❌ 向量模型加载失败: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    assistant = AIAssistant()
    sys.exit(assistant.run())

