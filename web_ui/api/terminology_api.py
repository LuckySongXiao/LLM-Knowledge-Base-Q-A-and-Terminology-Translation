"""
术语库API模块
提供术语库管理相关的RESTful API接口
"""

from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename
import os
import json
import csv
from datetime import datetime
from io import StringIO

terminology_bp = Blueprint('terminology', __name__)

@terminology_bp.route('/terms', methods=['GET'])
def get_terms():
    """获取术语列表"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        search_query = request.args.get('q', '').strip()
        source_lang = request.args.get('source_lang', '')
        target_lang = request.args.get('target_lang', '')

        # 获取松瓷机电AI助手实例
        assistant = current_app.config.get('AI_ASSISTANT')
        if not assistant or not hasattr(assistant, 'term_base'):
            return jsonify({'error': '术语库未初始化'}), 500

        term_base = assistant.term_base

        # 获取所有术语
        try:
            all_terms = term_base.terms if hasattr(term_base, 'terms') else {}
        except:
            all_terms = {}

        # 转换为列表格式
        terms_list = []
        for source_term, term_data in all_terms.items():
            if isinstance(term_data, dict):
                metadata = term_data.get('metadata', {})
                term_item = {
                    'id': metadata.get('id', str(hash(source_term))),
                    'source_term': source_term,
                    'target_term': term_data.get('target_term', term_data.get('definition', '')),
                    'source_lang': metadata.get('source_lang', 'zh'),
                    'target_lang': metadata.get('target_lang', 'en'),
                    'type': metadata.get('type', 'term'),
                    'created_at': metadata.get('added_time', ''),
                    'updated_at': metadata.get('updated_time', ''),
                    'category': metadata.get('category', ''),
                    'description': metadata.get('description', ''),
                    'usage_count': metadata.get('usage_count', 0)
                }
            else:
                # 兼容旧格式
                term_item = {
                    'id': str(hash(source_term)),
                    'source_term': source_term,
                    'target_term': str(term_data),
                    'source_lang': 'zh',
                    'target_lang': 'en',
                    'type': 'term',
                    'created_at': '',
                    'updated_at': '',
                    'category': '',
                    'description': '',
                    'usage_count': 0
                }
            terms_list.append(term_item)

        # 过滤术语
        filtered_terms = terms_list
        if search_query:
            filtered_terms = [
                term for term in filtered_terms
                if search_query.lower() in term['source_term'].lower() or
                   search_query.lower() in term['target_term'].lower()
            ]
        if source_lang:
            filtered_terms = [term for term in filtered_terms if term['source_lang'] == source_lang]
        if target_lang:
            filtered_terms = [term for term in filtered_terms if term['target_lang'] == target_lang]

        # 分页处理
        start = (page - 1) * per_page
        end = start + per_page
        paginated_terms = filtered_terms[start:end]

        return jsonify({
            'success': True,
            'terms': paginated_terms,
            'total': len(filtered_terms),
            'page': page,
            'per_page': per_page,
            'has_next': end < len(filtered_terms),
            'has_prev': start > 0,
            'search_query': search_query
        })

    except Exception as e:
        current_app.logger.error(f"获取术语列表失败: {e}")
        return jsonify({'error': f'获取术语列表失败: {str(e)}'}), 500

@terminology_bp.route('/add', methods=['POST'])
def add_term():
    """添加术语条目"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': '请求数据不能为空'}), 400

        source_term = data.get('source_term', '').strip()
        target_term = data.get('target_term', '').strip()
        source_lang = data.get('source_lang', 'zh')
        target_lang = data.get('target_lang', 'en')
        category = data.get('category', '').strip()
        description = data.get('description', '').strip()

        if not source_term or not target_term:
            return jsonify({'error': '源术语和目标术语不能为空'}), 400

        # 获取松瓷机电AI助手实例
        assistant = current_app.config.get('AI_ASSISTANT')
        if not assistant or not hasattr(assistant, 'term_base'):
            return jsonify({'error': '术语库未初始化'}), 500

        term_base = assistant.term_base

        # 检查术语是否已存在
        if hasattr(term_base, 'terms') and source_term in term_base.terms:
            return jsonify({'error': '术语已存在'}), 400

        # 添加术语
        success = term_base.add_term(
            source_term=source_term,
            target_term=target_term,
            source_lang=source_lang,
            target_lang=target_lang
        )

        if success:
            # 如果有额外的元数据，更新术语
            if category or description:
                if hasattr(term_base, 'terms') and source_term in term_base.terms:
                    term_data = term_base.terms[source_term]
                    if isinstance(term_data, dict) and 'metadata' in term_data:
                        term_data['metadata']['category'] = category
                        term_data['metadata']['description'] = description
                        term_data['metadata']['updated_time'] = datetime.now().isoformat()
                        term_base.save()

            return jsonify({
                'success': True,
                'message': '术语添加成功',
                'term': {
                    'source_term': source_term,
                    'target_term': target_term,
                    'source_lang': source_lang,
                    'target_lang': target_lang,
                    'category': category,
                    'description': description
                }
            })
        else:
            return jsonify({'error': '添加术语失败'}), 500

    except Exception as e:
        current_app.logger.error(f"添加术语失败: {e}")
        return jsonify({'error': f'添加术语失败: {str(e)}'}), 500

