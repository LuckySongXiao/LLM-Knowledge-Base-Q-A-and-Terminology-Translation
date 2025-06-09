"""
翻译API模块
提供文本翻译相关的RESTful API接口
"""

from flask import Blueprint, request, jsonify, current_app
from datetime import datetime
import json
import time

translation_bp = Blueprint('translation', __name__)

# 全局变量存储翻译历史（生产环境应使用数据库）
translation_history = []

# 支持的语言列表
SUPPORTED_LANGUAGES = {
    'zh': '中文',
    'en': '英语',
    'ja': '日语',
    'ko': '韩语',
    'fr': '法语',
    'de': '德语',
    'es': '西班牙语',
    'ru': '俄语',
    'it': '意大利语',
    'pt': '葡萄牙语'
}

@translation_bp.route('/translate', methods=['POST'])
def translate_text():
    """执行文本翻译"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': '请求数据不能为空'}), 400

        # 验证必需参数
        source_text = data.get('text', '').strip()
        source_lang = data.get('source_lang', 'auto')
        target_lang = data.get('target_lang', 'zh')
        use_termbase = data.get('use_termbase', True)  # 默认使用术语库
        selected_model = data.get('selected_model', 'local_default')  # 选择的模型

        if not source_text:
            return jsonify({'error': '翻译文本不能为空'}), 400

        if target_lang not in SUPPORTED_LANGUAGES:
            return jsonify({'error': f'不支持的目标语言: {target_lang}'}), 400

        # 获取松瓷机电AI助手实例
        assistant = current_app.config.get('AI_ASSISTANT')
        if not assistant:
            return jsonify({'error': '松瓷机电AI助手未初始化'}), 500

        # 检查翻译器是否可用
        if not hasattr(assistant, 'translator') or not assistant.translator:
            return jsonify({'error': '翻译引擎未初始化'}), 500

        # 术语匹配信息
        matched_terms = []

        try:
            # 如果使用术语库，先进行术语匹配
            if use_termbase and hasattr(assistant, 'term_base') and assistant.term_base:
                try:
                    # 获取术语库
                    terms = {}
                    if hasattr(assistant.term_base, 'terms'):
                        terms = assistant.term_base.terms

                    # 查找匹配的术语 - 使用我们的增强术语匹配逻辑
                    if terms:
                        matched_terms = _find_matching_terms(source_text, terms, source_lang, target_lang)
                        current_app.logger.info(f"找到 {len(matched_terms)} 个匹配术语")
                except Exception as e:
                    current_app.logger.warning(f"术语匹配失败: {e}")

            # 执行翻译 - 根据选择的模型
            placeholder_map = None
            if selected_model == 'local_default':
                # 使用本地模型翻译
                if use_termbase and matched_terms:
                    # 使用占位符策略进行本地翻译
                    processed_text, placeholder_map = _replace_terms_with_placeholders(source_text, matched_terms)

                    if hasattr(assistant.translator, 'translate_text'):
                        temp_result = assistant.translator.translate_text(
                            text=processed_text,
                            source_lang=source_lang,
                            target_lang=target_lang,
                            use_termbase=False  # 关闭内置术语库，使用我们的占位符
                        )
                    else:
                        temp_result = assistant.translator.translate(
                            text=processed_text,
                            source_lang=source_lang,
                            target_lang=target_lang,
                            use_termbase=False  # 关闭内置术语库，使用我们的占位符
                        )

                    # 恢复占位符
                    translation_result = _restore_placeholders(temp_result, placeholder_map)
                else:
                    # 普通翻译
                    if hasattr(assistant.translator, 'translate_text'):
                        translation_result = assistant.translator.translate_text(
                            text=source_text,
                            source_lang=source_lang,
                            target_lang=target_lang,
                            use_termbase=use_termbase
                        )
                    else:
                        translation_result = assistant.translator.translate(
                            text=source_text,
                            source_lang=source_lang,
                            target_lang=target_lang,
                            use_termbase=use_termbase
                        )
            else:
                # 使用外部模型翻译（Ollama或OpenAI）
                result_data = _translate_with_external_model(
                    source_text, source_lang, target_lang, selected_model, use_termbase, matched_terms
                )
                if isinstance(result_data, tuple):
                    translation_result, placeholder_map = result_data
                else:
                    translation_result = result_data

            if not translation_result:
                return jsonify({'error': '翻译失败，请稍后重试'}), 500

            # 翻译质量验证和修复
            current_app.logger.info("开始翻译质量验证...")
            quality_issues = _validate_translation_quality(
                source_text, translation_result, source_lang, target_lang,
                placeholder_map, matched_terms
            )

            if quality_issues:
                current_app.logger.warning(f"发现翻译质量问题: {quality_issues}")
                # 尝试修复问题
                translation_result = _fix_translation_issues(
                    source_text, translation_result, quality_issues,
                    source_lang, target_lang, placeholder_map, matched_terms
                )

                # 再次验证修复结果
                remaining_issues = _validate_translation_quality(
                    source_text, translation_result, source_lang, target_lang,
                    placeholder_map, matched_terms
                )

                if remaining_issues:
                    current_app.logger.warning(f"修复后仍存在问题: {remaining_issues}")
                else:
                    current_app.logger.info("翻译质量问题已修复")
            else:
                current_app.logger.info("翻译质量验证通过")

        except Exception as e:
            current_app.logger.error(f"翻译执行失败: {e}")
            return jsonify({'error': f'翻译执行失败: {str(e)}'}), 500

        # 记录翻译历史
        translation_record = {
            'id': len(translation_history) + 1,
            'source_text': source_text,
            'translated_text': translation_result,
            'source_lang': source_lang,
            'target_lang': target_lang,
            'timestamp': datetime.now().isoformat(),
            'character_count': len(source_text),
            'use_termbase': use_termbase,
            'matched_terms_count': len(matched_terms)
        }
        translation_history.append(translation_record)

        return jsonify({
            'success': True,
            'translation': translation_record,
            'matched_terms': matched_terms,
            'source_language_name': SUPPORTED_LANGUAGES.get(source_lang, source_lang),
            'target_language_name': SUPPORTED_LANGUAGES.get(target_lang, target_lang),
            'quality_check': {
                'issues_found': len(quality_issues) if 'quality_issues' in locals() else 0,
                'issues_fixed': len(quality_issues) - len(remaining_issues) if 'quality_issues' in locals() and 'remaining_issues' in locals() else 0,
                'remaining_issues': remaining_issues if 'remaining_issues' in locals() else []
            }
        })

    except Exception as e:
        current_app.logger.error(f"翻译请求处理失败: {e}")
        return jsonify({'error': f'翻译请求处理失败: {str(e)}'}), 500

@translation_bp.route('/history', methods=['GET'])
def get_translation_history():
    """获取翻译历史"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        source_lang = request.args.get('source_lang')
        target_lang = request.args.get('target_lang')

        # 过滤历史记录
        filtered_history = translation_history
        if source_lang:
            filtered_history = [h for h in filtered_history if h['source_lang'] == source_lang]
        if target_lang:
            filtered_history = [h for h in filtered_history if h['target_lang'] == target_lang]

        # 分页处理
        start = (page - 1) * per_page
        end = start + per_page
        paginated_history = filtered_history[start:end]

        return jsonify({
            'success': True,
            'history': paginated_history,
            'total': len(filtered_history),
            'page': page,
            'per_page': per_page,
            'has_next': end < len(filtered_history),
            'has_prev': start > 0
        })

    except Exception as e:
        current_app.logger.error(f"获取翻译历史失败: {e}")
        return jsonify({'error': f'获取翻译历史失败: {str(e)}'}), 500

