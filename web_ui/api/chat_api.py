"""
聊天API模块
提供聊天对话相关的RESTful API接口
"""

from flask import Blueprint, request, jsonify, current_app
import json
import time
import requests
import subprocess
from datetime import datetime

chat_bp = Blueprint('chat', __name__)

# 全局变量存储聊天历史（生产环境应使用数据库）
chat_history = []

# 模型类型常量
MODEL_TYPE_LOCAL = "local"      # 本地模型（当前默认）
MODEL_TYPE_OLLAMA = "ollama"    # Ollama平台模型
MODEL_TYPE_OPENAI = "openai"    # OpenAI兼容API模型

# OpenAI兼容API配置
OPENAI_API_BASE = "http://192.168.100.71:8000/v1"
OPENAI_API_MODELS = ["deepseek-r1-70b"]  # 可用模型列表

# 当前模型状态管理
current_model_type = MODEL_TYPE_LOCAL
local_model_loaded = True  # 标记本地模型是否已加载

def _manage_model_resources(selected_model):
    """管理模型资源，在切换模型时优化GPU使用"""
    global current_model_type, local_model_loaded

    try:
        assistant = current_app.config.get('AI_ASSISTANT')
        if not assistant:
            return

        # 确定新模型类型
        new_model_type = MODEL_TYPE_LOCAL
        if selected_model.startswith('openai_'):
            new_model_type = MODEL_TYPE_OPENAI
        elif selected_model.startswith('ollama_') or selected_model in [model['id'] for model in _detect_ollama_models()]:
            new_model_type = MODEL_TYPE_OLLAMA

        # 如果模型类型没有变化，无需处理
        if new_model_type == current_model_type:
            return

        current_app.logger.info(f"模型切换: {current_model_type} -> {new_model_type}")

        # 如果切换到非本地模型，卸载本地模型以释放GPU资源
        if current_model_type == MODEL_TYPE_LOCAL and new_model_type != MODEL_TYPE_LOCAL:
            if local_model_loaded and hasattr(assistant, 'unload_local_model'):
                current_app.logger.info("卸载本地LLM模型以释放GPU资源")
                assistant.unload_local_model()
                local_model_loaded = False

        # 如果切换回本地模型，重新加载本地模型
        elif current_model_type != MODEL_TYPE_LOCAL and new_model_type == MODEL_TYPE_LOCAL:
            if not local_model_loaded and hasattr(assistant, 'reload_local_model'):
                current_app.logger.info("重新加载本地LLM模型")
                success = assistant.reload_local_model()
                local_model_loaded = success
                if not success:
                    current_app.logger.error("重新加载本地模型失败")

        current_model_type = new_model_type

    except Exception as e:
        current_app.logger.error(f"模型资源管理失败: {e}")

def _process_thinking_chain(response):
    """处理AI回答中的思维链，返回处理后的内容"""
    if not response:
        return response

    import re

    # 检测思维链标签
    think_pattern = r'<think>(.*?)</think>'
    matches = re.findall(think_pattern, response, re.DOTALL)

    if not matches:
        return response

    # 提取思维链内容和纯净回答
    thinking_content = []
    for match in matches:
        thinking_content.append(match.strip())

    # 移除思维链标签，获取纯净回答
    clean_response = re.sub(think_pattern, '', response, flags=re.DOTALL).strip()

    # 构建包含折叠思维链的HTML结构
    if thinking_content:
        thinking_html = ""
        for i, think in enumerate(thinking_content):
            thinking_html += f"""
            <div class="thinking-chain-container" data-thinking-id="{i}">
                <div class="thinking-toggle" onclick="toggleThinking({i})">
                    <i class="fas fa-brain"></i> 思维过程
                    <i class="fas fa-chevron-down toggle-icon"></i>
                </div>
                <div class="thinking-content collapsed" id="thinking-{i}">
                    <div class="thinking-text">{think}</div>
                </div>
            </div>
            """

        # 将思维链插入到回答前面
        processed_response = thinking_html + "\n\n" + clean_response
        return processed_response

    return clean_response

def _detect_ollama_models():
    """检测本地ollama平台的可用模型"""
    try:
        # 尝试调用ollama list命令
        result = subprocess.run(['ollama', 'list'],
                              capture_output=True,
                              text=True,
                              timeout=10)

        if result.returncode == 0:
            models = []
            lines = result.stdout.strip().split('\n')

            # 跳过标题行，解析模型列表
            for line in lines[1:]:
                if line.strip():
                    # 解析模型名称（第一列）
                    parts = line.split()
                    if parts:
                        model_name = parts[0]
                        models.append({
                            'id': model_name,
                            'name': model_name,
                            'type': MODEL_TYPE_OLLAMA,
                            'status': 'available'
                        })

            current_app.logger.info(f"检测到 {len(models)} 个Ollama模型")
            return models
        else:
            current_app.logger.warning(f"Ollama命令执行失败: {result.stderr}")
            return []

    except subprocess.TimeoutExpired:
        current_app.logger.warning("Ollama命令执行超时")
        return []
    except FileNotFoundError:
        current_app.logger.info("未找到Ollama命令，可能未安装")
        return []
    except Exception as e:
        current_app.logger.error(f"检测Ollama模型时出错: {e}")
        return []

