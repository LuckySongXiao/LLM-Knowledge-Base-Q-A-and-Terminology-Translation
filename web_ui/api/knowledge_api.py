"""
知识库API模块
提供知识库管理相关的RESTful API接口
"""

from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename
import os
import json
from datetime import datetime

knowledge_bp = Blueprint('knowledge', __name__)

def _format_knowledge_item(item_name, item_data):
    """格式化知识条目数据，与PC端保持一致"""
    if isinstance(item_data, dict):
        metadata = item_data.get('metadata', {})

        # 根据不同类型处理显示内容
        if metadata.get('type') == 'qa_group':
            # 问答对类型
            title = metadata.get('question', '未知问题')
            content_preview = metadata.get('answer', '未知答案')
            full_content = f"问题：{title}\n\n答案：{content_preview}"
        elif metadata.get('type') == 'document_chunk':
            # 文档片段类型
            title = metadata.get('title', f"文档片段 {metadata.get('chunk_index', 0) + 1}")
            content_preview = item_data.get('content', '')
            full_content = content_preview
        else:
            # 普通文本类型
            title = item_data.get('title', item_name)
            content_preview = item_data.get('content', '')
            full_content = content_preview

        # 生成预览文本（用于列表显示）
        preview_text = content_preview[:200] + '...' if len(content_preview) > 200 else content_preview

        return {
            'id': item_name,  # 使用条目名称作为ID，与PC端一致
            'title': title,
            'content': preview_text,  # 用于列表预览
            'full_content': full_content,  # 完整内容
            'type': metadata.get('type', 'text'),
            'created_at': metadata.get('imported_at', ''),
            'updated_at': metadata.get('imported_at', ''),
            'tags': item_data.get('tags', []),
            'metadata': metadata
        }
    else:
        # 处理字符串类型的条目
        content_str = str(item_data)
        return {
            'id': item_name,  # 使用条目名称作为ID
            'title': content_str[:50] + '...' if len(content_str) > 50 else content_str,
            'content': content_str[:200] + '...' if len(content_str) > 200 else content_str,
            'full_content': content_str,
            'type': 'text',
            'created_at': '',
            'updated_at': '',
            'tags': [],
            'metadata': {}
        }