@translation_bp.route('/languages', methods=['GET'])
def get_supported_languages():
    """获取支持的语言列表"""
    try:
        return jsonify({
            'success': True,
            'languages': SUPPORTED_LANGUAGES,
            'total_count': len(SUPPORTED_LANGUAGES)
        })

    except Exception as e:
        current_app.logger.error(f"获取语言列表失败: {e}")
        return jsonify({'error': f'获取语言列表失败: {str(e)}'}), 500

@translation_bp.route('/clear_history', methods=['DELETE'])
def clear_translation_history():
    """清空翻译历史"""
    try:
        global translation_history
        translation_history.clear()

        return jsonify({
            'success': True,
            'message': '翻译历史已清空'
        })

    except Exception as e:
        current_app.logger.error(f"清空翻译历史失败: {e}")
        return jsonify({'error': f'清空翻译历史失败: {str(e)}'}), 500

@translation_bp.route('/batch_translate', methods=['POST'])
def batch_translate():
    """批量翻译"""
    try:
        data = request.get_json()
        if not data or 'texts' not in data:
            return jsonify({'error': '请求数据格式错误'}), 400

        texts = data.get('texts', [])
        source_lang = data.get('source_lang', 'auto')
        target_lang = data.get('target_lang', 'zh')

        if not texts or not isinstance(texts, list):
            return jsonify({'error': '翻译文本列表不能为空'}), 400

        if len(texts) > 100:  # 限制批量翻译数量
            return jsonify({'error': '批量翻译最多支持100条文本'}), 400

        # 获取松瓷机电AI助手实例
        assistant = current_app.config.get('AI_ASSISTANT')
        if not assistant or not hasattr(assistant, 'translator'):
            return jsonify({'error': '翻译引擎未初始化'}), 500

        results = []
        failed_count = 0

        for i, text in enumerate(texts):
            try:
                if not text.strip():
                    results.append({
                        'index': i,
                        'source_text': text,
                        'translated_text': '',
                        'success': False,
                        'error': '文本为空'
                    })
                    failed_count += 1
                    continue

                translation_result = assistant.translator.translate(
                    text=text.strip(),
                    source_lang=source_lang,
                    target_lang=target_lang
                )

                results.append({
                    'index': i,
                    'source_text': text,
                    'translated_text': translation_result,
                    'success': True,
                    'error': None
                })

                # 记录到历史
                translation_record = {
                    'id': len(translation_history) + 1,
                    'source_text': text,
                    'translated_text': translation_result,
                    'source_lang': source_lang,
                    'target_lang': target_lang,
                    'timestamp': datetime.now().isoformat(),
                    'character_count': len(text),
                    'batch_id': f"batch_{int(datetime.now().timestamp())}"
                }
                translation_history.append(translation_record)

            except Exception as e:
                current_app.logger.error(f"批量翻译第{i+1}条失败: {e}")
                results.append({
                    'index': i,
                    'source_text': text,
                    'translated_text': '',
                    'success': False,
                    'error': str(e)
                })
                failed_count += 1

        return jsonify({
            'success': True,
            'results': results,
            'total_count': len(texts),
            'success_count': len(texts) - failed_count,
            'failed_count': failed_count,
            'source_language_name': SUPPORTED_LANGUAGES.get(source_lang, source_lang),
            'target_language_name': SUPPORTED_LANGUAGES.get(target_lang, target_lang)
        })

    except Exception as e:
        current_app.logger.error(f"批量翻译失败: {e}")
        return jsonify({'error': f'批量翻译失败: {str(e)}'}), 500