def _call_ollama_model(model_name, message, history=None, is_knowledge_query=False):
    """调用Ollama模型进行对话"""
    import time

    # 根据是否为知识库查询设置不同的超时时间
    timeout = 180 if is_knowledge_query else 90  # 知识库查询使用3分钟超时，普通对话使用1.5分钟
    max_retries = 2  # 最大重试次数

    for attempt in range(max_retries + 1):
        try:
            # 构建对话历史
            messages = []
            if history:
                for msg in history:
                    messages.append({
                        'role': msg['role'],
                        'content': msg['content']
                    })

            # 添加当前消息
            messages.append({
                'role': 'user',
                'content': message
            })

            # 调用ollama API
            ollama_url = "http://localhost:11434/api/chat"
            payload = {
                'model': model_name,
                'messages': messages,
                'stream': False
            }

            current_app.logger.info(f"调用Ollama模型 {model_name}，尝试 {attempt + 1}/{max_retries + 1}，超时设置: {timeout}秒")

            response = requests.post(ollama_url, json=payload, timeout=timeout)
            response.raise_for_status()

            result = response.json()
            content = result.get('message', {}).get('content', '抱歉，模型返回了空响应')

            current_app.logger.info(f"Ollama模型调用成功，返回内容长度: {len(content)} 字符")
            return content

        except requests.exceptions.Timeout as e:
            current_app.logger.warning(f"Ollama模型调用超时 (尝试 {attempt + 1}/{max_retries + 1}): {e}")
            if attempt < max_retries:
                wait_time = (attempt + 1) * 2  # 递增等待时间
                current_app.logger.info(f"等待 {wait_time} 秒后重试...")
                time.sleep(wait_time)
                continue
            else:
                return f"Ollama模型调用超时，已重试 {max_retries} 次。请检查模型是否正常运行或尝试使用其他模型。"

        except requests.exceptions.ConnectionError as e:
            current_app.logger.error(f"无法连接到Ollama服务 (尝试 {attempt + 1}/{max_retries + 1}): {e}")
            if attempt < max_retries:
                wait_time = (attempt + 1) * 2
                current_app.logger.info(f"等待 {wait_time} 秒后重试...")
                time.sleep(wait_time)
                continue
            else:
                return "无法连接到Ollama服务，请确保Ollama正在运行并监听端口11434。"

        except requests.exceptions.RequestException as e:
            current_app.logger.error(f"调用Ollama模型失败: {e}")
            return f"调用Ollama模型失败: {str(e)}"
        except Exception as e:
            current_app.logger.error(f"Ollama模型调用出错: {e}")
            return f"模型调用出错: {str(e)}"

def _call_openai_model(model_name, message, history=None):
    """调用OpenAI兼容API模型进行对话"""
    try:
        # 构建对话历史
        messages = []
        if history:
            for msg in history:
                messages.append({
                    'role': msg['role'],
                    'content': msg['content']
                })

        # 添加当前消息
        messages.append({
            'role': 'user',
            'content': message
        })

        # 调用OpenAI兼容API
        api_url = f"{OPENAI_API_BASE}/chat/completions"
        payload = {
            'model': model_name,
            'messages': messages,
            'stream': False
        }

        response = requests.post(api_url,
                               json=payload,
                               headers={'Content-Type': 'application/json'},
                               timeout=60)
        response.raise_for_status()

        result = response.json()
        return result['choices'][0]['message']['content']

    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"调用OpenAI兼容API失败: {e}")
        return f"调用OpenAI兼容API失败: {str(e)}"
    except Exception as e:
        current_app.logger.error(f"OpenAI兼容API调用出错: {e}")
        return f"API调用出错: {str(e)}"

