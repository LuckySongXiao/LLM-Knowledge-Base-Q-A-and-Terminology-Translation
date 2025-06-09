import os
import json
import re
from datetime import datetime
import uuid

class TermBase:
    """术语库管理类"""

    def __init__(self, vector_db, settings):
        self.vector_db = vector_db
        self.settings = settings
        self.term_path = os.path.join('data', 'terms')
        self.ensure_dir_exists(self.term_path)

        # 术语条目
        self.terms = {}  # {term: {'definition': str, 'vector_id': str, 'metadata': dict}}

        # 加载术语条目
        self.load()

        # 当向量模型加载完成后初始化术语向量
        if hasattr(vector_db, 'model') and vector_db.model:
            self.ensure_term_vectors()
        else:
            print("向量模型尚未加载，将在模型加载完成后初始化术语向量")

    def ensure_dir_exists(self, path):
        """确保目录存在"""
        if not os.path.exists(path):
            os.makedirs(path)

    def add_term(self, source_term, target_term, source_lang="zh", target_lang="en"):
        """添加术语条目"""
        if not source_term or not target_term:
            print("[ERROR] 添加术语失败: 源术语或目标术语不能为空")
            return False

        # 生成唯一ID
        term_id = str(uuid.uuid4())

        # 创建术语数据
        metadata = {
            'id': term_id,
            'source_lang': source_lang,
            'target_lang': target_lang,
            'type': 'term',
            'added_time': datetime.now().isoformat()
        }

        term_data = {
            'source_term': source_term,
            'target_term': target_term,
            'definition': target_term,  # 兼容旧版结构
            'vector_id': None,  # 稍后生成向量
            'metadata': metadata
        }

        # 添加到术语库
        self.terms[source_term] = term_data

        # 保存术语库
        save_result = self.save()

        # 尝试生成向量
        if self.vector_db and hasattr(self.vector_db, 'model') and self.vector_db.model:
            try:
                vector = self.vector_db.get_embedding(source_term)
                if vector is not None:
                    vector_id = str(uuid.uuid4())
                    self.vector_db.add_vector(vector_id, source_term, vector, metadata)
                    term_data['vector_id'] = vector_id
                    self.terms[source_term] = term_data
                    self.save()
                    print(f"[INFO] 术语 '{source_term}' 向量生成成功")
            except Exception as e:
                print(f"[WARNING] 术语 '{source_term}' 向量生成失败: {e}")

        return save_result

    def get_term(self, term):
        """获取术语定义"""
        if term in self.terms:
            return self.terms[term]['definition']
        return None

    def update_term(self, term, definition, metadata=None):
        """更新术语条目"""
        if term not in self.terms:
            return False

        if metadata is None:
            metadata = self.terms[term]['metadata']

        # 获取文本向量
        ai_engine = self.settings.get_ai_engine()
        if not ai_engine:
            return False

        vector = ai_engine.get_vector_embedding(term + " " + definition)
        if vector is None:
            return False

        # 删除旧向量
        old_vector_id = self.terms[term]['vector_id']
        self.vector_db.delete(old_vector_id)

        # 添加新向量
        vector_id = self.vector_db.add(term + " " + definition, vector, metadata)

        # 更新术语条目
        self.terms[term] = {
            'definition': definition,
            'vector_id': vector_id,
            'metadata': metadata
        }

        return True

    def delete_term(self, term):
        """删除术语条目"""
        if term not in self.terms:
            return False

        # 删除向量
        vector_id = self.terms[term]['vector_id']
        self.vector_db.delete(vector_id)

        # 删除术语条目
        del self.terms[term]

        return True

    def list_terms(self):
        """列出所有术语条目"""
        return list(self.terms.keys())

    def search(self, query, top_k=15):
        """搜索术语条目"""
        # 如果查询为空，则返回所有术语
        if not query.strip():
            return list(self.terms.keys())

        try:
            # 检查向量数据库是否可用
            if not hasattr(self, 'vector_db') or not self.vector_db:
                print("警告: 向量数据库未初始化，使用简单文本匹配搜索")
                return self._text_search(query)

            # 检查向量模型是否就绪
            if not self.vector_db.check_model_ready():
                print("警告: 向量模型未就绪，使用简单文本匹配搜索")
                return self._text_search(query)

            # 获取查询向量
            print(f"生成查询向量: {query}")
            query_vector = self.vector_db.encode_text(query)

            if query_vector is None:
                print("警告: 无法生成查询向量，使用简单文本匹配搜索")
                return self._text_search(query)

            # 搜索相似向量
            print("在向量数据库中搜索...")
            vector_results = self.vector_db.search(query_vector, top_k)

            # 转换结果为术语条目
            items = []
            for vector_id, _, _ in vector_results:
                for term_key, term_info in self.terms.items():
                    if term_info.get('vector_id') == vector_id:
                        items.append(term_key)
                        break

            # 如果向量搜索没有足够结果，补充文本搜索
            if len(items) < top_k:
                text_results = self._text_search(query)
                for term in text_results:
                    if term not in items:
                        items.append(term)
                        if len(items) >= top_k:
                            break

            return items
        except Exception as e:
            print(f"术语搜索错误: {e}")
            import traceback
            traceback.print_exc()
            # 出错时回退到文本搜索
            return self._text_search(query)

    def _text_search(self, query):
        """使用简单文本匹配搜索术语"""
        results = []
        query_lower = query.lower()

        # 搜索术语名称
        for term_key in self.terms.keys():
            if query_lower in term_key.lower():
                results.append(term_key)

        # 搜索术语内容
        for term_key, term_info in self.terms.items():
            if term_key in results:
                continue

            # 搜索翻译
            for target_lang, translations in term_info['translations'].items():
                if query_lower in translations.lower():
                    results.append(term_key)
                    break

        return results

    def import_termbase(self, file_path):
        """导入术语表"""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")

        # 读取文件内容
        file_ext = os.path.splitext(file_path)[1].lower()

        # 根据文件类型处理
        if file_ext == '.json':
            with open(file_path, 'r', encoding='utf-8') as f:
                term_data = json.load(f)

            for term, definition in term_data.items():
                metadata = {
                    'source': file_path,
                    'imported_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                self.add_term(term, definition, metadata)

        elif file_ext in ['.txt', '.csv']:
            # 假设格式为 "术语,定义"
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            for line in lines:
                if ',' in line:
                    term, definition = line.strip().split(',', 1)
                    metadata = {
                        'source': file_path,
                        'imported_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
                    self.add_term(term, definition, metadata)
        else:
            raise ValueError(f"不支持的文件类型: {file_ext}")

        return True

    def get_relevant_terms(self, text):
        """获取与文本相关的术语"""
        result = []

        # 如果术语库为空，直接返回空列表
        if not self.terms:
            return result

        try:
            # 使用文本匹配进行基本搜索
            text_lower = text.lower()
            for term_id, term_data in self.terms.items():
                if 'source_term' in term_data and term_data['source_term'].lower() in text_lower:
                    result.append(term_data)

            # 如果有AI引擎和向量能力，尝试使用向量搜索补充结果
            ai_engine = None
            if hasattr(self, 'ai_engine'):
                ai_engine = self.ai_engine
            elif hasattr(self, 'settings') and hasattr(self.settings, 'ai_engine'):
                ai_engine = self.settings.ai_engine

            if ai_engine and hasattr(ai_engine, 'get_vector_embedding'):
                try:
                    # 获取文本向量
                    text_vector = ai_engine.get_vector_embedding(text)
                    if text_vector is not None and hasattr(ai_engine, 'vector_db') and ai_engine.vector_db:
                        # 搜索相似向量
                        max_terms = 5  # 最多返回5个相关术语
                        vector_results = ai_engine.vector_db.search(text_vector, max_terms)

                        # 记录已添加的术语ID，避免重复
                        added_term_ids = set([term.get('id') for term in result if 'id' in term])

                        # 将向量结果转换为术语
                        for vector_id, _, score in vector_results:
                            for term_id, term_data in self.terms.items():
                                if term_id not in added_term_ids and term_data.get('vector_id') == vector_id:
                                    result.append(term_data)
                                    added_term_ids.add(term_id)
                except Exception as e:
                    print(f"向量搜索术语失败: {e}")
                    # 继续使用文本匹配的结果

            return result
        except Exception as e:
            print(f"获取相关术语失败: {e}")
            import traceback
            traceback.print_exc()
            return []

    def get_formatted_terms(self, term_dict):
        """获取格式化的术语列表"""
        if not term_dict:
            return ""

        formatted = ""
        for term, definition in term_dict.items():
            formatted += f"{term}: {definition}\n"

        return formatted.strip()

    def save(self):
        """保存术语库"""
        print("\n===== 保存术语库 =====")
        try:
            import os
            import json
            import uuid
            from datetime import datetime

            # 确保目录存在
            if not os.path.exists(self.term_path):
                os.makedirs(self.term_path)
                print(f"创建术语库目录: {self.term_path}")

            # 保存术语条目索引
            save_path = os.path.join(self.term_path, 'terms.json')

            # 创建备份
            if os.path.exists(save_path):
                backup_path = save_path + '.bak'
                try:
                    import shutil
                    shutil.copy2(save_path, backup_path)
                    print(f"[INFO] 已创建备份文件: {backup_path}")
                except Exception as e:
                    print(f"[WARNING] 创建备份文件失败: {e}")

            print(f"[INFO] 保存术语库文件: {save_path}")

            # 去除向量数据，只保存必要信息
            serializable_terms = {}
            for term, term_data in self.terms.items():
                try:
                    # 创建可序列化的副本，确保包含所有必要字段
                    serializable_terms[term] = {
                        'source_term': term_data.get('source_term', term),
                        'target_term': term_data.get('target_term', term_data.get('definition', '')),
                        'definition': term_data.get('definition', term_data.get('target_term', '')),
                        'vector_id': term_data.get('vector_id'),
                        'metadata': {
                            'id': term_data.get('metadata', {}).get('id', str(uuid.uuid4())),
                            'source_lang': term_data.get('metadata', {}).get('source_lang', 'zh'),
                            'target_lang': term_data.get('metadata', {}).get('target_lang', 'en'),
                            'type': 'term',
                            'added_time': term_data.get('metadata', {}).get('added_time', datetime.now().isoformat())
                        }
                    }
                    print(f"[INFO] 处理术语: {term} => {serializable_terms[term]['target_term']}")
                except Exception as e:
                    print(f"[WARNING] 序列化术语 '{term}' 时出错: {e}")

            # 写入临时文件
            temp_path = save_path + '.tmp'
            try:
                with open(temp_path, 'w', encoding='utf-8') as f:
                    json.dump(serializable_terms, f, ensure_ascii=False, indent=2)

                # 验证临时文件可以被正确读取
                with open(temp_path, 'r', encoding='utf-8') as f:
                    test_load = json.load(f)

                # 如果验证成功，替换原文件
                if os.path.exists(save_path):
                    os.remove(save_path)
                os.rename(temp_path, save_path)

                print(f"[INFO] 成功保存 {len(serializable_terms)} 个术语条目到 {save_path}")
            except Exception as e:
                print(f"[ERROR] 保存术语库失败: {e}")
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                return False

            # 保存向量数据库
            if hasattr(self, 'vector_db') and self.vector_db:
                self.vector_db.save()
                print("[INFO] 术语向量数据库已保存")

            print("===== 术语库保存完成 =====\n")
            return True

        except Exception as e:
            print(f"[ERROR] 保存术语库失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    def load(self):
        """加载术语库"""
        # 加载术语条目索引
        load_path = os.path.join(self.term_path, 'terms.json')

        # 调试信息：显示当前工作目录和文件路径
        current_dir = os.getcwd()
        abs_load_path = os.path.abspath(load_path)

        if os.path.exists(load_path):
            try:
                # 尝试加载主文件
                with open(load_path, 'r', encoding='utf-8') as f:
                    try:
                        self.terms = json.load(f)
                        print(f"[INFO] 成功从 {load_path} 加载了 {len(self.terms)} 个术语")
                        return True
                    except json.JSONDecodeError as e:
                        print(f"[ERROR] 主文件解析失败: {e}")

                        # 尝试加载备份文件
                        backup_path = load_path + '.bak'
                        if os.path.exists(backup_path):
                            print("[INFO] 尝试从备份文件恢复...")
                            with open(backup_path, 'r', encoding='utf-8') as bf:
                                self.terms = json.load(bf)
                                print(f"[INFO] 成功从备份文件恢复了 {len(self.terms)} 个术语")

                                # 从备份恢复主文件
                                import shutil
                                shutil.copy2(backup_path, load_path)
                                print("[INFO] 已从备份文件恢复主文件")
                                return True
                        else:
                            print("[WARNING] 未找到可用的备份文件")
                            return False
            except Exception as e:
                print(f"[ERROR] 加载术语条目失败: {e}")
                import traceback
                traceback.print_exc()
                return False
        else:
            print(f"[INFO] 术语库文件不存在: {load_path}")
            self.terms = {}
            return True

    def import_terminology_file(self, file_path):
        """导入术语库文件，支持terminology.json嵌套结构"""
        try:
            print(f"开始导入术语文件: {file_path}")
            # 确保文件存在
            if not os.path.exists(file_path):
                return False, f"文件不存在: {file_path}"

            # 读取术语库文件
            with open(file_path, 'r', encoding='utf-8') as f:
                try:
                    terminology_data = json.load(f)
                    print(f"成功加载术语文件，开始处理")
                except json.JSONDecodeError:
                    # 尝试不同的格式
                    f.seek(0)
                    lines = f.readlines()
                    terminology_data = {}

                    for line in lines:
                        if ',' in line or '\t' in line:
                            # 尝试CSV或TSV格式
                            separator = ',' if ',' in line else '\t'
                            parts = line.strip().split(separator)
                            if len(parts) >= 2:
                                source_term = parts[0].strip()
                                target_term = parts[1].strip()
                                source_lang = parts[2].strip() if len(parts) > 2 else "en"
                                target_lang = parts[3].strip() if len(parts) > 3 else "zh"

                                if source_lang not in terminology_data:
                                    terminology_data[source_lang] = {}

                                if target_lang not in terminology_data[source_lang]:
                                    terminology_data[source_lang][target_lang] = {}

                                terminology_data[source_lang][target_lang][source_term] = target_term

            # 处理导入的数量
            imported_count = 0
            updated_count = 0
            errors = []

            # 根据术语库JSON格式进行处理
            if isinstance(terminology_data, dict):
                # 检查是否是terminology.json格式的嵌套结构
                if "中文" in terminology_data and isinstance(terminology_data["中文"], dict):
                    print("检测到terminology.json格式的嵌套术语结构")
                    for source_lang, target_langs in terminology_data.items():
                        if isinstance(target_langs, dict):
                            for target_lang, terms in target_langs.items():
                                if isinstance(terms, dict):
                                    print(f"处理 {source_lang} 到 {target_lang} 的术语，共 {len(terms)} 项")
                                    # 遍历所有术语对
                                    for source_term, target_term in terms.items():
                                        try:
                                            # 添加术语(源语言是中文，目标语言是英文等)
                                            success = self.add_term(
                                                source_term,
                                                target_term,
                                                source_lang,
                                                target_lang
                                            )

                                            if success:
                                                term_id = f"{source_term}_{source_lang}_{target_lang}"
                                                if term_id in self.terms:
                                                    updated_count += 1
                                                else:
                                                    imported_count += 1
                                            else:
                                                errors.append(f"添加术语失败: {source_term}")
                                        except Exception as e:
                                            errors.append(f"处理术语出错 '{source_term}': {str(e)}")
                # 检查术语数据格式 - 标准格式
                elif all(isinstance(v, str) for v in terminology_data.values()):
                    # 简单的 "术语":"定义" 格式
                    for source_term, target_term in terminology_data.items():
                        try:
                            success = self.add_term(source_term, target_term)
                            if success:
                                imported_count += 1
                            else:
                                errors.append(f"添加术语失败: {source_term}")
                        except Exception as e:
                            errors.append(f"处理术语出错 '{source_term}': {str(e)}")
                else:
                    # 标准格式: {source_lang: {target_lang: {source_term: target_term}}}
                    for source_lang, target_langs in terminology_data.items():
                        if isinstance(target_langs, dict):
                            for target_lang, terms in target_langs.items():
                                if isinstance(terms, dict):
                                    # 遍历所有术语对
                                    for source_term, target_term in terms.items():
                                        try:
                                            # 添加术语
                                            success = self.add_term(
                                                source_term,
                                                target_term,
                                                source_lang,
                                                target_lang
                                            )

                                            if success:
                                                term_id = f"{source_term}_{source_lang}_{target_lang}"
                                                if term_id in self.terms:
                                                    updated_count += 1
                                                else:
                                                    imported_count += 1
                                            else:
                                                errors.append(f"添加术语失败: {source_term}")
                                        except Exception as e:
                                            errors.append(f"处理术语出错 '{source_term}': {str(e)}")

            # 保存术语库
            self.save()

            # 为术语生成向量表示
            self.ensure_term_vectors()

            # 返回导入结果
            if errors:
                return True, f"导入完成: 新增{imported_count}个术语, 更新{updated_count}个术语, {len(errors)}个错误"
            else:
                return True, f"导入成功: 新增{imported_count}个术语, 更新{updated_count}个术语"

        except Exception as e:
            import traceback
            traceback.print_exc()
            return False, f"导入失败: {str(e)}"

    def ensure_term_vectors(self):
        """确保所有术语都有向量表示"""
        print("开始为术语生成向量表示...")
        vectorized_count = 0

        # 确保将向量存储到术语专用向量库
        vector_db = self.vector_db  # 这里应该是术语专用的向量数据库

        # 检查向量模型是否已加载
        if not hasattr(vector_db, 'model') or not vector_db.model:
            print("向量模型未加载，无法生成术语向量")
            # 尝试从主向量数据库获取模型
            if hasattr(self.settings, 'get_ai_engine'):
                ai_engine = self.settings.get_ai_engine()
                if ai_engine and hasattr(ai_engine, 'vector_model'):
                    print("从AI引擎获取向量模型")
                    vector_db.model = ai_engine.vector_model

            # 再次检查
            if not hasattr(vector_db, 'model') or not vector_db.model:
                return False

        # 遍历所有术语
        for term_id, term_data in self.terms.items():
            # 如果术语没有向量ID
            if not term_data.get('vector_id'):
                try:
                    # 对术语内容生成向量
                    source_term = term_data.get('source_term', '')
                    if source_term:
                        # 生成向量
                        vector = vector_db.get_embedding(source_term)
                        if vector is not None:
                            # 添加到专用向量数据库
                            metadata = term_data.get('metadata', {})
                            metadata['type'] = 'term'  # 标记为术语向量
                            vector_id = vector_db.add(source_term, vector, metadata)

                            # 更新术语数据
                            term_data['vector_id'] = vector_id
                            self.terms[term_id] = term_data
                            vectorized_count += 1
                            if vectorized_count % 20 == 0:
                                print(f"已处理 {vectorized_count} 个术语向量")
                except Exception as e:
                    print(f"为术语 '{term_id}' 生成向量时出错: {e}")

        # 保存更新后的术语和向量
        if vectorized_count > 0:
            print(f"成功为 {vectorized_count} 个术语生成向量表示")
            self.save()
            vector_db.save()  # 保存术语向量数据库

        return True

    def format_term_for_translation(self, term_data):
        """格式化术语用于翻译"""
        # 确保术语数据包含必要的字段
        if not term_data:
            return None

        # 如果已经是正确格式，直接返回
        if 'source_term' in term_data and 'target_term' in term_data:
            return term_data

        # 创建标准格式的术语数据
        formatted = {
            'source_term': term_data.get('term', ''),
            'target_term': term_data.get('definition', ''),
            'source_lang': term_data.get('metadata', {}).get('source_lang', 'auto'),
            'target_lang': term_data.get('metadata', {}).get('target_lang', 'zh')
        }

        return formatted

    def search_similar_terms(self, query, top_k=15):
        """使用向量相似度搜索相关术语"""
        if not hasattr(self.vector_db, 'model') or not self.vector_db.model:
            print("向量模型未加载，无法执行术语向量搜索")
            return []

        try:
            # 先确保所有术语都有向量
            self.ensure_term_vectors()

            # 获取查询文本的向量
            query_vector = self.vector_db.get_embedding(query)
            if query_vector is None:
                print("无法获取查询向量")
                return []

            # 在向量数据库中搜索
            results = self.vector_db.search(query, top_k=top_k, min_similarity=0.3)

            # 过滤结果，只保留术语类型
            term_results = []
            for result in results:
                metadata = result.get('metadata', {})
                if metadata.get('type') == 'term':
                    # 添加到结果中
                    term_results.append({
                        'term': result.get('content', ''),
                        'similarity': result.get('similarity', 0),
                        'metadata': metadata
                    })

            print(f"术语向量搜索完成，找到 {len(term_results)} 个相关术语")
            return term_results

        except Exception as e:
            print(f"术语向量搜索失败: {e}")
            import traceback
            traceback.print_exc()
            return []

    def get_all_terms(self):
        """获取所有术语，供翻译引擎使用"""
        return self.terms