@translation_bp.route('/status', methods=['GET'])
def get_translation_status():
    """获取翻译状态"""
    try:
        assistant = current_app.config.get('AI_ASSISTANT')

        status = {
            'translator_available': False,
            'total_translations': len(translation_history),
            'supported_languages_count': len(SUPPORTED_LANGUAGES),
            'last_translation_time': None
        }

        if assistant and hasattr(assistant, 'translator') and assistant.translator:
            status['translator_available'] = True

        if translation_history:
            status['last_translation_time'] = translation_history[-1]['timestamp']

        return jsonify({
            'success': True,
            'status': status
        })

    except Exception as e:
        current_app.logger.error(f"获取翻译状态失败: {e}")
        return jsonify({'error': f'获取翻译状态失败: {str(e)}'}), 500

@translation_bp.route('/match_terms', methods=['POST'])
def match_terms():
    """匹配文本中的术语"""
    try:
        data = request.get_json()
        if not data or 'text' not in data:
            return jsonify({'error': '文本内容不能为空'}), 400

        text = data['text'].strip()
        source_lang = data.get('source_lang', 'zh')
        target_lang = data.get('target_lang', 'en')

        if not text:
            return jsonify({'error': '文本内容不能为空'}), 400

        # 获取松瓷机电AI助手实例
        assistant = current_app.config.get('AI_ASSISTANT')
        if not assistant or not hasattr(assistant, 'term_base'):
            return jsonify({'error': '术语库未初始化'}), 500

        term_base = assistant.term_base
        matched_terms = []

        try:
            # 获取术语库
            terms = {}
            if hasattr(term_base, 'terms'):
                terms = term_base.terms

            # 查找匹配的术语 - 使用我们的增强术语匹配逻辑
            if terms:
                matched_terms = _find_matching_terms(text, terms, source_lang, target_lang)

            return jsonify({
                'success': True,
                'matched_terms': matched_terms,
                'total_matches': len(matched_terms),
                'text': text,
                'source_lang': source_lang,
                'target_lang': target_lang
            })

        except Exception as e:
            current_app.logger.error(f"术语匹配失败: {e}")
            return jsonify({'error': f'术语匹配失败: {str(e)}'}), 500

    except Exception as e:
        current_app.logger.error(f"术语匹配请求处理失败: {e}")
        return jsonify({'error': f'术语匹配请求处理失败: {str(e)}'}), 500