def _generate_knowledge_assisted_response(assistant, user_message, history=None):
    """生成知识库辅助的回答 - 与PC端策略保持一致"""
    try:
        current_app.logger.info(f"使用知识库辅助回答问题: {user_message}")

        # 检查知识库是否可用
        if not hasattr(assistant, 'knowledge_base') or not assistant.knowledge_base:
            current_app.logger.warning("知识库未初始化，回退到普通模式")
            return assistant.chat(message=user_message, history=history)

        # 优先使用PC端的chat_with_knowledge方法（如果存在）
        if hasattr(assistant, 'chat_with_knowledge'):
            current_app.logger.info("使用PC端chat_with_knowledge方法")
            return assistant.chat_with_knowledge(user_message, history)

        # 如果没有chat_with_knowledge方法，使用PC端相同的逻辑
        current_app.logger.info("使用PC端相同的知识库搜索逻辑")

        # 搜索相关知识 - 使用PC端相同的参数
        knowledge_base = assistant.knowledge_base
        knowledge_results = knowledge_base.search(user_message, top_k=5)  # PC端使用top_k=5

        if not knowledge_results or len(knowledge_results) == 0:
            current_app.logger.info("未找到相关知识条目，返回标准回复")
            return "知识库中没有相关的答案"

        # 使用PC端相同的结果处理逻辑
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

        if not knowledge_items:
            current_app.logger.info("知识库搜索结果处理后为空，返回标准回复")
            return "知识库中没有相关的答案"

        # 使用PC端相同的知识文本构建方式
        knowledge_text = "\n\n".join(knowledge_items[:3])  # PC端最多使用3个知识条目

        # 使用严格的知识库问答提示格式
        enhanced_message = f"""请严格按照以下知识库内容回答问题，不要添加任何额外的解释、扩展或补充说明：

知识库内容：
{knowledge_text}

用户问题：{user_message}

回答要求：
1. 只能基于上述知识库内容回答
2. 不得添加知识库中没有的信息
3. 不得进行推测或扩展说明
4. 如果知识库内容不足以回答问题，请直接说"知识库中没有相关的答案"
5. 回答要简洁准确，直接引用知识库内容

请回答："""

        current_app.logger.info("使用PC端相同的提示格式生成回答")
        return assistant.chat(enhanced_message, history)

    except Exception as e:
        current_app.logger.error(f"知识库搜索失败: {e}")
        import traceback
        traceback.print_exc()
        # 出错时回退到普通模式
        return assistant.chat(message=user_message, history=history)

def _process_knowledge_results(results, message):
    """处理知识库搜索结果，提取相关上下文 - 与PC端策略一致"""
    if not results or len(results) == 0:
        try:
            current_app.logger.info("未找到相关知识")
        except:
            print("未找到相关知识")
        return None

    # 提取内容
    knowledge_texts = []
    seen_content = set()  # 避免重复内容

    # 处理搜索结果
    for item in results:
        content = None
        similarity = 1.0  # 默认相似度

        if isinstance(item, str):
            # 如果是字符串，直接使用（可能是条目名称）
            try:
                # 尝试从知识库获取完整内容
                from flask import current_app
                assistant = current_app.config.get('AI_ASSISTANT')
                if assistant and hasattr(assistant, 'knowledge_base'):
                    item_data = assistant.knowledge_base.get_item(item)
                    if item_data:
                        if isinstance(item_data, dict):
                            metadata = item_data.get('metadata', {})
                            if metadata.get('type') == 'qa_group':
                                # 问答对类型
                                question = metadata.get('question', '')
                                answer = metadata.get('answer', '')
                                content = f"问题：{question}\n答案：{answer}"
                            else:
                                content = item_data.get('content', str(item_data))
                        else:
                            content = str(item_data)
                    else:
                        content = item
                else:
                    content = item
            except:
                content = item
        elif isinstance(item, dict):
            # 如果是字典，提取内容和相似度
            content = item.get('content', '')
            similarity = item.get('similarity', 1.0)

            # 处理特殊类型
            metadata = item.get('metadata', {})
            if metadata.get('type') == 'qa_group':
                question = metadata.get('question', '')
                answer = metadata.get('answer', '')
                content = f"问题：{question}\n答案：{answer}"
        else:
            content = str(item)

        if content:
            content = content.strip()
            # 避免重复内容
            content_hash = hash(content)
            if content_hash not in seen_content:
                seen_content.add(content_hash)

                # 根据相似度决定是否加入知识库
                similarity_float = float(similarity)
                if similarity_float >= 0.6:
                    knowledge_texts.append(f"【相关度: {similarity_float:.2f}】\n{content}")
                    try:
                        current_app.logger.debug(f"添加知识片段 (相似度:{similarity_float:.2f}): {content[:100]}...")
                    except:
                        print(f"添加知识片段 (相似度:{similarity_float:.2f}): {content[:100]}...")

    # 合并知识文本
    if knowledge_texts:
        combined_text = "\n\n".join(knowledge_texts[:5])  # 最多使用5个知识条目
        try:
            current_app.logger.debug(f"合并后的知识长度: {len(combined_text)} 字符")
        except:
            print(f"合并后的知识长度: {len(combined_text)} 字符")
        return combined_text
    else:
        return None