@knowledge_bp.route('/items', methods=['GET'])
def get_knowledge_items():
    """获取知识库条目列表"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        search_query = request.args.get('q', '').strip()

        # 获取AI助手实例
        assistant = current_app.config.get('AI_ASSISTANT')
        if not assistant or not hasattr(assistant, 'knowledge_base'):
            return jsonify({'error': '知识库未初始化'}), 500

        knowledge_base = assistant.knowledge_base

        # 获取知识条目 - 直接从knowledge_base.items获取，与PC端一致
        if search_query:
            # 执行搜索，返回条目名称列表
            search_results = knowledge_base.search(search_query, top_k=per_page * 2)
            # 确保搜索结果是条目名称列表
            if search_results and isinstance(search_results[0], str):
                item_names = search_results
            else:
                # 如果搜索返回的不是名称列表，从所有条目中筛选
                all_items = knowledge_base.items if hasattr(knowledge_base, 'items') else {}
                item_names = [name for name in all_items.keys() if search_query.lower() in name.lower()]
        else:
            # 获取所有条目名称
            all_items = knowledge_base.items if hasattr(knowledge_base, 'items') else {}
            item_names = list(all_items.keys())

        # 分页处理
        total_items = len(item_names)
        start = (page - 1) * per_page
        end = start + per_page
        paginated_names = item_names[start:end]

        # 格式化返回数据
        formatted_items = []
        for item_name in paginated_names:
            item_data = knowledge_base.get_item(item_name)
            if item_data:
                formatted_item = _format_knowledge_item(item_name, item_data)
                formatted_items.append(formatted_item)

        return jsonify({
            'success': True,
            'items': formatted_items,
            'total': total_items,
            'page': page,
            'per_page': per_page,
            'has_next': end < total_items,
            'has_prev': start > 0,
            'search_query': search_query
        })

    except Exception as e:
        current_app.logger.error(f"获取知识库条目失败: {e}")
        return jsonify({'error': f'获取知识库条目失败: {str(e)}'}), 500

@knowledge_bp.route('/item/<path:item_id>', methods=['GET'])
def get_knowledge_item_detail(item_id):
    """获取知识库条目详细内容"""
    try:
        # 获取AI助手实例
        assistant = current_app.config.get('AI_ASSISTANT')
        if not assistant or not hasattr(assistant, 'knowledge_base'):
            return jsonify({'error': '知识库未初始化'}), 500

        knowledge_base = assistant.knowledge_base

        # 检查是否是临时结果ID
        if item_id.startswith('temp_result_') or item_id.startswith('dict_result_'):
            # 从搜索缓存中获取临时结果
            if hasattr(knowledge_base, '_search_cache') and item_id in knowledge_base._search_cache:
                cached_result = knowledge_base._search_cache[item_id]
                return jsonify({
                    'success': True,
                    'item': cached_result
                })
            else:
                current_app.logger.warning(f"临时结果已过期: {item_id}")
                return jsonify({'error': '搜索结果已过期，请重新搜索后查看'}), 404

        # 直接使用条目名称获取详细信息，与PC端一致
        item_data = knowledge_base.get_item(item_id)
        if not item_data:
            current_app.logger.warning(f"找不到知识条目: {item_id}")
            return jsonify({'error': '知识条目不存在'}), 404

        # 使用统一的格式化函数
        formatted_item = _format_knowledge_item(item_id, item_data)

        # 为详情页面添加额外信息
        if isinstance(item_data, dict):
            metadata = item_data.get('metadata', {})

            # 添加详细的元数据信息
            if metadata.get('type') == 'qa_group':
                formatted_item.update({
                    'question': metadata.get('question', ''),
                    'answer': metadata.get('answer', ''),
                    'source': metadata.get('source', ''),
                    'imported_at': metadata.get('imported_at', '')
                })
            elif metadata.get('type') == 'document_chunk':
                formatted_item.update({
                    'chunk_index': metadata.get('chunk_index', 0),
                    'source': metadata.get('source', ''),
                    'imported_at': metadata.get('imported_at', '')
                })

        return jsonify({
            'success': True,
            'item': formatted_item
        })

    except Exception as e:
        current_app.logger.error(f"获取知识条目详情失败: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'获取知识条目详情失败: {str(e)}'}), 500

@knowledge_bp.route('/add', methods=['POST'])
def add_knowledge_item():
    """添加知识库条目"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': '请求数据不能为空'}), 400

        title = data.get('title', '').strip()
        content = data.get('content', '').strip()
        tags = data.get('tags', [])
        metadata = data.get('metadata', {})

        if not title or not content:
            return jsonify({'error': '标题和内容不能为空'}), 400

        # 获取AI助手实例
        assistant = current_app.config.get('AI_ASSISTANT')
        if not assistant or not hasattr(assistant, 'knowledge_base'):
            return jsonify({'error': '知识库未初始化'}), 500

        knowledge_base = assistant.knowledge_base

        # 创建知识条目
        item_data = {
            'title': title,
            'content': content,
            'type': 'text',
            'tags': tags if isinstance(tags, list) else [],
            'metadata': metadata if isinstance(metadata, dict) else {},
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }

        # 添加到知识库 - 使用与PC端一致的方法
        success = knowledge_base.add_item(title, item_data['content'], item_data.get('metadata', {}))

        if success:
            # 返回格式化的条目信息
            formatted_item = _format_knowledge_item(title, item_data)
            return jsonify({
                'success': True,
                'message': '知识条目添加成功',
                'item': formatted_item
            })
        else:
            return jsonify({'error': '添加知识条目失败'}), 500

    except Exception as e:
        current_app.logger.error(f"添加知识条目失败: {e}")
        return jsonify({'error': f'添加知识条目失败: {str(e)}'}), 500