def _build_translation_prompt(source_text, source_lang, target_lang, use_termbase, matched_terms):
    """构建翻译提示词"""
    # 获取语言全名
    source_lang_name = SUPPORTED_LANGUAGES.get(source_lang, source_lang)
    target_lang_name = SUPPORTED_LANGUAGES.get(target_lang, target_lang)

    # 如果使用术语库且有匹配的术语，使用占位符替换策略
    if use_termbase and matched_terms:
        # 使用占位符替换术语
        processed_text, placeholder_map = _replace_terms_with_placeholders(source_text, matched_terms)

        # 构建翻译提示
        direction_info = f"{source_lang_name} → {target_lang_name}"
        if source_lang == 'en' and target_lang == 'zh':
            direction_info += "（使用反向术语库）"

        # 构建极简翻译提示，避免过度润色
        if source_lang == 'en' and target_lang == 'zh':
            prompt = f"直译为中文，严格按照原文语序，不要改变句子结构，不要添加数量词或额外词汇。保持[T1]、[T2]等占位符格式不变：\n\n{processed_text}\n\n中文："
        elif source_lang == 'zh' and target_lang == 'en':
            prompt = f"Translate to English. Keep [T1], [T2], etc. unchanged:\n\n{processed_text}\n\nEnglish:"
        else:
            prompt = f"Translate to {target_lang_name}. Keep [T1], [T2], etc. unchanged:\n\n{processed_text}\n\nTranslation:"

        return prompt, placeholder_map
    else:
        # 基础翻译提示（极简版，避免过度润色）
        if source_lang == 'en' and target_lang == 'zh':
            prompt = f"直译为中文，严格按照原文语序，不要改变句子结构，不要添加数量词或额外词汇：\n\n{source_text}\n\n中文："
        elif source_lang == 'zh' and target_lang == 'en':
            prompt = f"Translate to English:\n\n{source_text}\n\nEnglish:"
        else:
            prompt = f"Translate to {target_lang_name}:\n\n{source_text}\n\nTranslation:"

        return prompt, None

def _replace_terms_with_placeholders(text, matched_terms):
    """使用固定格式占位符替换术语 - 简化版"""
    placeholder_map = {}
    processed_text = text

    current_app.logger.info(f"开始术语替换，共 {len(matched_terms)} 个术语")

    # 使用固定的简单格式：[T1], [T2], [T3]...
    for i, term in enumerate(matched_terms, 1):
        placeholder = f"[T{i}]"  # 极简格式，避免复杂变形
        source_term = term['source']
        target_term = term['target']

        # 确保术语在文本中存在才进行替换
        if source_term in processed_text:
            processed_text = processed_text.replace(source_term, placeholder)
            placeholder_map[placeholder] = target_term
            current_app.logger.info(f"✓ 替换: '{source_term}' -> '{placeholder}' (目标: '{target_term}')")
        else:
            current_app.logger.warning(f"✗ 术语未找到: '{source_term}'")

    current_app.logger.info(f"术语替换完成，创建 {len(placeholder_map)} 个占位符")
    current_app.logger.info(f"处理后文本: {processed_text}")
    return processed_text, placeholder_map

def _restore_placeholders(translated_text, placeholder_map):
    """恢复占位符为目标术语 - 简化且固定版"""
    if not placeholder_map:
        return translated_text

    result_text = translated_text
    restored_count = 0

    import re

    current_app.logger.info(f"开始恢复占位符，共 {len(placeholder_map)} 个")

    # 第一阶段：精确匹配
    for placeholder, target_term in placeholder_map.items():
        if placeholder in result_text:
            result_text = result_text.replace(placeholder, target_term)
            restored_count += 1
            current_app.logger.info(f"✓ 精确恢复: '{placeholder}' -> '{target_term}'")

    # 第二阶段：处理常见变形（仅限于简单格式）
    for placeholder, target_term in placeholder_map.items():
        if placeholder not in translated_text:  # 只处理未精确匹配的
            # 提取数字 [T1] -> 1
            num_match = re.search(r'T(\d+)', placeholder)
            if num_match:
                num = num_match.group(1)

                # 只处理最常见的几种变形
                simple_variants = [
                    f"[T {num}]",      # 空格变形
                    f"[ T{num} ]",     # 前后空格
                    f"[ T {num} ]",    # 完全空格
                    f"T{num}",         # 无括号
                    f"T {num}",        # 无括号+空格
                    # LaTeX风格变形（英译中常见）
                    f"\\[ T_{num} \\]",    # \[ T_1 \]
                    f"\\( T_{num} \\)",    # \( T_1 \)
                    f"\\[T_{num}\\]",      # \[T_1\]
                    f"\\(T_{num}\\)",      # \(T_1\)
                    f"[ T_{num} ]",        # [ T_1 ]
                    f"( T_{num} )",        # ( T_1 )
                    f"T_{num}",            # T_1
                    f"T _{num}",           # T _1
                    f"T_ {num}",           # T_ 1
                ]

                for variant in simple_variants:
                    if variant in result_text:
                        result_text = result_text.replace(variant, target_term)
                        restored_count += 1
                        current_app.logger.info(f"✓ 变形恢复: '{variant}' -> '{target_term}'")
                        break

    # 第三阶段：强制清理任何残留的占位符格式
    cleanup_patterns = [
        r'\[T\s*\d+\s*\]',     # [T1], [T 1], [ T1 ], [ T 1 ]
        r'T\s*\d+',            # T1, T 1
        r'\[\s*T\s*\d+\s*\]',  # 更宽泛的匹配
        r'\\?\[\s*T_?\s*\d+\s*\\?\]',  # LaTeX风格: \[ T_1 \], [ T_1 ]
        r'\\?\(\s*T_?\s*\d+\s*\\?\)',  # LaTeX风格: \( T_1 \), ( T_1 )
        r'T_\s*\d+',           # T_1, T_ 1
    ]

    for pattern in cleanup_patterns:
        matches = list(re.finditer(pattern, result_text, re.IGNORECASE))
        for match in matches:
            matched_text = match.group()
            # 尝试提取数字并找到对应术语
            num_match = re.search(r'(\d+)', matched_text)
            if num_match:
                num = num_match.group(1)
                target_placeholder = f"[T{num}]"
                if target_placeholder in placeholder_map:
                    target_term = placeholder_map[target_placeholder]
                    result_text = result_text.replace(matched_text, target_term)
                    current_app.logger.info(f"✓ 清理恢复: '{matched_text}' -> '{target_term}'")
                else:
                    # 删除无法匹配的残留
                    result_text = result_text.replace(matched_text, "")
                    current_app.logger.warning(f"⚠ 删除残留: '{matched_text}'")

    # 第四阶段：清理格式和多余内容
    result_text = re.sub(r'\s+', ' ', result_text)  # 合并多余空格
    result_text = re.sub(r'\s*([，。！？；：])\s*', r'\1', result_text)  # 标点前后空格
    result_text = result_text.strip()

    current_app.logger.info(f"占位符恢复完成: {restored_count}/{len(placeholder_map)} 个")
    current_app.logger.info(f"最终结果: {result_text}")

    return result_text