def _clean_ai_response(response):
    """清理AI回复中的角色标签和格式前缀 - 与PC端策略一致"""
    if not response:
        return ""

    # 处理特定的输出标签
    special_tags = ["assistantapatite", "solver", "answer", "cerer", "assistant"]
    for tag in special_tags:
        if tag in response:
            parts = response.split(tag, 1)
            if len(parts) > 1:
                response = parts[1].strip()
                current_app.logger.debug(f"已提取{tag}标签后的内容")
                break

    # 处理可能存在的顶层结构
    if "\nuser" in response:
        parts = response.split("\nuser")
        if len(parts) > 1:
            response = parts[-1].strip()

    # 如果开头还有user标记
    if response.startswith("user"):
        response = response[4:].strip()

    # 移除其他可能的前缀
    for prefix in ["AI:", "AI：", "助手:", "助手：", "system"]:
        if response.lower().startswith(prefix.lower()):
            response = response[len(prefix):].strip()

    # 移除可能的引导语
    common_intros = [
        "根据提供的知识",
        "根据给出的信息",
        "根据上述知识",
        "基于提供的知识",
        "基于相关知识"
    ]

    for intro in common_intros:
        if response.startswith(intro):
            # 找到第一个完整的句子结束位置
            pos = response.find("，", len(intro))
            if pos > 0:
                response = response[pos+1:].strip()

    return response.strip()

@chat_bp.route('/send', methods=['POST'])
def send_message():
    """发送聊天消息"""
    try:
        data = request.get_json()
        if not data or 'message' not in data:
            return jsonify({'error': '消息内容不能为空'}), 400

        user_message = data['message'].strip()
        if not user_message:
            return jsonify({'error': '消息内容不能为空'}), 400

        # 获取可选参数
        use_knowledge = data.get('use_knowledge', False)
        use_multi_turn = data.get('use_multi_turn', True)
        selected_model = data.get('selected_model', 'local_default')  # 新增：选择的模型

        # 管理模型资源（GPU优化）
        _manage_model_resources(selected_model)

        # 获取松瓷机电AI助手实例
        assistant = current_app.config.get('AI_ASSISTANT')
        if not assistant and selected_model == 'local_default':
            return jsonify({'error': '松瓷机电AI助手未初始化'}), 500

        # 记录用户消息
        user_msg = {
            'id': len(chat_history) + 1,
            'role': 'user',
            'content': user_message,
            'timestamp': datetime.now().isoformat(),
            'type': 'text'
        }
        chat_history.append(user_msg)

        # 获取历史对话（最近10轮）
        recent_history = []
        if use_multi_turn:
            for msg in chat_history[-20:]:  # 最近20条消息（10轮对话）
                if msg['role'] in ['user', 'assistant']:
                    recent_history.append({
                        'role': msg['role'],
                        'content': msg['content']
                    })

        # 调用松瓷机电AI助手生成回复
        try:
            # 根据选择的模型类型调用不同的API
            if selected_model.startswith('openai_'):
                # OpenAI兼容API模型
                model_name = selected_model.replace('openai_', '')
                if use_knowledge:
                    # 使用知识库辅助的OpenAI模型回答
                    ai_response = _generate_external_model_knowledge_response(assistant, user_message, model_name, 'openai', recent_history[:-1] if len(recent_history) > 1 else None)
                else:
                    ai_response = _call_openai_model(model_name, user_message, recent_history[:-1] if len(recent_history) > 1 else None)
            elif selected_model.startswith('ollama_') or selected_model in [model['id'] for model in _detect_ollama_models()]:
                # Ollama模型
                model_name = selected_model.replace('ollama_', '') if selected_model.startswith('ollama_') else selected_model
                if use_knowledge:
                    # 使用知识库辅助的Ollama模型回答
                    ai_response = _generate_external_model_knowledge_response(assistant, user_message, model_name, 'ollama', recent_history[:-1] if len(recent_history) > 1 else None)
                else:
                    ai_response = _call_ollama_model(model_name, user_message, recent_history[:-1] if len(recent_history) > 1 else None, is_knowledge_query=use_knowledge)
            else:
                # 本地模型（默认）
                if use_knowledge:
                    # 使用知识库辅助回答 - 与PC端策略一致
                    ai_response = _generate_knowledge_assisted_response(assistant, user_message, recent_history[:-1] if len(recent_history) > 1 else None)
                else:
                    # 普通聊天模式
                    ai_response = assistant.chat(
                        message=user_message,
                        history=recent_history[:-1] if len(recent_history) > 1 else None
                    )
        except Exception as e:
            current_app.logger.error(f"AI生成回复失败: {e}")
            ai_response = f"抱歉，处理您的请求时出现错误: {str(e)}"

        # 清理AI回复格式
        ai_response = _clean_ai_response(ai_response)

        # 处理思维链（如果存在）
        ai_response = _process_thinking_chain(ai_response)

        # 记录AI回复
        ai_msg = {
            'id': len(chat_history) + 1,
            'role': 'assistant',
            'content': ai_response,
            'timestamp': datetime.now().isoformat(),
            'type': 'text',
            'knowledge_used': use_knowledge,
            'model_used': selected_model  # 新增：记录使用的模型
        }
        chat_history.append(ai_msg)

        return jsonify({
            'success': True,
            'user_message': user_msg,
            'ai_response': ai_msg,
            'conversation_id': len(chat_history) // 2
        })

    except Exception as e:
        current_app.logger.error(f"发送消息失败: {e}")
        return jsonify({'error': f'发送消息失败: {str(e)}'}), 500

