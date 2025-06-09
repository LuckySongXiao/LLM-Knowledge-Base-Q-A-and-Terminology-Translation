import logging
from typing import Dict, List, Optional
from langdetect import detect
from .base_engine import BaseEngine
import os

# 配置日志 - 设置为DEBUG级别以显示所有日志
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # 确保DEBUG级别的日志被记录

# 如果没有处理程序，添加一个控制台处理程序
if not logger.handlers:
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

class TranslationEngine(BaseEngine):
    """专业翻译引擎，专门处理文本翻译功能"""

    def __init__(self, settings, term_base=None):
        """初始化翻译引擎"""
        super().__init__(settings)

        # 翻译引擎特定的生成配置
        self.generation_config = {
            "max_new_tokens": 1024,     # 最大生成长度
            "temperature": 0.3,         # 温度参数：非常低的温度确保翻译准确性
            "top_p": 0.6,               # top-p采样：降低采样范围
            "top_k": 20,                # top-k采样：减少选择
            "repetition_penalty": 1.5,  # 重复惩罚：高重复惩罚确保翻译忠实
            "do_sample": False          # 不使用采样：确保翻译结果的确定性
        }

        # 术语库对象
        self.term_base = term_base
        self.terms = {}
        logger.info("初始化翻译引擎，开始加载术语库...")
        self._load_terms()

        logger.info(f"初始化翻译引擎完成")

    def _load_terms(self) -> Dict:
        """加载术语库中的术语"""
        logger.info("===== 开始加载术语库详细诊断 =====")

        # 更详细的术语库对象检查
        logger.info(f"术语库对象: {self.term_base}")
        logger.info(f"术语库类型: {type(self.term_base).__name__ if self.term_base else 'None'}")

        # 检查术语库文件路径
        term_file_path = os.path.join('data', 'terms', 'terms.json')
        if os.path.exists(term_file_path):
            logger.info(f"术语库文件存在: {term_file_path}")
            try:
                # 尝试直接读取术语库文件
                import json
                with open(term_file_path, 'r', encoding='utf-8') as f:
                    file_content = f.read()
                    try:
                        terms_data = json.loads(file_content)
                        terms_count = len(terms_data) if isinstance(terms_data, dict) else 0
                        logger.info(f"成功读取术语库文件，包含 {terms_count} 个术语")
                        if terms_count > 0:
                            logger.info(f"术语库文件内容示例: {list(terms_data.keys())[:5]}")
                    except json.JSONDecodeError as je:
                        logger.error(f"术语库JSON解析错误: {je}")
                        if len(file_content) > 100:
                            logger.error(f"文件内容前100个字符: {file_content[:100]}")
                        else:
                            logger.error(f"文件内容: {file_content}")
            except Exception as e:
                logger.error(f"读取术语库文件失败: {e}")
        else:
            logger.warning(f"术语库文件不存在: {term_file_path}")

        terms = {}
        if self.term_base:
            try:
                logger.info(f"从术语库对象加载术语...")

                # 获取术语库对象中的术语
                if hasattr(self.term_base, 'terms') and self.term_base.terms:
                    terms = self.term_base.terms
                    logger.info(f"成功从术语库对象加载 {len(terms)} 个术语")

                    # 显示一些术语示例
                    if terms:
                        sample_terms = list(terms.keys())[:5] if len(terms) > 5 else list(terms.keys())
                        logger.info(f"术语示例: {sample_terms}")

                        # 显示第一个术语的详细信息
                        if sample_terms:
                            first_term = sample_terms[0]
                            logger.info(f"术语详情示例 '{first_term}': {terms[first_term]}")
                else:
                    logger.warning("术语库对象中没有terms属性或terms为空")
            except Exception as e:
                logger.error(f"从术语库加载术语时出错: {e}")
                import traceback
                logger.error(traceback.format_exc())
        else:
            logger.warning("术语库对象不可用，无法加载术语")

        logger.info(f"===== 术语库加载诊断完成，共 {len(terms)} 条 =====")
        return terms

    def generate_response(self, messages):
        """根据提供的消息生成翻译"""
        try:
            if not messages:
                return "错误：未提供消息"

            # 获取并记录模型类型和设备
            if hasattr(self, 'model') and self.model:
                self.model_type = self.model.__class__.__name__
            else:
                self.model_type = "未加载模型"
                self.device = "未知设备"

            # 记录提交给模型的消息
            logger.info(f"使用模型: {self.model_type}，设备: {self.device}")

            # 准备提示
            prompt = self._prepare_prompt(messages)

            # 根据模型类型处理生成
            if hasattr(self, 'gguf_model') and self.gguf_model:
                # 使用GGUF模型生成回复
                response = self._generate_with_gguf(prompt, self.generation_config)
                return self._clean_response(response)
            elif hasattr(self, 'model') and self.model:
                # 使用transformers模型生成回复
                response = self._generate_with_transformers(prompt, self.generation_config)
                return self._process_response(response)
            else:
                return "错误：模型未加载"

        except Exception as e:
            import traceback
            logger.error(f"生成翻译时出错: {e}")
            traceback.print_exc()
            return f"生成翻译时出错: {str(e)}"

    def translate_text(self, text: str, source_lang: str = None, target_lang: str = 'en', use_termbase: bool = True):
        """
        翻译文本，可选是否使用术语库

        Args:
            text: 要翻译的文本
            source_lang: 源语言，None表示自动检测
            target_lang: 目标语言
            use_termbase: 是否使用术语库

        Returns:
            翻译后的文本
        """
        # 检查输入文本是否为空
        if not text or not text.strip():
            logger.warning("输入文本为空，无法翻译")
            return ""

        # 日志记录开始翻译
        logger.info(f"===== 开始翻译任务 =====")
        logger.info(f"原文: {text[:100]}{'...' if len(text) > 100 else ''}")
        logger.info(f"使用术语库: {use_termbase}")

        # 规范化目标语言代码
        if isinstance(target_lang, bool):
            logger.warning(f"目标语言参数为布尔值 ({target_lang})，使用默认值'en'")
            target_lang = "en"
        elif not isinstance(target_lang, str):
            logger.warning(f"目标语言参数类型错误 ({type(target_lang).__name__})，使用默认值'en'")
            target_lang = "en"
        elif target_lang.lower() in ["中文", "chinese", "zh", "zh-cn", "zh-tw"]:
            target_lang = "zh"
        elif target_lang.lower() in ["英文", "english", "en", "en-us", "en-gb"]:
            target_lang = "en"

        # 自动检测源语言
        if not source_lang:
            try:
                detected_lang = detect(text)
                if detected_lang.lower() in ['zh-cn', 'zh-tw', 'zh']:
                    source_lang = 'zh'
                elif detected_lang.lower() in ['en']:
                    source_lang = 'en'
                else:
                    source_lang = detected_lang
                logger.info(f"自动检测到源语言: {source_lang}")
            except Exception as e:
                logger.warning(f"语言自动检测失败: {str(e)}，使用字符特征判断")
                # 根据文本特征判断
                if any(ord(c) > 127 for c in text):
                    source_lang = 'zh'  # 包含非ASCII字符，可能是中文
                else:
                    source_lang = 'en'  # 默认英文
                logger.info(f"根据字符特征判断源语言为: {source_lang}")

        # 规范化源语言代码
        if isinstance(source_lang, str) and source_lang.lower() in ['zh', 'chinese', '中文', 'zh-cn', 'zh-tw']:
            source_lang = 'zh'
        elif isinstance(source_lang, str) and source_lang.lower() in ['en', 'english', '英文', 'en-us', 'en-gb']:
            source_lang = 'en'

        logger.info(f"翻译方向: {source_lang} -> {target_lang}")

        # 获取术语库
        terms = {}
        if use_termbase:
            # 优先使用传入的术语库
            if hasattr(self, 'term_base') and self.term_base:
                if hasattr(self.term_base, 'terms'):
                    terms = self.term_base.terms

            # 如果术语库对象为空，使用内部术语库
            if not terms and hasattr(self, 'terms'):
                terms = self.terms

            logger.info(f"术语库状态: {'可用' if terms else '为空'}, 包含 {len(terms)} 个术语")

        # 如果使用术语库，查找匹配的术语
        matched_terms = []
        if use_termbase and terms:
            logger.info("===== 开始匹配术语 =====")
            matched_terms = self._find_matching_terms_in_text(text, terms, source_lang, target_lang)

            if matched_terms:
                logger.info(f"===== 成功匹配 {len(matched_terms)} 个术语 =====")
                for idx, term in enumerate(matched_terms, 1):
                    logger.info(f"匹配术语 {idx}: '{term['source']}' => '{term['target']}'")

        # 构建翻译提示，无论是否有术语匹配
        try:
            logger.info("构建翻译提示...")
            prompt = self._build_translation_prompt(text, use_termbase and matched_terms, matched_terms, target_lang)

            # 如果使用术语库，先进行术语替换
            processed_text = text
            if use_termbase and matched_terms:
                logger.info("===== 开始术语替换 =====")
                for term in matched_terms:
                    processed_text = processed_text.replace(term['source'], term['target'])
                logger.info(f"术语替换完成，共替换 {len(matched_terms)} 个术语")

            # 构建极简翻译提示
            prompt = f"请将以下文本翻译成{target_lang}：\n{processed_text}"

            messages = [
                {"role": "system", "content": prompt},
                {"role": "user", "content": processed_text}
            ]

            # 仅进行一次翻译
            logger.info("生成翻译...")
            translation = self.generate_response(messages)

            # 确保结果干净
            translation = self._clean_translation_result(translation)

            logger.info(f"翻译完成，生成了 {len(translation)} 个字符")
            logger.info(f"翻译结果: {translation[:100]}{'...' if len(translation) > 100 else ''}")
            return translation
        except Exception as e:
            logger.error(f"翻译过程中出错: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            raise

    def _find_matching_terms_in_text(self, text: str, terms: Dict, source_lang: str = None, target_lang: str = None):
        """在文本中寻找匹配的术语，返回匹配到的术语列表"""
        logger.info(f"开始术语匹配，文本长度: {len(text)}，术语库大小: {len(terms)}")

        # 检查输入
        if not text or not terms:
            logger.warning("输入文本或术语库为空，无法进行匹配")
            return []

        # 如果未指定源语言，尝试检测
        if not source_lang:
            try:
                source_lang = detect(text)
                logger.info(f"自动检测到源语言: {source_lang}")
            except:
                source_lang = "zh"  # 默认中文
                logger.info(f"语言检测失败，默认使用源语言: {source_lang}")

        # 标准化语言代码
        if source_lang and source_lang.lower() in ['zh-cn', 'zh-tw', 'chinese', '中文']:
            source_lang = 'zh'
        elif source_lang and source_lang.lower() in ['en-us', 'en-gb', 'english', '英文']:
            source_lang = 'en'

        if target_lang and target_lang.lower() in ['zh-cn', 'zh-tw', 'chinese', '中文']:
            target_lang = 'zh'
        elif target_lang and target_lang.lower() in ['en-us', 'en-gb', 'english', '英文']:
            target_lang = 'en'

        matched_terms = []

        # 排序术语列表，优先匹配长术语（避免子字符串问题）
        sorted_term_items = sorted(
            [(k, v) for k, v in terms.items()],
            key=lambda x: len(x[0]),
            reverse=True
        )

        for term_key, term_info in sorted_term_items:
            # 获取源术语和目标术语
            source_term = term_info.get('source_term', term_key)
            target_term = term_info.get('target_term', '')

            # 跳过无效术语
            if not source_term or not target_term:
                continue

            # 简化匹配逻辑：如果源术语在文本中，则认为匹配成功
            if source_term in text:
                logger.info(f"匹配到术语: '{source_term}' => '{target_term}'")
                matched_terms.append({
                    'source': source_term,
                    'target': target_term,
                    'definition': term_info.get('definition', '')
                })

        logger.info(f"术语匹配完成，共匹配到 {len(matched_terms)} 个术语")
        return matched_terms

    def _clean_translation_result(self, text):
        """清理翻译结果，删除不必要的角色前缀等"""
        if not text:
            return ""

        # 移除常见的角色前缀
        prefixes_to_remove = [
            "user:", "User:", "用户:",
            "assistant:", "Assistant:", "助手:",
            "system:", "System:", "系统:",
            "Translation:", "翻译:", "翻译结果:"
        ]

        result = text
        for prefix in prefixes_to_remove:
            if result.startswith(prefix):
                result = result[len(prefix):].strip()

        # 删除结尾可能的引号和多余空白
        result = result.strip('" \t\n')

        return result

    def _code_to_language(self, code):
        """将语言代码转换为语言全名"""
        language_map = {
            'zh': '中文',
            'en': '英文',
            'ja': '日文',
            'ko': '韩文',
            'fr': '法文',
            'de': '德文',
            'es': '西班牙文',
            'ru': '俄文',
            'it': '意大利文',
            'pt': '葡萄牙文'
        }
        return language_map.get(code, code)

    def _build_translation_prompt(self, text, use_termbase, matched_terms, target_lang):
        """构建翻译提示词"""
        # 进行术语替换
        if use_termbase and matched_terms:
            for term in matched_terms:
                text = text.replace(term['source'], term['target'])

        # 构建简洁翻译指令
        prompt = f"Translate the following text accurately, keeping all technical terms unchanged:\n{text}"

        logger.info(f"构建的翻译提示：长度 {len(prompt)} 字符")
        return prompt

    def set_term_base(self, term_base):
        """设置术语库引用"""
        logger.info(f"设置术语库: {term_base}")
        self.term_base = term_base

        # 立即尝试加载术语，验证设置是否成功
        term_count = len(self._load_terms())
        logger.info(f"术语库设置{'成功' if term_count > 0 else '失败'}, 加载了 {term_count} 个术语")
        return term_count > 0

    def translate(self, text: str, source_lang: str = None, target_lang: str = 'en', use_termbase: bool = True):
        """翻译文本的简便方法"""
        return self.translate_text(
            text=text,
            source_lang=source_lang,
            target_lang=target_lang,
            use_termbase=use_termbase
        )

    def _prepare_translation_prompt(self, text: str, target_lang: str, source_lang: str,
                            use_terms: bool = True, terms_dict: Dict = None):
        """准备翻译提示"""
        # 获取语言的全名
        source_lang_full = self._code_to_language(source_lang) or source_lang
        target_lang_full = self._code_to_language(target_lang) or target_lang

        # 基础提示模板
        prompt = f"""你是一个专业的翻译引擎，请将以下{source_lang_full}文本精准翻译为{target_lang_full}。
要翻译的文本：
{text}

要求：
1. 保持翻译的精确性和流畅性
2. 保留原文格式，包括段落、列表和标点符号
3. 直接输出翻译结果，不要添加解释或额外标记"""

        logger.debug(f"生成的翻译提示：\n{prompt}")
        return prompt