def _validate_translation_quality(original_text, translated_text, source_lang, target_lang, placeholder_map=None, matched_terms=None):
    """验证翻译质量，检查常见问题 - 极简版"""
    issues = []

    current_app.logger.info("开始翻译质量验证（极简版）")

    # 1. 检查占位符残留（仅检查新格式）
    if placeholder_map:
        import re

        # 检查原始占位符是否未恢复
        for placeholder in placeholder_map.keys():
            if placeholder in translated_text:
                issues.append(f"占位符未恢复: {placeholder}")

        # 检查简单的残留格式
        simple_patterns = [
            r'\[T\s*\d+\s*\]',     # [T1], [T 1], [ T1 ]
            r'T\s*\d+',            # T1, T 1
            r'TER\s*M\s*\d+',      # TER M 001
            r'TERMINOLOGY\s*\d+',  # TERMINOLOGY 003
        ]

        for pattern in simple_patterns:
            matches = re.findall(pattern, translated_text, re.IGNORECASE)
            if matches:
                issues.append(f"发现占位符残留: {matches}")

    # 2. 检查翻译是否为空
    if not translated_text.strip():
        issues.append("翻译结果为空")

    # 3. 检查是否包含解释文本
    explanation_indicators = [
        '不过这里的术语可能需要',
        '如果你能提供更多的背景信息',
        '注：',
        '（注：',
        '这里的术语似乎是',
        '请根据具体情境理解',
        '如果这是技术文档的一部分',
        '则可能还需要更多的背景信息',
        '这些名称代表什么内容',
        '并且需要准确的解释'
    ]

    for indicator in explanation_indicators:
        if indicator in translated_text:
            issues.append(f"翻译结果包含解释文本: 包含'{indicator}'")
            break

    current_app.logger.info(f"质量验证完成，发现 {len(issues)} 个问题")
    return issues