@chat_bp.route('/history', methods=['GET'])
def get_chat_history():
    """获取聊天历史"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)

        # 分页处理
        start = (page - 1) * per_page
        end = start + per_page

        paginated_history = chat_history[start:end]

        return jsonify({
            'success': True,
            'history': paginated_history,
            'total': len(chat_history),
            'page': page,
            'per_page': per_page,
            'has_next': end < len(chat_history),
            'has_prev': start > 0
        })

    except Exception as e:
        current_app.logger.error(f"获取聊天历史失败: {e}")
        return jsonify({'error': f'获取聊天历史失败: {str(e)}'}), 500

@chat_bp.route('/clear', methods=['DELETE'])
def clear_chat_history():
    """清空聊天历史"""
    try:
        global chat_history
        chat_history.clear()

        return jsonify({
            'success': True,
            'message': '聊天历史已清空'
        })

    except Exception as e:
        current_app.logger.error(f"清空聊天历史失败: {e}")
        return jsonify({'error': f'清空聊天历史失败: {str(e)}'}), 500

@chat_bp.route('/export', methods=['GET'])
def export_chat_history():
    """导出聊天历史"""
    try:
        format_type = request.args.get('format', 'json')

        if format_type == 'json':
            return jsonify({
                'success': True,
                'data': chat_history,
                'exported_at': datetime.now().isoformat(),
                'total_messages': len(chat_history)
            })
        elif format_type == 'txt':
            # 生成文本格式
            text_content = "松瓷机电AI助手聊天记录\n"
            text_content += f"导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            text_content += "=" * 50 + "\n\n"

            for msg in chat_history:
                sender = "用户" if msg['role'] == 'user' else "松瓷机电AI助手"
                timestamp = datetime.fromisoformat(msg['timestamp']).strftime('%H:%M:%S')
                text_content += f"[{timestamp}] {sender}: {msg['content']}\n\n"

            return text_content, 200, {
                'Content-Type': 'text/plain; charset=utf-8',
                'Content-Disposition': f'attachment; filename=chat_history_{int(time.time())}.txt'
            }
        else:
            return jsonify({'error': '不支持的导出格式'}), 400

    except Exception as e:
        current_app.logger.error(f"导出聊天历史失败: {e}")
        return jsonify({'error': f'导出聊天历史失败: {str(e)}'}), 500

@chat_bp.route('/models', methods=['GET'])
def get_available_models():
    """获取可用模型列表"""
    try:
        models = []

        # 1. 添加当前本地模型（默认模型）
        assistant = current_app.config.get('AI_ASSISTANT')
        if assistant:
            try:
                # 获取当前模型信息
                current_model_name = "当前本地模型"
                if hasattr(assistant, 'ai_engine') and hasattr(assistant.ai_engine, 'chat_engine'):
                    if hasattr(assistant.ai_engine.chat_engine, 'model_path'):
                        import os
                        model_path = assistant.ai_engine.chat_engine.model_path
                        if model_path:
                            current_model_name = os.path.basename(model_path)

                models.append({
                    'id': 'local_default',
                    'name': current_model_name,
                    'type': MODEL_TYPE_LOCAL,
                    'status': 'active',
                    'description': '当前加载的本地模型'
                })
            except Exception as e:
                current_app.logger.warning(f"获取本地模型信息失败: {e}")
                models.append({
                    'id': 'local_default',
                    'name': '本地模型',
                    'type': MODEL_TYPE_LOCAL,
                    'status': 'active',
                    'description': '当前加载的本地模型'
                })

        # 2. 检测Ollama模型
        ollama_models = _detect_ollama_models()
        models.extend(ollama_models)

        # 3. 添加OpenAI兼容API模型
        for model_name in OPENAI_API_MODELS:
            models.append({
                'id': f'openai_{model_name}',
                'name': model_name,
                'type': MODEL_TYPE_OPENAI,
                'status': 'available',
                'description': f'内网OpenAI兼容API模型'
            })

        return jsonify({
            'success': True,
            'models': models,
            'total': len(models)
        })

    except Exception as e:
        current_app.logger.error(f"获取模型列表失败: {e}")
        return jsonify({'error': f'获取模型列表失败: {str(e)}'}), 500

@chat_bp.route('/status', methods=['GET'])
def get_chat_status():
    """获取聊天状态"""
    try:
        assistant = current_app.config.get('AI_ASSISTANT')

        status = {
            'ai_available': assistant is not None,
            'total_messages': len(chat_history),
            'last_message_time': chat_history[-1]['timestamp'] if chat_history else None,
            'model_info': None
        }

        # 获取模型信息
        if assistant and hasattr(assistant, 'ai_engine'):
            try:
                if hasattr(assistant.ai_engine, 'chat_engine') and hasattr(assistant.ai_engine.chat_engine, 'model'):
                    model_info = assistant.ai_engine.chat_engine.model
                    if model_info:
                        status['model_info'] = {
                            'name': model_info.get('name', 'Unknown'),
                            'type': model_info.get('type', 'Unknown'),
                            'device': model_info.get('device', 'Unknown')
                        }
            except Exception as e:
                current_app.logger.warning(f"获取模型信息失败: {e}")

        return jsonify({
            'success': True,
            'status': status
        })

    except Exception as e:
        current_app.logger.error(f"获取聊天状态失败: {e}")
        return jsonify({'error': f'获取聊天状态失败: {str(e)}'}), 500

@chat_bp.route('/knowledge-qa', methods=['POST'])
def knowledge_qa():
    """专门的知识库问答接口"""
    try:
        data = request.get_json()
        if not data or 'question' not in data:
            return jsonify({'error': '问题内容不能为空'}), 400

        question = data['question'].strip()
        if not question:
            return jsonify({'error': '问题内容不能为空'}), 400

        # 获取配置参数
        assistant = current_app.config.get('AI_ASSISTANT')
        if assistant and hasattr(assistant, 'settings'):
            settings = assistant.settings
            # 检查知识库问答是否启用
            if not settings.get('enable_knowledge', True):
                return jsonify({'error': '知识库问答功能已禁用'}), 400

            # 从配置获取参数，允许请求覆盖
            top_k = data.get('top_k', settings.get('kb_top_k', 15))
            threshold = settings.get('kb_threshold', 0.7)
        else:
            top_k = data.get('top_k', 15)
            threshold = 0.7

        selected_model = data.get('selected_model', 'local_default')  # 新增：选择的模型

        # 管理模型资源（GPU优化）
        _manage_model_resources(selected_model)

        # 获取松瓷机电AI助手实例
        if not assistant and selected_model == 'local_default':
            return jsonify({'error': '松瓷机电AI助手未初始化'}), 500

        # 检查知识库是否可用
        if not hasattr(assistant, 'knowledge_base') or not assistant.knowledge_base:
            return jsonify({'error': '知识库未初始化'}), 500

        start_time = time.time()

        # 使用PC端相同的知识库搜索策略
        knowledge_base = assistant.knowledge_base

        # 根据选择的模型类型使用不同的策略
        if selected_model.startswith('openai_'):
            # OpenAI兼容API模型 - 使用外部模型知识库问答
            model_name = selected_model.replace('openai_', '')
            current_app.logger.info(f"使用OpenAI模型进行知识库问答: {model_name}")
            answer = _generate_external_model_knowledge_response(assistant, question, model_name, 'openai')

            # 清理回答格式
            answer = _clean_ai_response(answer)

            return jsonify({
                'success': True,
                'answer': answer,
                'knowledge_items': [],
                'search_time': time.time() - start_time,
                'question': question,
                'method': 'openai_knowledge_qa'
            })

        elif selected_model.startswith('ollama_') or selected_model in [model['id'] for model in _detect_ollama_models()]:
            # Ollama模型 - 使用外部模型知识库问答
            model_name = selected_model.replace('ollama_', '') if selected_model.startswith('ollama_') else selected_model
            current_app.logger.info(f"使用Ollama模型进行知识库问答: {model_name}")
            answer = _generate_external_model_knowledge_response(assistant, question, model_name, 'ollama')

            # 清理回答格式
            answer = _clean_ai_response(answer)

            return jsonify({
                'success': True,
                'answer': answer,
                'knowledge_items': [],
                'search_time': time.time() - start_time,
                'question': question,
                'method': 'ollama_knowledge_qa'
            })

        # 本地模型 - 优先使用PC端的chat_with_knowledge方法
        elif hasattr(assistant, 'chat_with_knowledge'):
            current_app.logger.info("使用PC端chat_with_knowledge方法进行知识库问答")
            answer = assistant.chat_with_knowledge(question)

            # 提取回答内容（去除可能的格式化前缀）
            if isinstance(answer, str):
                answer = _clean_ai_response(answer)

            return jsonify({
                'success': True,
                'answer': answer,
                'knowledge_items': [],  # PC端方法不返回具体的知识条目
                'search_time': time.time() - start_time,
                'question': question,
                'method': 'pc_chat_with_knowledge'
            })

        # 如果没有PC端方法，使用PC端相同的搜索逻辑
        current_app.logger.info("使用PC端相同的知识库搜索逻辑")
        knowledge_results = knowledge_base.search(question, top_k=5)  # PC端使用top_k=5

        if not knowledge_results or len(knowledge_results) == 0:
            return jsonify({
                'success': True,
                'answer': '知识库中没有相关的答案',
                'knowledge_items': [],
                'search_time': time.time() - start_time,
                'question': question
            })

        # 使用PC端相同的结果处理逻辑
        knowledge_items = []
        for result in knowledge_results:
            if isinstance(result, dict):
                # 处理字典类型的结果
                content = result.get('content', '')
                metadata = result.get('metadata', {})

                # 如果是问答对类型，格式化显示
                if metadata.get('type') == 'qa_group':
                    question_text = metadata.get('question', '')
                    answer_text = metadata.get('answer', '')
                    knowledge_items.append(f"问题：{question_text}\n答案：{answer_text}")
                else:
                    knowledge_items.append(content)
            else:
                # 处理字符串类型的结果
                knowledge_items.append(str(result))

        if not knowledge_items:
            return jsonify({
                'success': True,
                'answer': '知识库中没有相关的答案',
                'knowledge_items': [],
                'search_time': time.time() - start_time,
                'question': question,
                'method': 'pc_fallback'
            })

        # 使用PC端相同的知识文本构建方式
        knowledge_text = "\n\n".join(knowledge_items[:3])  # PC端最多使用3个知识条目

        # 使用严格的知识库问答提示格式
        enhanced_message = f"""请严格按照以下知识库内容回答问题，不要添加任何额外的解释、扩展或补充说明：