@knowledge_bp.route('/update/<path:item_id>', methods=['PUT'])
def update_knowledge_item(item_id):
    """更新知识库条目"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': '请求数据不能为空'}), 400

        # 获取AI助手实例
        assistant = current_app.config.get('AI_ASSISTANT')
        if not assistant or not hasattr(assistant, 'knowledge_base'):
            return jsonify({'error': '知识库未初始化'}), 500

        knowledge_base = assistant.knowledge_base

        # 获取现有条目
        existing_item = knowledge_base.get_item(item_id)
        if not existing_item:
            return jsonify({'error': '知识条目不存在'}), 404

        # 更新数据 - 使用与PC端一致的方法
        new_content = data.get('content', '')
        new_metadata = data.get('metadata', {})

        if isinstance(existing_item, dict):
            # 保留原有元数据，只更新指定字段
            updated_metadata = existing_item.get('metadata', {})
            updated_metadata.update(new_metadata)
            updated_metadata['updated_at'] = datetime.now().isoformat()
        else:
            updated_metadata = new_metadata
            updated_metadata['updated_at'] = datetime.now().isoformat()

        # 使用知识库的update_item方法
        success = knowledge_base.update_item(item_id, new_content, updated_metadata)

        if success:
            # 获取更新后的条目并格式化
            updated_item = knowledge_base.get_item(item_id)
            formatted_item = _format_knowledge_item(item_id, updated_item)

            return jsonify({
                'success': True,
                'message': '知识条目更新成功',
                'item': formatted_item
            })
        else:
            return jsonify({'error': '更新知识条目失败'}), 500

    except Exception as e:
        current_app.logger.error(f"更新知识条目失败: {e}")
        return jsonify({'error': f'更新知识条目失败: {str(e)}'}), 500

@knowledge_bp.route('/delete/<path:item_id>', methods=['DELETE'])
def delete_knowledge_item(item_id):
    """删除知识库条目"""
    try:
        # 获取AI助手实例
        assistant = current_app.config.get('AI_ASSISTANT')
        if not assistant or not hasattr(assistant, 'knowledge_base'):
            return jsonify({'error': '知识库未初始化'}), 500

        knowledge_base = assistant.knowledge_base

        # 检查条目是否存在
        existing_item = knowledge_base.get_item(item_id)
        if not existing_item:
            return jsonify({'error': '知识条目不存在'}), 404

        # 删除条目 - 使用与PC端一致的方法
        success = knowledge_base.delete_item(item_id)

        if success:
            return jsonify({
                'success': True,
                'message': '知识条目删除成功'
            })
        else:
            return jsonify({'error': '删除知识条目失败'}), 500

    except Exception as e:
        current_app.logger.error(f"删除知识条目失败: {e}")
        return jsonify({'error': f'删除知识条目失败: {str(e)}'}), 500

@knowledge_bp.route('/search', methods=['POST'])
def search_knowledge():
    """搜索知识库"""
    try:
        data = request.get_json()
        if not data or 'query' not in data:
            return jsonify({'error': '搜索查询不能为空'}), 400

        query = data['query'].strip()
        limit = data.get('limit', 10)
        threshold = data.get('threshold', 0.7)

        if not query:
            return jsonify({'error': '搜索查询不能为空'}), 400

        # 获取AI助手实例
        assistant = current_app.config.get('AI_ASSISTANT')
        if not assistant or not hasattr(assistant, 'knowledge_base'):
            return jsonify({'error': '知识库未初始化'}), 500

        knowledge_base = assistant.knowledge_base

        # 执行搜索 - 修复参数名称
        results = knowledge_base.search(query, top_k=limit)

        # 格式化搜索结果 - 确保ID有效且可查询
        formatted_results = []
        for i, result in enumerate(results):
            if isinstance(result, dict):
                # 字典类型结果，直接使用
                formatted_result = {
                    'id': result.get('id', f'dict_result_{i}'),
                    'title': result.get('title', result.get('name', '未命名')),
                    'content': result.get('content', ''),
                    'score': result.get('score', 0),
                    'type': result.get('type', 'text'),
                    'tags': result.get('tags', []),
                    'metadata': result.get('metadata', {}),
                    'full_content': result.get('content', '')  # 保存完整内容
                }
            elif isinstance(result, str):
                # 字符串类型结果（知识条目名称）
                item_data = knowledge_base.get_item(result)
                if item_data and isinstance(item_data, dict):
                    metadata = item_data.get('metadata', {})
                    content = item_data.get('content', '')
                    formatted_result = {
                        'id': result,  # 使用条目名称作为ID
                        'title': metadata.get('title', result),
                        'content': content[:200] + '...' if len(content) > 200 else content,
                        'score': 1.0,
                        'type': metadata.get('type', 'text'),
                        'tags': metadata.get('tags', []),
                        'metadata': metadata,
                        'full_content': content,  # 保存完整内容
                        'question': item_data.get('question', ''),  # QA类型的问题
                        'answer': item_data.get('answer', ''),      # QA类型的答案
                        'source': metadata.get('source', ''),
                        'imported_at': metadata.get('imported_at', ''),
                        'chunk_index': metadata.get('chunk_index', 0)
                    }
                else:
                    # 如果无法获取详细信息，创建一个临时结果
                    formatted_result = {
                        'id': f'temp_result_{i}',  # 使用临时ID
                        'title': result[:50] + '...' if len(result) > 50 else result,
                        'content': result,
                        'score': 1.0,
                        'type': 'text',
                        'tags': [],
                        'metadata': {},
                        'full_content': result,
                        'is_temporary': True  # 标记为临时结果
                    }
            else:
                # 其他类型结果
                content = str(result)
                formatted_result = {
                    'id': f'temp_result_{i}',
                    'title': content[:50] + '...' if len(content) > 50 else content,
                    'content': content,
                    'score': 1.0,
                    'type': 'text',
                    'tags': [],
                    'metadata': {},
                    'full_content': content,
                    'is_temporary': True
                }
            formatted_results.append(formatted_result)

        # 缓存搜索结果到知识库对象中，用于后续查看
        if hasattr(knowledge_base, '_search_cache'):
            knowledge_base._search_cache = {}
        else:
            knowledge_base._search_cache = {}

        # 将格式化结果按ID缓存
        for result in formatted_results:
            if result.get('is_temporary') or result['id'].startswith(('temp_result_', 'dict_result_')):
                knowledge_base._search_cache[result['id']] = result

        return jsonify({
            'success': True,
            'results': formatted_results,
            'query': query,
            'total_results': len(formatted_results),
            'search_time': datetime.now().isoformat()
        })

    except Exception as e:
        current_app.logger.error(f"搜索知识库失败: {e}")
        return jsonify({'error': f'搜索知识库失败: {str(e)}'}), 500

@knowledge_bp.route('/upload', methods=['POST'])
def upload_document():
    """上传文档到知识库"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': '没有选择文件'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': '没有选择文件'}), 400

        # 检查文件类型
        allowed_extensions = current_app.config.get('ALLOWED_EXTENSIONS', {'txt', 'pdf', 'doc', 'docx', 'md'})
        if not ('.' in file.filename and file.filename.rsplit('.', 1)[1].lower() in allowed_extensions):
            return jsonify({'error': f'不支持的文件类型，支持的类型: {", ".join(allowed_extensions)}'}), 400

        # 保存文件
        filename = secure_filename(file.filename)
        upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
        os.makedirs(upload_folder, exist_ok=True)
        file_path = os.path.join(upload_folder, filename)
        file.save(file_path)

        # 获取AI助手实例
        assistant = current_app.config.get('AI_ASSISTANT')
        if not assistant or not hasattr(assistant, 'knowledge_base'):
            return jsonify({'error': '知识库未初始化'}), 500

        knowledge_base = assistant.knowledge_base

        # 导入文档到知识库
        try:
            success, message = knowledge_base.import_file(file_path)

            # 清理临时文件
            if os.path.exists(file_path):
                os.remove(file_path)

            if success:
                return jsonify({
                    'success': True,
                    'message': message,
                    'filename': filename
                })
            else:
                return jsonify({'error': message}), 500

        except Exception as e:
            # 清理临时文件
            if os.path.exists(file_path):
                os.remove(file_path)
            raise e

    except Exception as e:
        current_app.logger.error(f"上传文档失败: {e}")
        return jsonify({'error': f'上传文档失败: {str(e)}'}), 500