@terminology_bp.route('/update/<term_id>', methods=['PUT'])
def update_term(term_id):
    """更新术语条目"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': '请求数据不能为空'}), 400

        # 获取松瓷机电AI助手实例
        assistant = current_app.config.get('AI_ASSISTANT')
        if not assistant or not hasattr(assistant, 'term_base'):
            return jsonify({'error': '术语库未初始化'}), 500

        term_base = assistant.term_base

        # 查找要更新的术语
        target_source_term = None
        if hasattr(term_base, 'terms'):
            for source_term, term_data in term_base.terms.items():
                if isinstance(term_data, dict):
                    metadata = term_data.get('metadata', {})
                    if metadata.get('id') == term_id or str(hash(source_term)) == term_id:
                        target_source_term = source_term
                        break

        if not target_source_term:
            return jsonify({'error': '术语不存在'}), 404

        # 更新术语数据
        term_data = term_base.terms[target_source_term]
        if isinstance(term_data, dict):
            # 更新基本信息
            if 'target_term' in data:
                term_data['target_term'] = data['target_term']
                term_data['definition'] = data['target_term']  # 兼容旧版

            # 更新元数据
            metadata = term_data.get('metadata', {})
            if 'source_lang' in data:
                metadata['source_lang'] = data['source_lang']
            if 'target_lang' in data:
                metadata['target_lang'] = data['target_lang']
            if 'category' in data:
                metadata['category'] = data['category']
            if 'description' in data:
                metadata['description'] = data['description']

            metadata['updated_time'] = datetime.now().isoformat()
            term_data['metadata'] = metadata

            # 保存更新
            success = term_base.save()

            if success:
                return jsonify({
                    'success': True,
                    'message': '术语更新成功',
                    'term': {
                        'id': term_id,
                        'source_term': target_source_term,
                        'target_term': term_data.get('target_term', ''),
                        'source_lang': metadata.get('source_lang', 'zh'),
                        'target_lang': metadata.get('target_lang', 'en'),
                        'category': metadata.get('category', ''),
                        'description': metadata.get('description', '')
                    }
                })
            else:
                return jsonify({'error': '保存术语失败'}), 500
        else:
            return jsonify({'error': '术语数据格式错误'}), 500

    except Exception as e:
        current_app.logger.error(f"更新术语失败: {e}")
        return jsonify({'error': f'更新术语失败: {str(e)}'}), 500

@terminology_bp.route('/delete/<term_id>', methods=['DELETE'])
def delete_term(term_id):
    """删除术语条目"""
    try:
        # 获取松瓷机电AI助手实例
        assistant = current_app.config.get('AI_ASSISTANT')
        if not assistant or not hasattr(assistant, 'term_base'):
            return jsonify({'error': '术语库未初始化'}), 500

        term_base = assistant.term_base

        # 查找要删除的术语
        target_source_term = None
        if hasattr(term_base, 'terms'):
            for source_term, term_data in term_base.terms.items():
                if isinstance(term_data, dict):
                    metadata = term_data.get('metadata', {})
                    if metadata.get('id') == term_id or str(hash(source_term)) == term_id:
                        target_source_term = source_term
                        break

        if not target_source_term:
            return jsonify({'error': '术语不存在'}), 404

        # 删除术语
        del term_base.terms[target_source_term]
        success = term_base.save()

        if success:
            return jsonify({
                'success': True,
                'message': '术语删除成功'
            })
        else:
            return jsonify({'error': '删除术语失败'}), 500

    except Exception as e:
        current_app.logger.error(f"删除术语失败: {e}")
        return jsonify({'error': f'删除术语失败: {str(e)}'}), 500

@terminology_bp.route('/search', methods=['POST'])
def search_terms():
    """搜索术语"""
    try:
        data = request.get_json()
        if not data or 'query' not in data:
            return jsonify({'error': '搜索查询不能为空'}), 400

        query = data['query'].strip()
        source_lang = data.get('source_lang', '')
        target_lang = data.get('target_lang', '')
        limit = data.get('limit', 20)

        if not query:
            return jsonify({'error': '搜索查询不能为空'}), 400

        # 获取松瓷机电AI助手实例
        assistant = current_app.config.get('AI_ASSISTANT')
        if not assistant or not hasattr(assistant, 'term_base'):
            return jsonify({'error': '术语库未初始化'}), 500

        term_base = assistant.term_base

        # 执行搜索
        results = []
        if hasattr(term_base, 'terms'):
            for source_term, term_data in term_base.terms.items():
                # 检查是否匹配搜索条件
                if query.lower() in source_term.lower():
                    score = 1.0
                elif isinstance(term_data, dict):
                    target_term = term_data.get('target_term', term_data.get('definition', ''))
                    if query.lower() in target_term.lower():
                        score = 0.8
                    else:
                        continue
                else:
                    if query.lower() in str(term_data).lower():
                        score = 0.8
                    else:
                        continue

                # 检查语言过滤
                if isinstance(term_data, dict):
                    metadata = term_data.get('metadata', {})
                    if source_lang and metadata.get('source_lang') != source_lang:
                        continue
                    if target_lang and metadata.get('target_lang') != target_lang:
                        continue

                    result = {
                        'id': metadata.get('id', str(hash(source_term))),
                        'source_term': source_term,
                        'target_term': term_data.get('target_term', term_data.get('definition', '')),
                        'source_lang': metadata.get('source_lang', 'zh'),
                        'target_lang': metadata.get('target_lang', 'en'),
                        'score': score,
                        'category': metadata.get('category', ''),
                        'description': metadata.get('description', '')
                    }
                else:
                    result = {
                        'id': str(hash(source_term)),
                        'source_term': source_term,
                        'target_term': str(term_data),
                        'source_lang': 'zh',
                        'target_lang': 'en',
                        'score': score,
                        'category': '',
                        'description': ''
                    }

                results.append(result)

        # 按分数排序并限制结果数量
        results.sort(key=lambda x: x['score'], reverse=True)
        results = results[:limit]

        return jsonify({
            'success': True,
            'results': results,
            'query': query,
            'total_results': len(results),
            'search_time': datetime.now().isoformat()
        })

    except Exception as e:
        current_app.logger.error(f"搜索术语失败: {e}")
        return jsonify({'error': f'搜索术语失败: {str(e)}'}), 500

@terminology_bp.route('/import', methods=['POST'])
def import_terms():
    """导入术语库"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': '没有选择文件'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': '没有选择文件'}), 400

        # 检查文件类型
        allowed_extensions = {'csv', 'json', 'txt'}
        file_ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
        if file_ext not in allowed_extensions:
            return jsonify({'error': f'不支持的文件类型，支持的类型: {", ".join(allowed_extensions)}'}), 400

        # 获取松瓷机电AI助手实例
        assistant = current_app.config.get('AI_ASSISTANT')
        if not assistant or not hasattr(assistant, 'term_base'):
            return jsonify({'error': '术语库未初始化'}), 500

        term_base = assistant.term_base

        # 读取文件内容
        file_content = file.read().decode('utf-8')
        imported_count = 0
        failed_count = 0
        errors = []

        try:
            if file_ext == 'csv':
                # 处理CSV文件
                csv_reader = csv.DictReader(StringIO(file_content))
                for row_num, row in enumerate(csv_reader, 1):
                    try:
                        source_term = row.get('source_term', '').strip()
                        target_term = row.get('target_term', '').strip()
                        source_lang = row.get('source_lang', 'zh')
                        target_lang = row.get('target_lang', 'en')

                        if source_term and target_term:
                            success = term_base.add_term(
                                source_term=source_term,
                                target_term=target_term,
                                source_lang=source_lang,
                                target_lang=target_lang
                            )
                            if success:
                                imported_count += 1
                            else:
                                failed_count += 1
                                errors.append(f"第{row_num}行: 添加术语失败")
                        else:
                            failed_count += 1
                            errors.append(f"第{row_num}行: 源术语或目标术语为空")
                    except Exception as e:
                        failed_count += 1
                        errors.append(f"第{row_num}行: {str(e)}")

            elif file_ext == 'json':
                # 处理JSON文件
                data = json.loads(file_content)
                if isinstance(data, list):
                    for idx, item in enumerate(data, 1):
                        try:
                            source_term = item.get('source_term', '').strip()
                            target_term = item.get('target_term', '').strip()
                            source_lang = item.get('source_lang', 'zh')
                            target_lang = item.get('target_lang', 'en')

                            if source_term and target_term:
                                success = term_base.add_term(
                                    source_term=source_term,
                                    target_term=target_term,
                                    source_lang=source_lang,
                                    target_lang=target_lang
                                )
                                if success:
                                    imported_count += 1
                                else:
                                    failed_count += 1
                                    errors.append(f"第{idx}项: 添加术语失败")
                            else:
                                failed_count += 1
                                errors.append(f"第{idx}项: 源术语或目标术语为空")
                        except Exception as e:
                            failed_count += 1
                            errors.append(f"第{idx}项: {str(e)}")
                elif isinstance(data, dict):
                    # 处理字典格式
                    for source_term, target_term in data.items():
                        try:
                            if source_term and target_term:
                                success = term_base.add_term(
                                    source_term=source_term,
                                    target_term=str(target_term),
                                    source_lang='zh',
                                    target_lang='en'
                                )
                                if success:
                                    imported_count += 1
                                else:
                                    failed_count += 1
                                    errors.append(f"术语'{source_term}': 添加失败")
                            else:
                                failed_count += 1
                                errors.append(f"术语'{source_term}': 源术语或目标术语为空")
                        except Exception as e:
                            failed_count += 1
                            errors.append(f"术语'{source_term}': {str(e)}")

            elif file_ext == 'txt':
                # 处理文本文件（每行一个术语对，用制表符或逗号分隔）
                lines = file_content.strip().split('\n')
                for line_num, line in enumerate(lines, 1):
                    try:
                        line = line.strip()
                        if not line:
                            continue

                        # 尝试用制表符分隔
                        if '\t' in line:
                            parts = line.split('\t', 1)
                        # 尝试用逗号分隔
                        elif ',' in line:
                            parts = line.split(',', 1)
                        else:
                            failed_count += 1
                            errors.append(f"第{line_num}行: 格式错误，需要用制表符或逗号分隔")
                            continue

                        if len(parts) >= 2:
                            source_term = parts[0].strip()
                            target_term = parts[1].strip()

                            if source_term and target_term:
                                success = term_base.add_term(
                                    source_term=source_term,
                                    target_term=target_term,
                                    source_lang='zh',
                                    target_lang='en'
                                )
                                if success:
                                    imported_count += 1
                                else:
                                    failed_count += 1
                                    errors.append(f"第{line_num}行: 添加术语失败")
                            else:
                                failed_count += 1
                                errors.append(f"第{line_num}行: 源术语或目标术语为空")
                        else:
                            failed_count += 1
                            errors.append(f"第{line_num}行: 格式错误")
                    except Exception as e:
                        failed_count += 1
                        errors.append(f"第{line_num}行: {str(e)}")

            return jsonify({
                'success': True,
                'message': f'术语导入完成',
                'imported_count': imported_count,
                'failed_count': failed_count,
                'total_count': imported_count + failed_count,
                'errors': errors[:10],  # 只返回前10个错误
                'has_more_errors': len(errors) > 10
            })

        except Exception as e:
            return jsonify({'error': f'文件解析失败: {str(e)}'}), 400

    except Exception as e:
        current_app.logger.error(f"导入术语失败: {e}")
        return jsonify({'error': f'导入术语失败: {str(e)}'}), 500