知识库内容：
{knowledge_text}

用户问题：{question}

回答要求：
1. 只能基于上述知识库内容回答
2. 不得添加知识库中没有的信息
3. 不得进行推测或扩展说明
4. 如果知识库内容不足以回答问题，请直接说"知识库中没有相关的答案"
5. 回答要简洁准确，直接引用知识库内容

请回答："""

        # 生成回答
        try:
            # 根据选择的模型类型调用不同的API
            if selected_model.startswith('openai_'):
                model_name = selected_model.replace('openai_', '')
                answer = _call_openai_model(model_name, enhanced_message)
            elif selected_model.startswith('ollama_') or selected_model in [model['id'] for model in _detect_ollama_models()]:
                model_name = selected_model.replace('ollama_', '') if selected_model.startswith('ollama_') else selected_model
                answer = _call_ollama_model(model_name, enhanced_message, is_knowledge_query=True)
            else:
                # 本地模型（默认）
                answer = assistant.chat(enhanced_message)
        except Exception as e:
            current_app.logger.error(f"生成知识库回答失败: {e}")
            answer = "生成回答时出现错误，但已找到相关知识条目"

        # 清理回答格式
        answer = _clean_ai_response(answer)

        # 简化知识条目格式化
        formatted_knowledge = []
        for i, item in enumerate(knowledge_items[:5]):  # 最多显示5个条目
            formatted_knowledge.append({
                'id': f"item_{i}",
                'content': item[:200] + '...' if len(item) > 200 else item,
                'type': 'text'
            })

        return jsonify({
            'success': True,
            'answer': answer,
            'knowledge_items': formatted_knowledge,
            'search_time': time.time() - start_time,
            'question': question,
            'total_items': len(formatted_knowledge),
            'model_used': selected_model,
            'method': 'pc_compatible'
        })

    except Exception as e:
        current_app.logger.error(f"知识库问答失败: {e}")
        return jsonify({'error': f'知识库问答失败: {str(e)}'}), 500

def _generate_external_model_knowledge_response(assistant, user_message, model_name, model_type, history=None):
    """使用外部模型生成知识库辅助的回答"""
    try:
        current_app.logger.info(f"使用外部模型 {model_name} ({model_type}) 进行知识库问答")

        # 检查知识库是否可用
        if not hasattr(assistant, 'knowledge_base') or not assistant.knowledge_base:
            current_app.logger.warning("知识库未初始化，回退到普通模式")
            if model_type == 'openai':
                return _call_openai_model(model_name, user_message, history)
            elif model_type == 'ollama':
                return _call_ollama_model(model_name, user_message, history)
            else:
                return "知识库未初始化"

        # 使用PC端相同的简洁搜索策略
        knowledge_base = assistant.knowledge_base

        # PC端相同的搜索参数
        knowledge_results = knowledge_base.search(user_message, top_k=5)
        current_app.logger.info(f"知识库搜索完成，找到 {len(knowledge_results) if knowledge_results else 0} 条结果")

        if not knowledge_results or len(knowledge_results) == 0:
            current_app.logger.info("未找到相关知识条目，返回标准回复")
            return "知识库中没有相关的答案"

        # 使用PC端相同的结果处理逻辑
        knowledge_items = []
        for result in knowledge_results:
            if isinstance(result, dict):
                # 处理字典类型的结果
                content = result.get('content', '')
                metadata = result.get('metadata', {})

                # 如果是问答对类型，格式化显示
                if metadata.get('type') == 'qa_group':
                    question_text = metadata.get('question', '')
                    answer_text = metadata.get('answer', '')
                    knowledge_items.append(f"问题：{question_text}\n答案：{answer_text}")
                else:
                    knowledge_items.append(content)
            else:
                # 处理字符串类型的结果
                knowledge_items.append(str(result))

        if not knowledge_items:
            current_app.logger.info("知识库搜索结果处理后为空，返回标准回复")
            return "知识库中没有相关的答案"

        # 使用PC端相同的知识文本构建方式
        knowledge_text = "\n\n".join(knowledge_items[:3])  # PC端最多使用3个知识条目

        # 使用严格的知识库问答提示格式
        enhanced_message = f"""请严格按照以下知识库内容回答问题，不要添加任何额外的解释、扩展或补充说明：

