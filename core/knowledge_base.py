import os
import json
import re
from datetime import datetime
import time
import numpy as np

class KnowledgeBase:
    """知识库管理类"""

    def __init__(self, vector_db, settings):
        self.vector_db = vector_db
        self.settings = settings
        self.knowledge_path = os.path.join('data', 'knowledge')
        self.ensure_dir_exists(self.knowledge_path)

        # 知识条目
        self.items = {}  # {name: {'content': str, 'vector_id': str, 'metadata': dict}}

        # 加载知识条目
        self.load()

    def ensure_dir_exists(self, path):
        """确保目录存在"""
        if not os.path.exists(path):
            os.makedirs(path)

    def add_item(self, name, content, metadata=None):
        """添加知识条目"""
        if metadata is None:
            metadata = {}

        # 获取AI引擎
        ai_engine = self.settings.get_ai_engine()
        if not ai_engine:
            return False

        # 获取文本向量
        vector = ai_engine.get_vector_embedding(content)
        if vector is None:
            return False

        # 添加到向量数据库
        vector_id = self.vector_db.add(content, vector, metadata)

        # 添加到知识条目
        self.items[name] = {
            'content': content,
            'vector_id': vector_id,
            'metadata': metadata
        }

        return True

    def get_item(self, name):
        """获取知识条目"""
        if name in self.items:
            return self.items[name]
        else:
            print(f"找不到知识条目: {name}")
            return None

    def update_item(self, name, content, metadata=None):
        """更新知识条目"""
        if name not in self.items:
            return False

        if metadata is None:
            metadata = self.items[name]['metadata']

        # 获取文本向量
        ai_engine = self.settings.get_ai_engine()
        if not ai_engine:
            return False

        vector = ai_engine.get_vector_embedding(content)
        if vector is None:
            return False

        # 删除旧向量
        old_vector_id = self.items[name]['vector_id']
        self.vector_db.delete(old_vector_id)

        # 添加新向量
        vector_id = self.vector_db.add(content, vector, metadata)

        # 更新知识条目
        self.items[name] = {
            'content': content,
            'vector_id': vector_id,
            'metadata': metadata
        }

        return True

    def delete_item(self, name):
        """删除知识条目"""
        if name not in self.items:
            return False

        # 删除向量
        vector_id = self.items[name]['vector_id']
        self.vector_db.delete(vector_id)

        # 删除知识条目
        del self.items[name]

        return True

    def delete_knowledge(self, name):
        """删除知识条目（PC端兼容方法）"""
        return self.delete_item(name)

    def add_knowledge(self, name, content, metadata=None):
        """添加知识条目（PC端兼容方法）"""
        return self.add_item(name, content, metadata)

    def list_items(self):
        """列出所有知识条目"""
        return list(self.items.keys())

    def search(self, query, top_k=5):
        """增强的知识库搜索方法，支持查询变体和关键词提取"""
        try:
            print(f"知识库搜索查询: {query}")
            start_time = time.time()

            # 确保知识库已初始化
            if not hasattr(self, 'vector_db') or self.vector_db is None:
                print("[ERROR] 知识库向量数据库未初始化")
                return []

            # 确保向量数据库有模型
            if not hasattr(self.vector_db, 'model') or self.vector_db.model is None:
                print("[ERROR] 向量模型未加载")
                return []

            # 生成查询变体以增加匹配概率
            query_variants = self._generate_query_variants(query)
            print(f"[DEBUG] 生成的查询变体: {query_variants}")

            # 提取关键词
            try:
                import jieba.analyse
                keywords = jieba.analyse.extract_tags(query, topK=3)
                if keywords:
                    query_variants.extend(keywords)
                    print(f"[DEBUG] 提取的关键词: {keywords}")
            except:
                print("[WARNING] 关键词提取失败")

            # 依次尝试所有查询变体
            all_results = []
            seen_contents = set()

            for variant in query_variants:
                print(f"[DEBUG] 尝试搜索变体: '{variant}'")
                # 降低相似度阈值以提高召回率
                results = self.vector_db.search(variant, top_k=15, min_similarity=0.4)

                if results:
                    # 去重并合并结果
                    for result in results:
                        content = result.get('content', '')
                        content_hash = hash(content)
                        if content_hash not in seen_contents:
                            seen_contents.add(content_hash)
                            all_results.append(result)

            # 重新按相似度排序
            all_results.sort(key=lambda x: x.get('similarity', 0), reverse=True)

            # 最多返回top_k个结果
            final_results = all_results[:top_k]

            # 记录搜索时间
            elapsed = time.time() - start_time
            print(f"知识库搜索完成，耗时: {elapsed:.2f}秒，找到 {len(final_results)} 条结果")

            return final_results
        except Exception as e:
            print(f"[ERROR] 知识库搜索失败: {e}")
            import traceback
            traceback.print_exc()
            return []

    def _generate_query_variants(self, query):
        """生成查询变体"""
        variants = [query]  # 原始查询

        # 添加前缀变体
        prefixes = ["如何", "什么是", "请解释", "关于", "定义"]
        for prefix in prefixes:
            if not query.startswith(prefix):
                variants.append(f"{prefix}{query}")

        # 添加后缀变体
        suffixes = ["的解释", "的定义", "的方法", "的过程", "的概念"]
        for suffix in suffixes:
            if not query.endswith(suffix):
                variants.append(f"{query}{suffix}")

        return variants

    def _keyword_search(self, query, top_k=15):
        """基于关键词的搜索"""
        # 提取查询关键词
        import jieba
        import re

        # 简单分词
        keywords = [w for w in jieba.cut(query) if len(w) > 1]

        # 按关键词匹配度评分
        scored_items = []
        for title, item in self.items.items():
            score = 0
            content = item['content'].lower()
            for keyword in keywords:
                if keyword.lower() in content:
                    # 根据出现次数和位置加权
                    count = content.count(keyword.lower())
                    # 关键词在前面出现权重更高
                    position = content.find(keyword.lower())
                    position_weight = 1.0 / (1 + position / 100) if position >= 0 else 0
                    score += count * (0.5 + position_weight)

            if score > 0:
                scored_items.append((title, score))

        # 排序并返回前top_k个结果
        scored_items.sort(key=lambda x: x[1], reverse=True)
        return [title for title, _ in scored_items[:top_k]]

    def _combine_and_rerank(self, keyword_results, vector_results, query, top_k=5):
        """结合并重排序结果"""
        # 初始化vector_titles变量，确保在所有条件分支中都有定义
        vector_titles = []

        # 检查输入是否为空
        if not vector_results and not keyword_results:
            return []

        # 如果向量结果为空，直接返回关键词结果
        if not vector_results:
            return keyword_results[:top_k]

        # 如果关键词结果为空，处理向量结果
        if not keyword_results:
            # 处理向量结果 - 不需要创建新的vector_titles，使用上面已初始化的
            for result in vector_results:
                try:
                    # 适应不同的返回格式
                    if isinstance(result, tuple):
                        if len(result) >= 2:
                            vector_id = result[0]
                        else:
                            continue
                    else:
                        vector_id = result

                    # 查找对应的知识条目
                    for title, item in self.items.items():
                        if 'vector_id' in item and item['vector_id'] == vector_id and title not in vector_titles:
                            vector_titles.append(title)
                except Exception as e:
                    print(f"处理向量结果时出错: {e}")
                    continue

            return vector_titles[:top_k]

        # 正常处理：合并向量结果和关键词结果
        # 在这个分支也需要构建vector_titles
        for result in vector_results:
            try:
                # 适应不同的返回格式
                if isinstance(result, tuple):
                    if len(result) >= 2:
                        vector_id = result[0]
                    else:
                        continue
                else:
                    vector_id = result

                # 查找对应的知识条目
                for title, item in self.items.items():
                    if 'vector_id' in item and item['vector_id'] == vector_id and title not in vector_titles:
                        vector_titles.append(title)
            except Exception as e:
                print(f"处理向量结果时出错: {e}")
                continue

        # 合并结果
        combined = []

        # 先添加同时出现在两种结果中的项
        for title in keyword_results:
            if title in vector_titles:
                combined.append(title)

        # 然后添加仅在向量结果中的项
        for title in vector_titles:
            if title not in combined:
                combined.append(title)

        # 最后添加仅在关键词结果中的项
        for title in keyword_results:
            if title not in combined:
                combined.append(title)

        # 截取前top_k个结果
        return combined[:top_k]

    def import_file(self, file_path):
        """导入文件到知识库，支持问答格式和普通文档"""
        try:
            # 检查文件是否存在
            if not os.path.exists(file_path):
                return False, f"文件不存在: {file_path}"

            # 读取文件内容
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 获取文件名作为基础标题
            base_title = os.path.basename(file_path)
            print(f"正在导入文件: {base_title}")

            # 首先尝试解析为问答格式
            qa_groups = self._parse_qa_content(content)

            if qa_groups:
                # 按问答格式处理
                return self._import_qa_format(qa_groups, base_title, file_path)
            else:
                # 按普通文档格式处理
                return self._import_document_format(content, base_title, file_path)

        except Exception as e:
            import traceback
            traceback.print_exc()
            return False, f"导入失败: {str(e)}"

    def _import_qa_format(self, qa_groups, base_title, file_path):
        """导入问答格式内容"""
        success_count = 0
        failed_count = 0

        # 处理每个问答组
        for i, qa_group in enumerate(qa_groups):
            # 为每个QA组创建唯一标题
            title = f"{base_title}_QA_{i+1}"

            # 检查是否已存在同名条目
            if title in self.items:
                # 添加时间戳确保唯一性
                title = f"{title}_{int(time.time())}"

            # 尝试生成向量
            vector_id = None
            if hasattr(self, 'vector_db') and self.vector_db and self.vector_db.check_model_ready():
                try:
                    # 使用问题部分生成向量(主问题+相似问)，提高检索精度
                    index_text = qa_group['question'] + "\n" + qa_group['similar_questions']
                    vector = self.vector_db.encode_text(index_text)

                    if vector is not None:
                        # 添加到向量数据库(存储完整内容)
                        vector_id = self.vector_db.add(qa_group['full_text'], vector, {
                            'title': title,
                            'type': 'qa_group',
                            'source': file_path
                        })
                except Exception as e:
                    print(f"向量处理出错: {e}")

            # 添加到知识条目
            self.items[title] = {
                'content': qa_group['full_text'],  # 存储完整内容
                'vector_id': vector_id,
                'metadata': {
                    'imported_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'source': file_path,
                    'type': 'qa_group',
                    'question': qa_group['question'],
                    'answer': qa_group['answer']
                }
            }

            if vector_id:
                success_count += 1
            else:
                failed_count += 1

        # 保存知识库
        self.save()

        return True, f"已导入 {success_count} 个问答组 (其中 {failed_count} 个无向量索引)"

    def _import_document_format(self, content, base_title, file_path):
        """导入普通文档格式内容"""
        success_count = 0
        failed_count = 0

        # 将文档分块处理
        chunks = self.chunk_document(content, max_chunk_size=1000)

        for i, chunk in enumerate(chunks):
            if not chunk.strip():
                continue

            # 为每个块创建唯一标题
            title = f"{base_title}_CHUNK_{i+1}"

            # 检查是否已存在同名条目
            if title in self.items:
                # 添加时间戳确保唯一性
                title = f"{title}_{int(time.time())}"

            # 尝试生成向量
            vector_id = None
            if hasattr(self, 'vector_db') and self.vector_db and self.vector_db.check_model_ready():
                try:
                    vector = self.vector_db.encode_text(chunk)

                    if vector is not None:
                        # 添加到向量数据库
                        vector_id = self.vector_db.add(chunk, vector, {
                            'title': title,
                            'type': 'document_chunk',
                            'source': file_path,
                            'chunk_index': i
                        })
                except Exception as e:
                    print(f"向量处理出错: {e}")

            # 添加到知识条目
            self.items[title] = {
                'content': chunk,
                'vector_id': vector_id,
                'metadata': {
                    'imported_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'source': file_path,
                    'type': 'document_chunk',
                    'chunk_index': i,
                    'title': f"文档片段 {i+1}"
                }
            }

            if vector_id:
                success_count += 1
            else:
                failed_count += 1

        # 保存知识库
        self.save()

        return True, f"已导入 {success_count} 个文档片段 (其中 {failed_count} 个无向量索引)"

    def _parse_qa_content(self, content):
        """解析问答格式内容为多个QA组"""
        qa_groups = []

        # 按空行分割为多个问答组
        blocks = re.split(r'\n\s*\n', content)

        for block in blocks:
            if not block.strip():
                continue

            lines = block.split('\n')
            qa_group = {
                'full_text': block,
                'question': '',
                'similar_questions': '',
                'answer': ''
            }

            # 解析问题、相似问和答案
            current_section = None
            for line in lines:
                line = line.strip()
                if not line:
                    continue

                if line.startswith('问题:') or line.startswith('问题：'):
                    current_section = 'question'
                    qa_group['question'] = line.split(':', 1)[1].strip() if ':' in line else line.split('：', 1)[1].strip()
                elif line.startswith('相似问:') or line.startswith('相似问：'):
                    current_section = 'similar_questions'
                    qa_group['similar_questions'] = line.split(':', 1)[1].strip() if ':' in line else line.split('：', 1)[1].strip()
                elif line.startswith('答案:') or line.startswith('答案：'):
                    current_section = 'answer'
                    qa_group['answer'] = line.split(':', 1)[1].strip() if ':' in line else line.split('：', 1)[1].strip()
                elif current_section:
                    # 添加到当前部分
                    qa_group[current_section] += '\n' + line

            # 只添加有问题和答案的组
            if qa_group['question'] and qa_group['answer']:
                qa_groups.append(qa_group)

        return qa_groups

    def chunk_document(self, content, max_chunk_size=1000):
        """将文档分成小块"""
        if len(content) <= max_chunk_size:
            return [content]

        # 按段落分割
        paragraphs = re.split(r'\n\s*\n', content)

        chunks = []
        current_chunk = ""

        for para in paragraphs:
            if len(current_chunk) + len(para) <= max_chunk_size:
                current_chunk += para + "\n\n"
            else:
                # 如果当前段落加上当前块超过最大块大小
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = para + "\n\n"

        # 添加最后一个块
        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks

    def get_relevant_knowledge(self, query, max_items=3):
        """获取与查询相关的知识条目"""
        items = self.search(query, max_items)

        if not items:
            return ""

        # 拼接相关知识内容
        knowledge = ""
        for item in items:
            content = self.get_item(item)
            if content:
                knowledge += f"--- {item} ---\n{content}\n\n"

        return knowledge.strip()

    def save(self):
        """保存知识库"""
        # 保存向量数据库
        self.vector_db.save()

        # 保存知识条目索引
        save_path = os.path.join(self.knowledge_path, 'items.json')
        try:
            # 去除向量数据，只保存引用
            serializable_items = {}
            for name, item in self.items.items():
                serializable_items[name] = {
                    'vector_id': item['vector_id'],
                    'metadata': item['metadata']
                }

            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump(serializable_items, f, ensure_ascii=False, indent=4)
            return True
        except Exception as e:
            print(f"保存知识条目失败: {e}")
            return False

    def load(self):
        """加载知识条目"""
        knowledge_file = os.path.join(self.knowledge_path, 'items.json')

        if os.path.exists(knowledge_file):
            try:
                with open(knowledge_file, 'r', encoding='utf-8') as f:
                    self.items = json.load(f)
                print(f"已加载 {len(self.items)} 个知识条目")

                # 验证数据完整性
                self._validate_items()
                return True
            except Exception as e:
                print(f"加载知识条目失败: {e}")
                import traceback
                traceback.print_exc()

                # 尝试创建备份并重置
                try:
                    backup_file = f"{knowledge_file}.bak"
                    if os.path.exists(knowledge_file):
                        import shutil
                        shutil.copy2(knowledge_file, backup_file)
                        print(f"已创建知识库备份: {backup_file}")
                except Exception as be:
                    print(f"创建备份失败: {be}")

                # 重置知识条目
                self.items = {}
        else:
            print("知识库文件不存在，创建新的知识库")
            self.items = {}

        return False

    def _validate_items(self):
        """验证知识条目的完整性"""
        invalid_items = []
        for name, item in self.items.items():
            # 检查是否为字典
            if not isinstance(item, dict):
                print(f"警告: 知识条目 '{name}' 格式不正确，尝试修复")
                self.items[name] = {'content': str(item), 'metadata': {}}
                continue

            # 检查是否有content字段
            if 'content' not in item and not ('metadata' in item and item['metadata'].get('type') == 'qa_group'):
                print(f"警告: 知识条目 '{name}' 缺少内容字段")
                invalid_items.append(name)

        # 移除无效条目
        for name in invalid_items:
            print(f"移除无效知识条目: {name}")
            del self.items[name]

    def add_entry(self, title, content, vectors=None):
        """添加知识条目"""
        # 生成唯一ID
        entry_id = f"k_{len(self.entries)}_{int(time.time())}"

        # 如果没有提供向量，尝试生成
        if vectors is None and hasattr(self, 'vector_db') and self.vector_db:
            try:
                vectors = self.vector_db.encode_text(content)
            except Exception as e:
                print(f"生成向量失败: {e}")
                # 使用空向量
                vectors = np.zeros(768)  # 使用默认维度

        # 添加条目
        self.entries[entry_id] = {
            'title': title,
            'content': content,
            'vectors': vectors,
            'created_at': time.time()
        }

        # 如果有向量数据库，添加到向量数据库
        if hasattr(self, 'vector_db') and self.vector_db and vectors is not None:
            self.vector_db.add(content, vectors, {'id': entry_id, 'title': title})

        return entry_id

    def prepare_knowledge_context(self, query, max_items=3):
        """为问答准备知识上下文，返回相关的知识条目列表"""
        try:
            print(f"[DEBUG] 正在搜索与问题相关的知识: {query}")
            print(f"[DEBUG] 知识库类型: {type(self).__name__}")
            print(f"[DEBUG] 知识库方法: {[method for method in dir(self) if not method.startswith('_') and callable(getattr(self, method))]}")

            # 检查向量数据库模型是否就绪
            if not hasattr(self.vector_db, 'model') or not self.vector_db.model:
                print("[ERROR] 向量模型未加载")
                return []

            # 使用文本和向量相似度结合的搜索方法
            # 使用向量相似度搜索
            results = self.vector_db.search(query, top_k=max_items*2, min_similarity=0.4)

            # 转换结果格式
            formatted_results = []
            for result in results:
                # 处理不同格式的结果
                if isinstance(result, dict):
                    item = {
                        'content': result.get('content', ''),
                        'similarity': result.get('similarity', 0.0)
                    }
                elif isinstance(result, tuple) and len(result) >= 3:
                    vector_id, content, similarity = result
                    item = {
                        'content': content,
                        'similarity': similarity
                    }
                else:
                    continue

                # 添加有效结果
                if item['content']:
                    formatted_results.append(item)

            # 按相似度分数排序
            formatted_results.sort(key=lambda x: x.get('similarity', 0), reverse=True)

            # 取前max_items个最相关的结果
            top_results = formatted_results[:max_items]

            if top_results:
                # 打印调试信息
                print(f"[INFO] 找到 {len(top_results)} 条相关知识条目:")
                for i, item in enumerate(top_results, 1):
                    similarity = item.get('similarity', 0.0)
                    content_preview = item.get('content', '')[:50].replace('\n', ' ') + '...'
                    print(f"  {i}. 相似度: {similarity:.4f}, 内容: {content_preview}")
            else:
                print("[INFO] 未找到相关知识条目，回退到普通模式")

            return top_results

        except Exception as e:
            print(f"[ERROR] 准备知识上下文时出错: {e}")
            import traceback
            traceback.print_exc()
            return []

    def ensure_vectors(self):
        """确保所有知识条目都有对应的向量"""
        # 检查向量数据库和模型是否可用
        if not hasattr(self, 'vector_db') or not self.vector_db:
            print("错误: 向量数据库未初始化，无法创建向量")
            return False

        # 模型检查和尝试加载
        if not self.vector_db.check_model_ready():
            print("警告: 向量模型尚未加载，尝试自动加载...")
            # 尝试从主程序中获取向量模型
            try:
                from importlib import import_module
                try:
                    # 尝试从主程序中获取松瓷机电AI助手实例
                    module = import_module('AI_assistant')
                    if hasattr(module, 'assistant') and hasattr(module.assistant, '_load_bge_m3_model'):
                        print("调用主程序的模型加载函数...")
                        # 获取BGE-M3模型路径并尝试加载
                        model_path = self.vector_db.model_path if hasattr(self.vector_db, 'model_path') else os.path.join('BAAI', 'bge-m3')
                        model_result = module.assistant._load_bge_m3_model(model_path)
                        if not model_result:
                            print("模型加载失败，无法继续向量化")
                            return False
                    else:
                        print("未找到主程序中的模型加载函数")
                        return False
                except ImportError:
                    print("无法导入主程序模块")
                    return False
            except Exception as e:
                print(f"尝试自动加载模型失败: {e}")
                print("向量模型未正确加载，无法创建向量")
                return False

        # 再次确认模型已加载
        if not hasattr(self.vector_db, 'model') or not self.vector_db.model:
            print("向量模型加载状态异常，无法继续向量化")
            return False

        # 测试向量模型是否可用
        try:
            test_text = "模型测试文本"
            test_vector = self.vector_db.encode_text(test_text)
            if test_vector is None:
                print("向量模型测试失败，无法生成向量")
                return False
            print(f"向量模型测试成功，向量维度: {len(test_vector)}")
        except Exception as e:
            print(f"向量模型测试失败: {e}")
            return False

        # 遍历所有知识条目
        vectorized_count = 0
        error_count = 0
        for name, item in self.items.items():
            if 'vector_id' not in item or item.get('vector_id') is None:
                try:
                    # 使用内容创建向量
                    content = item.get('content', '')
                    if not content and isinstance(item, dict) and 'metadata' in item:
                        # 对于问答组类型，使用答案作为向量化内容
                        if item['metadata'].get('type') == 'qa_group':
                            content = item['metadata'].get('answer', '')

                    if content:
                        # 生成向量并保存ID
                        vector = self.vector_db.encode_text(content)
                        if vector is not None:
                            vector_id = self.vector_db.add(content, vector)
                            if vector_id:
                                self.items[name]['vector_id'] = vector_id
                                vectorized_count += 1
                        else:
                            print(f"为知识条目 '{name}' 生成向量失败")
                            error_count += 1
                except Exception as e:
                    print(f"为知识条目 '{name}' 创建向量时出错: {e}")
                    error_count += 1

        # 保存更新的知识条目和向量
        if vectorized_count > 0:
            print(f"已创建 {vectorized_count} 个知识条目的向量")
            if error_count > 0:
                print(f"处理失败 {error_count} 个知识条目")
            self.save()
            self.vector_db.save()
            return True
        elif error_count > 0:
            print(f"所有 {error_count} 个知识条目处理失败")
            return False
        else:
            print("所有知识条目均已有向量，无需处理")
            return True

    def debug_knowledge_files(self):
        """调试知识库文件路径和内容"""
        print("\n===== 知识库文件诊断 =====")

        vector_dir = os.path.join('data', 'vectors')
        print(f"向量数据目录: {os.path.abspath(vector_dir)}")
        if os.path.exists(vector_dir):
            files = os.listdir(vector_dir)
            print(f"目录中的文件: {files}")

            vector_file = os.path.join(vector_dir, 'vectors.json')
            if os.path.exists(vector_file):
                try:
                    import json
                    with open(vector_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    print(f"向量文件大小: {os.path.getsize(vector_file)} 字节")
                    print(f"向量文件结构: {type(data)}")
                    if isinstance(data, dict):
                        print(f"向量文件顶层键: {list(data.keys())}")
                        if 'vectors' in data:
                            print(f"vectors包含 {len(data['vectors'])} 项")
                        if 'collections' in data:
                            print(f"collections包含 {len(data['collections'])} 项")
                except Exception as e:
                    print(f"读取向量文件失败: {e}")
        else:
            print("向量数据目录不存在")

        # 检查当前知识库
        print("\n当前知识库状态:")
        print(f"知识条目数: {len(self.items) if hasattr(self, 'items') else '未初始化'}")
        if hasattr(self, 'vector_db'):
            print(f"向量数据库类型: {type(self.vector_db).__name__}")
            print(f"向量数据库方法: {[m for m in dir(self.vector_db) if callable(getattr(self.vector_db, m)) and not m.startswith('_')]}")

            if hasattr(self.vector_db, 'vectors'):
                print(f"向量数: {len(self.vector_db.vectors)}")
            if hasattr(self.vector_db, 'collections'):
                print(f"集合数: {len(self.vector_db.collections)}")
        else:
            print("向量数据库未初始化")

        print("===== 诊断完成 =====\n")

    def _scan_vectors(self):
        """扫描并诊断向量数据"""
        if not hasattr(self, 'vector_db'):
            print("向量数据库未初始化")
            return

        print("扫描向量数据...")

        # 检查vectors属性
        if hasattr(self.vector_db, 'vectors'):
            vectors_data = self.vector_db.vectors
            print(f"向量数据类型: {type(vectors_data)}")
            print(f"向量数量: {len(vectors_data) if vectors_data else 0}")

            # 抽样检查
            if vectors_data:
                sample_key = next(iter(vectors_data))
                sample_data = vectors_data[sample_key]
                print(f"样本向量ID: {sample_key}")
                print(f"样本数据类型: {type(sample_data)}")
                if isinstance(sample_data, dict):
                    print(f"样本数据键: {list(sample_data.keys())}")

                # 尝试重构向量数据结构
                if not isinstance(sample_data, dict) or 'vector' not in sample_data:
                    print("向量数据结构异常，尝试修复")
                    return False
        else:
            print("向量对象无vectors属性")
            return False

        return True