@terminology_bp.route('/export', methods=['GET'])
def export_terms():
    """导出术语库"""
    try:
        format_type = request.args.get('format', 'csv').lower()
        source_lang = request.args.get('source_lang', '')
        target_lang = request.args.get('target_lang', '')

        if format_type not in ['csv', 'json', 'txt']:
            return jsonify({'error': '不支持的导出格式'}), 400

        # 获取松瓷机电AI助手实例
        assistant = current_app.config.get('AI_ASSISTANT')
        if not assistant or not hasattr(assistant, 'term_base'):
            return jsonify({'error': '术语库未初始化'}), 500

        term_base = assistant.term_base

        # 获取术语数据
        terms_data = []
        if hasattr(term_base, 'terms'):
            for source_term, term_data in term_base.terms.items():
                if isinstance(term_data, dict):
                    metadata = term_data.get('metadata', {})

                    # 语言过滤
                    if source_lang and metadata.get('source_lang') != source_lang:
                        continue
                    if target_lang and metadata.get('target_lang') != target_lang:
                        continue

                    term_item = {
                        'source_term': source_term,
                        'target_term': term_data.get('target_term', term_data.get('definition', '')),
                        'source_lang': metadata.get('source_lang', 'zh'),
                        'target_lang': metadata.get('target_lang', 'en'),
                        'category': metadata.get('category', ''),
                        'description': metadata.get('description', ''),
                        'created_at': metadata.get('added_time', ''),
                        'updated_at': metadata.get('updated_time', '')
                    }
                else:
                    # 兼容旧格式
                    term_item = {
                        'source_term': source_term,
                        'target_term': str(term_data),
                        'source_lang': 'zh',
                        'target_lang': 'en',
                        'category': '',
                        'description': '',
                        'created_at': '',
                        'updated_at': ''
                    }
                terms_data.append(term_item)

        if not terms_data:
            return jsonify({'error': '没有术语数据可导出'}), 400

        # 生成导出内容
        if format_type == 'csv':
            output = StringIO()
            fieldnames = ['source_term', 'target_term', 'source_lang', 'target_lang', 'category', 'description']
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            for term in terms_data:
                writer.writerow({k: term.get(k, '') for k in fieldnames})
            content = output.getvalue()
            content_type = 'text/csv'
            filename = f'terminology_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'

        elif format_type == 'json':
            content = json.dumps(terms_data, ensure_ascii=False, indent=2)
            content_type = 'application/json'
            filename = f'terminology_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'

        elif format_type == 'txt':
            lines = []
            for term in terms_data:
                lines.append(f"{term['source_term']}\t{term['target_term']}")
            content = '\n'.join(lines)
            content_type = 'text/plain'
            filename = f'terminology_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt'

        return jsonify({
            'success': True,
            'content': content,
            'content_type': content_type,
            'filename': filename,
            'total_terms': len(terms_data),
            'exported_at': datetime.now().isoformat()
        })

    except Exception as e:
        current_app.logger.error(f"导出术语失败: {e}")
        return jsonify({'error': f'导出术语失败: {str(e)}'}), 500