def _fix_translation_issues(original_text, translated_text, issues, source_lang, target_lang, placeholder_map=None, matched_terms=None):
    """尝试修复翻译问题"""
    if not issues:
        return translated_text

    current_app.logger.warning(f"检测到翻译问题: {issues}")

    # 尝试基本修复
    fixed_text = translated_text

    # 修复占位符问题 - 使用增强的恢复机制
    if placeholder_map:
        import re
        for placeholder, target_term in placeholder_map.items():
            # 首先尝试精确匹配
            if placeholder in fixed_text:
                fixed_text = fixed_text.replace(placeholder, target_term)
                current_app.logger.info(f"修复占位符: {placeholder} -> {target_term}")
            else:
                # 尝试模糊匹配
                term_number = re.search(r'(\d+)', placeholder)
                if term_number:
                    num = int(term_number.group(1))
                    # 尝试各种可能的格式变化（与主恢复函数保持一致）
                    possible_formats = [
                        f"__TERM_{num:03d}__",
                        f"__TERM_{num}__",
                        f"__ TERM _ {num:03d}__",
                        f"__ TERM _ {num} __",
                        f"__ TERM_{num:03d} __",
                        f"__ TERM_{num} __",
                        f"(__ TERM {num:03d}__)",  # 带括号的变形（英译中常见）
                        f"(__ TERM_{num:03d}__)",
                        f"(__ TERM _ {num:03d}__)",
                        f"(__ TERM _ {num} __)",
                        f"(__ TERMS {num:03d}__)",  # TERMS 复数形式（英译中常见）
                        f"(__ TERMS _ {num:03d}__)",
                        f"(__ TERMS _ {num} __)",
                        f"(__ TERMS {num}__)",
                        f"__ TERMS {num:03d}__",    # 不带括号的TERMS
                        f"__ TERMS _ {num:03d}__",
                        f"__ TERMS _ {num} __",
                        f"__ TERMS {num}__",
                        f"__ TERM _ {num:03d} ___",  # 额外的下划线
                        f"__ TERM _ {num} ___",
                        f"[TERM_{num}]",
                        f"[ TERM_{num} ]",
                        f"[TERM {num}]",
                        f"[ TERM {num} ]",
                        f"TERM_{num}",
                        f"TERM {num}",
                        f"_TERM_{num}_",
                        f"_TERM {num}_"
                    ]

                    found = False
                    for possible_format in possible_formats:
                        if possible_format in fixed_text:
                            fixed_text = fixed_text.replace(possible_format, target_term)
                            current_app.logger.info(f"修复变形占位符: {possible_format} -> {target_term}")
                            found = True
                            break

                    if not found:
                        current_app.logger.warning(f"无法修复占位符: {placeholder} -> {target_term}")

    # 清理术语周围的多余括号（修复阶段）
    if placeholder_map:
        for placeholder, target_term in placeholder_map.items():
            # 简化的括号清理：直接替换 (术语) 为 术语
            pattern = rf'\(\s*{re.escape(target_term)}\s*\)'

            if re.search(pattern, fixed_text):
                fixed_text = re.sub(pattern, target_term, fixed_text)
                current_app.logger.info(f"修复阶段清理术语括号: '({target_term})' -> '{target_term}'")

    # 移除提示词残留
    prompt_indicators = ['翻译结果：', 'Translation:', '译文：', 'Result:', '翻译：']
    for indicator in prompt_indicators:
        if indicator in fixed_text:
            fixed_text = fixed_text.replace(indicator, '').strip()
            current_app.logger.info(f"移除提示词残留: {indicator}")

    # 移除模型添加的解释文本（英译中常见问题）
    normalized_source_lang = _normalize_language_code(source_lang, original_text)
    normalized_target_lang = _normalize_language_code(target_lang, fixed_text)

    if normalized_source_lang == 'en' and normalized_target_lang == 'zh':
        # 查找并移除解释文本
        explanation_patterns = [
            r'。不过这里的术语可能需要.*',  # 从"不过这里的术语"开始到结尾
            r'。如果你能提供更多的背景信息.*',  # 从"如果你能提供"开始到结尾
            r'（注：.*?）',  # 括号内的注释
            r'\(注：.*?\)',  # 英文括号内的注释
            r'注：.*',  # 从"注："开始到结尾
            r'。.*TERMS.*可能是某种.*',  # 包含TERMS解释的句子
            r'。.*这些代码代表的具体内容.*',  # 关于代码的解释
        ]

        for pattern in explanation_patterns:
            if re.search(pattern, fixed_text):
                original_text_for_log = fixed_text
                fixed_text = re.sub(pattern, '', fixed_text)
                if fixed_text != original_text_for_log:
                    current_app.logger.info(f"移除模型解释文本: 使用模式 '{pattern}'")

        # 清理可能的句子片段
        # 如果翻译结果以冒号结尾，可能是不完整的
        if fixed_text.endswith('：') or fixed_text.endswith(':'):
            # 查找最后一个完整句子
            sentences = re.split(r'[。！？]', fixed_text)
            if len(sentences) > 1:
                # 保留除最后一个不完整句子外的所有内容
                fixed_text = '。'.join(sentences[:-1]) + '。'
                current_app.logger.info("移除不完整的句子片段")

        # 清理多余的空格和标点
        fixed_text = re.sub(r'\s+', ' ', fixed_text)
        fixed_text = re.sub(r'。+', '。', fixed_text)
        fixed_text = fixed_text.strip()

    # 如果修复后仍有严重问题，返回错误信息
    remaining_issues = _validate_translation_quality(original_text, fixed_text, source_lang, target_lang, placeholder_map, matched_terms)
    critical_issues = [issue for issue in remaining_issues if any(keyword in issue for keyword in ['占位符未恢复', '翻译结果为空', '与原文相同'])]

    if critical_issues:
        current_app.logger.error(f"翻译修复失败，存在严重问题: {critical_issues}")
        return f"翻译质量检查失败: {'; '.join(critical_issues)}"

    return fixed_text

def _parse_multiple_terms(term_string):
    """解析多个外语术语（用英文逗号分隔）

    Args:
        term_string: 术语字符串，如 "Neck,Crystal neck,Growth neck"

    Returns:
        list: 术语列表，按优先级排序 ["Neck", "Crystal neck", "Growth neck"]
    """
    if not term_string:
        return []

    # 按英文逗号分割并去除空白
    terms = [term.strip() for term in term_string.split(',') if term.strip()]
    return terms