@knowledge_bp.route('/status', methods=['GET'])
def get_knowledge_status():
    """获取知识库状态"""
    try:
        assistant = current_app.config.get('AI_ASSISTANT')

        status = {
            'knowledge_base_available': False,
            'vector_db_available': False,
            'total_items': 0,
            'vector_model_info': None
        }

        if assistant and hasattr(assistant, 'knowledge_base') and assistant.knowledge_base:
            status['knowledge_base_available'] = True

            # 获取条目数量
            try:
                items = assistant.knowledge_base.list_items()
                status['total_items'] = len(items) if items else 0
            except:
                status['total_items'] = 0

            # 检查向量数据库
            if hasattr(assistant.knowledge_base, 'vector_db') and assistant.knowledge_base.vector_db:
                status['vector_db_available'] = True

                # 获取向量模型信息
                vector_db = assistant.knowledge_base.vector_db
                if hasattr(vector_db, 'model') and vector_db.model:
                    if isinstance(vector_db.model, dict):
                        status['vector_model_info'] = {
                            'name': vector_db.model.get('name', 'Unknown'),
                            'device': vector_db.model.get('device', 'Unknown')
                        }
                    else:
                        status['vector_model_info'] = {
                            'name': 'Loaded',
                            'device': 'Unknown'
                        }

        return jsonify({
            'success': True,
            'status': status
        })

    except Exception as e:
        current_app.logger.error(f"获取知识库状态失败: {e}")
        return jsonify({'error': f'获取知识库状态失败: {str(e)}'}), 500