知识库内容：
{knowledge_text}

用户问题：{user_message}

回答要求：
1. 只能基于上述知识库内容回答
2. 不得添加知识库中没有的信息
3. 不得进行推测或扩展说明
4. 如果知识库内容不足以回答问题，请直接说"知识库中没有相关的答案"
5. 回答要简洁准确，直接引用知识库内容

请回答："""

        # 调用相应的外部模型
        if model_type == 'openai':
            response = _call_openai_model(model_name, enhanced_message, history)
        elif model_type == 'ollama':
            response = _call_ollama_model(model_name, enhanced_message, history, is_knowledge_query=True)
        else:
            response = "不支持的模型类型"

        current_app.logger.info(f"外部模型知识库问答完成，回答长度: {len(response) if response else 0}")
        return response

    except Exception as e:
        current_app.logger.error(f"外部模型知识库问答失败: {e}")
        # 出错时回退到普通模式
        try:
            if model_type == 'openai':
                return _call_openai_model(model_name, user_message, history)
            elif model_type == 'ollama':
                return _call_ollama_model(model_name, user_message, history)
            else:
                return f"知识库问答出错: {str(e)}"
        except:
            return f"知识库问答出错: {str(e)}"

def _extract_keywords(text):
    """提取文本中的关键词"""
    import re

    # 移除标点符号和特殊字符
    cleaned_text = re.sub(r'[^\w\s]', ' ', text)

    # 分词（简单的空格分割）
    words = cleaned_text.split()

    # 过滤停用词和短词
    stop_words = {'的', '了', '在', '是', '我', '你', '他', '她', '它', '们', '这', '那', '有', '没', '不', '要', '会', '能', '可以', '如何', '什么', '怎么', '为什么', '哪里', '什么时候', '谁', '吗', '呢', '吧', '啊', '呀'}

    keywords = []
    for word in words:
        if len(word) >= 2 and word not in stop_words:
            keywords.append(word)

    # 返回前5个关键词
    return keywords[:5]

def _build_knowledge_enhanced_prompt(user_message, knowledge_text, history=None):
    """构建知识库增强的提示词"""
    # 构建对话历史
    history_text = ""
    if history:
        for msg in history[-3:]:  # 只保留最近3轮对话
            role = "用户" if msg['role'] == 'user' else "助手"
            history_text += f"{role}: {msg['content']}\n"
        history_text += "\n"

    # 构建知识库增强提示
    prompt = f"""请基于以下知识库内容和对话历史，严谨准确地回答用户问题。

对话历史：
{history_text}

知识库内容：
{knowledge_text}

用户问题：{user_message}

回答要求：
1. 必须使用Markdown格式组织回答，包括标题、列表、代码块等
2. 回答必须基于提供的知识库内容，确保准确性
3. 如果知识库内容不足以完整回答问题，请明确说明
4. 使用清晰的逻辑结构，分点说明
5. 对于技术性内容，请提供具体的步骤或示例
6. 避免模糊或不确定的表述及猜测性解释，保持严谨性
7. 结合对话历史提供连贯的回答

请开始回答："""

    return prompt