def _create_reverse_term_cache(terms, source_lang, target_lang):
    """创建反向术语库缓存（用于外语→中文翻译）

    术语库结构：
    - 键（key）：中文术语
    - 值（value）：外语术语（支持多个，用逗号分隔）

    反向翻译时：
    - 匹配：外语术语（原术语库的值，支持多个）
    - 替换：中文术语（原术语库的键）
    - 优先级：第一个术语享有最高翻译权限
    """
    reverse_terms = {}

    if not terms:
        return reverse_terms

    current_app.logger.info(f"创建反向术语库缓存: {source_lang} → {target_lang}")

    for chinese_term, term_data in terms.items():  # chinese_term是键（中文）
        if isinstance(term_data, dict):
            metadata = term_data.get('metadata', {})
            # 检查原始术语的语言方向
            original_source_lang = metadata.get('source_lang', 'zh')  # 原始：中文
            original_target_lang = metadata.get('target_lang', 'en')  # 原始：外语

            # 如果当前翻译是外语→中文，且原术语库是中文→外语
            if (source_lang == original_target_lang and target_lang == original_source_lang):
                foreign_term_string = term_data.get('target_term', term_data.get('definition', ''))  # 外语术语字符串
                if foreign_term_string:
                    # 解析多个外语术语
                    foreign_terms = _parse_multiple_terms(foreign_term_string)

                    for i, foreign_term in enumerate(foreign_terms):
                        # 创建反向映射：外语术语（小写作为查找键） → 中文术语
                        reverse_terms[foreign_term.lower()] = {
                            'source_term': foreign_term,      # 在文本中匹配的外语术语
                            'target_term': chinese_term,      # 要替换成的中文术语
                            'definition': chinese_term,
                            'priority': i,                     # 优先级（0最高）
                            'primary_term': foreign_terms[0] if foreign_terms else foreign_term,  # 主要术语（用于恢复）
                            'all_terms': foreign_terms,       # 所有术语
                            'metadata': {
                                'source_lang': source_lang,           # 当前翻译：外语
                                'target_lang': target_lang,           # 当前翻译：中文
                                'original_source_lang': original_source_lang,  # 原始：中文
                                'original_target_lang': original_target_lang   # 原始：外语
                            }
                        }
                        current_app.logger.info(f"反向术语映射: '{foreign_term}' → '{chinese_term}' (优先级: {i})")

    current_app.logger.info(f"反向术语库缓存创建完成，共 {len(reverse_terms)} 个术语")
    return reverse_terms

def _normalize_language_code(lang_code, text_sample=""):
    """规范化语言代码，处理auto检测"""
    if lang_code == 'auto':
        # 简单的语言检测逻辑
        import re
        # 检查是否包含中文字符
        if re.search(r'[\u4e00-\u9fff]', text_sample):
            return 'zh'
        # 检查是否主要是英文字符
        elif re.search(r'^[a-zA-Z\s\.,!?;:\'"-]+$', text_sample.strip()):
            return 'en'
        else:
            # 默认返回中文
            return 'zh'
    return lang_code