@terminology_bp.route('/categories', methods=['GET'])
def get_categories():
    """获取术语分类列表"""
    try:
        # 获取松瓷机电AI助手实例
        assistant = current_app.config.get('AI_ASSISTANT')
        if not assistant or not hasattr(assistant, 'term_base'):
            return jsonify({'error': '术语库未初始化'}), 500

        term_base = assistant.term_base

        # 收集所有分类
        categories = set()
        if hasattr(term_base, 'terms'):
            for term_data in term_base.terms.values():
                if isinstance(term_data, dict):
                    metadata = term_data.get('metadata', {})
                    category = metadata.get('category', '').strip()
                    if category:
                        categories.add(category)

        categories_list = sorted(list(categories))

        return jsonify({
            'success': True,
            'categories': categories_list,
            'total_count': len(categories_list)
        })

    except Exception as e:
        current_app.logger.error(f"获取术语分类失败: {e}")
        return jsonify({'error': f'获取术语分类失败: {str(e)}'}), 500

@terminology_bp.route('/statistics', methods=['GET'])
def get_statistics():
    """获取术语库统计信息"""
    try:
        # 获取松瓷机电AI助手实例
        assistant = current_app.config.get('AI_ASSISTANT')
        if not assistant or not hasattr(assistant, 'term_base'):
            return jsonify({'error': '术语库未初始化'}), 500

        term_base = assistant.term_base

        # 统计信息
        stats = {
            'total_terms': 0,
            'language_pairs': {},
            'categories': {},
            'recent_additions': 0,
            'last_updated': None
        }

        if hasattr(term_base, 'terms'):
            stats['total_terms'] = len(term_base.terms)

            # 统计语言对和分类
            for term_data in term_base.terms.values():
                if isinstance(term_data, dict):
                    metadata = term_data.get('metadata', {})

                    # 语言对统计
                    source_lang = metadata.get('source_lang', 'zh')
                    target_lang = metadata.get('target_lang', 'en')
                    lang_pair = f"{source_lang}-{target_lang}"
                    stats['language_pairs'][lang_pair] = stats['language_pairs'].get(lang_pair, 0) + 1

                    # 分类统计
                    category = metadata.get('category', '未分类')
                    if not category:
                        category = '未分类'
                    stats['categories'][category] = stats['categories'].get(category, 0) + 1

                    # 最近添加统计（7天内）
                    added_time = metadata.get('added_time', '')
                    if added_time:
                        try:
                            from datetime import datetime, timedelta
                            added_date = datetime.fromisoformat(added_time.replace('Z', '+00:00'))
                            if added_date > datetime.now() - timedelta(days=7):
                                stats['recent_additions'] += 1
                        except:
                            pass

                    # 最后更新时间
                    updated_time = metadata.get('updated_time', metadata.get('added_time', ''))
                    if updated_time:
                        if not stats['last_updated'] or updated_time > stats['last_updated']:
                            stats['last_updated'] = updated_time

        return jsonify({
            'success': True,
            'statistics': stats
        })

    except Exception as e:
        current_app.logger.error(f"获取术语库统计失败: {e}")
        return jsonify({'error': f'获取术语库统计失败: {str(e)}'}), 500

@terminology_bp.route('/status', methods=['GET'])
def get_terminology_status():
    """获取术语库状态"""
    try:
        assistant = current_app.config.get('AI_ASSISTANT')

        status = {
            'term_base_available': False,
            'vector_db_available': False,
            'total_terms': 0,
            'last_updated': None
        }

        if assistant and hasattr(assistant, 'term_base') and assistant.term_base:
            status['term_base_available'] = True

            # 获取术语数量
            try:
                if hasattr(assistant.term_base, 'terms'):
                    status['total_terms'] = len(assistant.term_base.terms)
            except:
                status['total_terms'] = 0

            # 检查向量数据库
            if hasattr(assistant.term_base, 'vector_db') and assistant.term_base.vector_db:
                status['vector_db_available'] = True

        return jsonify({
            'success': True,
            'status': status
        })

    except Exception as e:
        current_app.logger.error(f"获取术语库状态失败: {e}")
        return jsonify({'error': f'获取术语库状态失败: {str(e)}'}), 500