def _find_matching_terms(source_text, terms, source_lang, target_lang):
    """查找文本中匹配的术语"""
    matched_terms = []

    if not terms:
        return matched_terms

    # 规范化语言代码
    normalized_source_lang = _normalize_language_code(source_lang, source_text)
    normalized_target_lang = _normalize_language_code(target_lang)

    current_app.logger.info(f"语言规范化: {source_lang} → {normalized_source_lang}, {target_lang} → {normalized_target_lang}")

    # 检查是否需要使用反向术语库
    if normalized_source_lang == 'en' and normalized_target_lang == 'zh':
        # EN→ZH翻译，使用反向术语库
        reverse_terms = _create_reverse_term_cache(terms, normalized_source_lang, normalized_target_lang)
        current_app.logger.info(f"使用反向术语库进行EN→ZH翻译，术语数量: {len(reverse_terms)}")

        # 在反向术语库中查找匹配
        # 反向术语库结构：外语术语(小写) → {source_term: 外语术语, target_term: 中文术语}
        source_text_lower = source_text.lower()
        for foreign_term_lower, term_data in reverse_terms.items():
            # 检查外语术语是否在文本中（不区分大小写）
            if foreign_term_lower in source_text_lower:
                # 获取术语信息
                foreign_term = term_data['source_term']  # 外语术语（原始大小写）
                chinese_term = term_data['target_term']  # 中文术语
                position = source_text_lower.find(foreign_term_lower)

                matched_terms.append({
                    'source': foreign_term,   # 在文本中匹配到的外语术语
                    'target': chinese_term,   # 要替换成的中文术语
                    'position': position,
                    'length': len(foreign_term)
                })
                current_app.logger.info(f"找到反向术语匹配: '{foreign_term}' → '{chinese_term}'")
            else:
                # 尝试更灵活的匹配（处理单词边界）
                import re
                # 创建单词边界匹配模式
                pattern = r'\b' + re.escape(foreign_term_lower) + r'\b'
                match = re.search(pattern, source_text_lower)
                if match:
                    foreign_term = term_data['source_term']
                    chinese_term = term_data['target_term']
                    position = match.start()

                    matched_terms.append({
                        'source': foreign_term,
                        'target': chinese_term,
                        'position': position,
                        'length': len(foreign_term)
                    })
                    current_app.logger.info(f"找到反向术语匹配（单词边界）: '{foreign_term}' → '{chinese_term}'")
    else:
        # 正向翻译（ZH→EN等），使用原始术语库
        current_app.logger.info(f"使用正向术语库进行翻译: {normalized_source_lang} → {normalized_target_lang}")

        for source_term, term_data in terms.items():
            if source_term.lower() in source_text.lower():
                if isinstance(term_data, dict):
                    metadata = term_data.get('metadata', {})
                    # 检查语言匹配（使用规范化后的语言代码）
                    term_source_lang = metadata.get('source_lang', 'zh')
                    term_target_lang = metadata.get('target_lang', 'en')

                    current_app.logger.debug(f"检查术语 '{source_term}': 术语语言 {term_source_lang}→{term_target_lang}, 翻译语言 {normalized_source_lang}→{normalized_target_lang}")

                    if (term_source_lang == normalized_source_lang and term_target_lang == normalized_target_lang):
                        target_term_string = term_data.get('target_term', term_data.get('definition', ''))
                        if target_term_string:
                            # 解析多个外语术语，选择第一个（最高优先级）
                            target_terms = _parse_multiple_terms(target_term_string)
                            primary_target = target_terms[0] if target_terms else target_term_string

                            matched_terms.append({
                                'source': source_term,
                                'target': primary_target,  # 使用最高优先级的术语
                                'all_targets': target_terms,  # 保存所有可选术语
                                'position': source_text.lower().find(source_term.lower()),
                                'length': len(source_term)
                            })
                            current_app.logger.info(f"正向术语匹配: '{source_term}' → '{primary_target}' (备选: {target_terms[1:] if len(target_terms) > 1 else '无'})")
                elif isinstance(term_data, str):
                    # 简单的字符串映射（假设是ZH→EN）
                    if normalized_source_lang == 'zh' and normalized_target_lang == 'en':
                        target_terms = _parse_multiple_terms(term_data)
                        primary_target = target_terms[0] if target_terms else term_data

                        matched_terms.append({
                            'source': source_term,
                            'target': primary_target,
                            'all_targets': target_terms,
                            'position': source_text.lower().find(source_term.lower()),
                            'length': len(source_term)
                        })
                        current_app.logger.info(f"正向术语匹配（简单映射）: '{source_term}' → '{primary_target}'")

    current_app.logger.info(f"术语匹配完成，共匹配到 {len(matched_terms)} 个术语")
    return matched_terms

def _translate_with_external_model(source_text, source_lang, target_lang, selected_model, use_termbase, matched_terms):
    """使用外部模型进行翻译"""
    try:
        # 导入聊天API中的模型调用函数
        from web_ui.api.chat_api import _call_ollama_model, _call_openai_model, _detect_ollama_models

        # 构建翻译提示（可能包含占位符）
        prompt_result = _build_translation_prompt(source_text, source_lang, target_lang, use_termbase, matched_terms)

        if isinstance(prompt_result, tuple):
            translation_prompt, placeholder_map = prompt_result
        else:
            translation_prompt = prompt_result
            placeholder_map = None

        current_app.logger.info(f"使用外部模型翻译: {selected_model}")

        if selected_model.startswith('openai_'):
            # OpenAI兼容API模型
            model_name = selected_model.replace('openai_', '')
            result = _call_openai_model(model_name, translation_prompt)
        elif selected_model.startswith('ollama_') or selected_model in [model['id'] for model in _detect_ollama_models()]:
            # Ollama模型
            model_name = selected_model.replace('ollama_', '') if selected_model.startswith('ollama_') else selected_model
            result = _call_ollama_model(model_name, translation_prompt)
        else:
            current_app.logger.warning(f"未知的模型类型: {selected_model}")
            return None

        # 清理翻译结果
        if result:
            # 移除可能的前缀和后缀
            result = result.strip()
            if result.startswith('"') and result.endswith('"'):
                result = result[1:-1]
            if result.startswith("翻译结果："):
                result = result.replace("翻译结果：", "").strip()

            # 恢复占位符为目标术语
            if placeholder_map:
                result = _restore_placeholders(result, placeholder_map)

        # 返回翻译结果和占位符映射（用于质量验证）
        if placeholder_map:
            return result, placeholder_map
        else:
            return result

    except Exception as e:
        current_app.logger.error(f"外部模型翻译失败: {e}")
        return None
