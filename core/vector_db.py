import os
import pickle
import numpy as np
from datetime import datetime
import time
import traceback
import json

class VectorDB:
    """向量数据库类，用于存储和检索文本的向量表示"""

    def __init__(self, settings_or_path=None, model=None):
        """初始化向量数据库，支持Settings对象或直接路径"""
        # 判断settings_or_path参数类型，兼容两种初始化方式
        if hasattr(settings_or_path, 'get') and callable(settings_or_path.get):
            # 如果是Settings对象，从中获取向量路径配置
            self.settings = settings_or_path
            vector_path = os.path.join('data', 'vectors')
            try:
                # 尝试从设置中获取自定义路径
                custom_path = self.settings.get('vector_db_path')
                if custom_path and isinstance(custom_path, str):
                    vector_path = custom_path
            except:
                print("[WARNING] 无法从设置中读取向量数据库路径，使用默认路径")
        else:
            # 如果是字符串路径或None，直接使用
            self.settings = None
            vector_path = settings_or_path or os.path.join('data', 'vectors')

        # 设置向量存储路径
        self.vector_path = vector_path
        print(f"[INFO] 向量数据库路径: {self.vector_path}")
        os.makedirs(self.vector_path, exist_ok=True)

        # 初始化向量模型
        self.model = model

        # 初始化数据结构
        self.collections = {}  # 集合字典
        self.default_collection = 'default'  # 默认集合名
        self.vectors = {}  # 向量存储

        # 确保默认集合存在
        if self.default_collection not in self.collections:
            self.collections[self.default_collection] = {
                'vectors': [],
                'texts': [],
                'metadata': []
            }

        # 添加当前集合属性，解决搜索错误
        self.current_collection = self.default_collection

        # 加载现有向量
        self.load()

    def ensure_dir_exists(self, path):
        """确保目录存在"""
        if not os.path.exists(path):
            os.makedirs(path)

    def add_to_collection(self, text, collection_name=None, vector=None, metadata=None):
        """添加文本向量到指定集合"""
        if collection_name is None:
            collection_name = self.default_collection

        # 确保集合存在
        if collection_name not in self.collections:
            self.collections[collection_name] = {
                'vectors': [],
                'texts': [],
                'metadata': []
            }

        # 如果没有提供向量，生成向量
        if vector is None:
            vector = self.encode_text(text)
            if vector is None:
                print(f"无法为文本生成向量: {text[:30]}...")
                return None

        # 如果没有提供元数据，创建空元数据
        if metadata is None:
            metadata = {}

        # 生成ID
        vector_id = f"v_{collection_name}_{len(self.collections[collection_name]['vectors'])}_{int(time.time())}"
        metadata['id'] = vector_id

        # 添加到集合
        self.collections[collection_name]['vectors'].append(vector)
        self.collections[collection_name]['texts'].append(text)
        self.collections[collection_name]['metadata'].append(metadata)

        # 兼容旧版本 - 也添加到self.vectors
        self.vectors[vector_id] = {
            'text': text,
            'vector': vector,
            'metadata': metadata
        }

        return vector_id

    def add(self, text, vector=None, metadata=None):
        """添加文本向量到默认集合"""
        return self.add_to_collection(text, self.default_collection, vector, metadata)

    def get(self, vector_id):
        """获取向量"""
        return self.vectors.get(vector_id)

    def delete(self, vector_id):
        """删除向量"""
        if vector_id in self.vectors:
            del self.vectors[vector_id]
            return True
        return False

    def search(self, query, top_k=15, min_similarity=0.4):
        """优化的向量数据库搜索方法，修复空数据库问题"""
        try:
            print(f"[DEBUG] 向量数据库开始搜索: '{query[:50]}...' (top_k={top_k})")

            # 检查模型加载状态
            if not hasattr(self, 'model') or self.model is None:
                print("[ERROR] 向量模型未加载，无法执行搜索")
                return []

            # 获取查询向量
            query_vector = self.get_embedding(query)
            if query_vector is None:
                print("[ERROR] 无法获取查询向量")
                return []

            # 转换查询向量为numpy数组
            if not isinstance(query_vector, np.ndarray):
                query_vector = np.array(query_vector, dtype=np.float32)

            print(f"[DEBUG] 查询向量维度: {query_vector.shape}")

            # 调试向量数据库状态
            print(f"[DEBUG] 向量数据库结构: {type(self.vectors)}")
            print(f"[DEBUG] 向量集合: {list(self.collections.keys()) if hasattr(self, 'collections') else '无'}")

            # 尝试从集合和向量两种途径获取数据
            all_vectors = {}

            # 方法1: 从self.vectors直接获取
            if hasattr(self, 'vectors') and self.vectors:
                print(f"[DEBUG] 从vectors属性获取数据: {len(self.vectors)} 项")
                all_vectors.update(self.vectors)

            # 方法2: 从collections获取
            if hasattr(self, 'collections') and self.collections:
                print(f"[DEBUG] 尝试从collections获取数据")
                for coll_name, coll_data in self.collections.items():
                    # 每个集合中的向量数据
                    if isinstance(coll_data, dict) and 'vectors' in coll_data and 'texts' in coll_data:
                        vectors = coll_data['vectors']
                        texts = coll_data['texts']
                        metadata = coll_data.get('metadata', [{}] * len(vectors))

                        print(f"[DEBUG] 集合 {coll_name} 包含 {len(vectors)} 个向量")

                        # 将集合数据转换为向量字典
                        for i, (vector, text) in enumerate(zip(vectors, texts)):
                            vector_id = f"v_{coll_name}_{i}_{int(time.time())}"
                            all_vectors[vector_id] = {
                                'vector': vector,
                                'text': text,
                                'metadata': metadata[i] if i < len(metadata) else {}
                            }

            if not all_vectors:
                print("[ERROR] 无法获取任何向量数据")
                return []

            print(f"[DEBUG] 总共获取到 {len(all_vectors)} 个向量")

            # 计算相似度并返回结果
            results = []

            for vector_id, vector_data in all_vectors.items():
                if isinstance(vector_data, dict) and 'vector' in vector_data and 'text' in vector_data:
                    vector = vector_data['vector']
                    text = vector_data['text']
                    metadata = vector_data.get('metadata', {})

                    # 确保向量格式正确
                    if not isinstance(vector, np.ndarray):
                        try:
                            vector = np.array(vector, dtype=np.float32)
                        except:
                            print(f"[WARNING] 跳过无法转换的向量: {type(vector)}")
                            continue

                    # 处理可能的维度不匹配问题
                    if vector.shape != query_vector.shape:
                        print(f"[WARNING] 向量维度不匹配: {vector.shape} vs {query_vector.shape}")
                        continue

                    # 计算余弦相似度
                    similarity = self._cosine_similarity(query_vector, vector)

                    # 过滤低相似度结果
                    if similarity >= min_similarity:
                        results.append({
                            'vector_id': vector_id,
                            'content': text,
                            'similarity': similarity,
                            'metadata': metadata
                        })

            # 按相似度排序
            results.sort(key=lambda x: x['similarity'], reverse=True)

            # 限制返回数量
            results = results[:top_k]

            print(f"[DEBUG] 搜索完成，返回 {len(results)} 个结果")

            # 打印结果的相似度
            for i, res in enumerate(results[:5], 1):
                print(f"  结果 {i}: 相似度: {res['similarity']:.4f}")

            return results

        except Exception as e:
            import traceback
            print(f"[ERROR] 向量搜索失败: {e}")
            traceback.print_exc()
            return []

    def _cosine_similarity(self, vec1, vec2):
        """计算余弦相似度，确保向量格式正确"""
        try:
            # 确保向量是numpy数组
            if not isinstance(vec1, np.ndarray):
                vec1 = np.array(vec1, dtype=np.float32)
            if not isinstance(vec2, np.ndarray):
                vec2 = np.array(vec2, dtype=np.float32)

            # 确保维度一致
            if vec1.shape != vec2.shape:
                print(f"[WARNING] 向量维度不一致: {vec1.shape} vs {vec2.shape}")
                # 尝试调整维度
                if len(vec1.shape) == 2 and vec1.shape[0] == 1:
                    vec1 = vec1.flatten()
                if len(vec2.shape) == 2 and vec2.shape[0] == 1:
                    vec2 = vec2.flatten()

            # 计算余弦相似度
            dot_product = np.dot(vec1, vec2)
            norm_a = np.linalg.norm(vec1)
            norm_b = np.linalg.norm(vec2)

            if norm_a == 0 or norm_b == 0:
                return 0

            similarity = dot_product / (norm_a * norm_b)
            return similarity
        except Exception as e:
            print(f"[ERROR] 计算相似度失败: {e}")
            traceback.print_exc()
            return 0

    def save(self):
        """保存向量数据"""
        vector_file = os.path.join(self.vector_path, 'vectors.json')

        try:
            import json
            import numpy as np

            # 创建可序列化的数据结构 - 将NumPy数组转换为列表
            serializable_collections = {}

            for col_name, collection in self.collections.items():
                serializable_collections[col_name] = {
                    'vectors': [vector.tolist() if isinstance(vector, np.ndarray) else vector
                               for vector in collection['vectors']],
                    'texts': collection['texts'],
                    'metadata': collection['metadata']
                }

            # 使用新格式保存
            data = {
                'collections': serializable_collections,
                'default_collection': self.default_collection
            }

            with open(vector_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            print(f"向量数据已保存到: {vector_file}")
            return True
        except Exception as e:
            print(f"保存向量数据时出错: {e}")
            import traceback
            traceback.print_exc()
            return False

    def load(self):
        """加载向量数据，并确保数据结构正确"""
        vector_file = os.path.join(self.vector_path, 'vectors.json')

        # 调试信息：显示当前工作目录和文件路径
        current_dir = os.getcwd()
        abs_vector_file = os.path.abspath(vector_file)

        if not os.path.exists(vector_file):
            print(f"向量数据文件不存在: {vector_file}")
            print(f"当前工作目录: {current_dir}")
            print(f"绝对路径: {abs_vector_file}")
            print(f"文件是否存在(绝对路径): {os.path.exists(abs_vector_file)}")
            return False

        try:
            # 尝试加载向量数据
            with open(vector_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 检查数据结构并清理
            if isinstance(data, dict):
                # 检查collections和vectors属性
                if 'collections' in data:
                    self.collections = data['collections']
                    print(f"加载了 {len(self.collections)} 个向量集合")
                else:
                    print("加载的向量数据中无collections属性")
                    self.collections = {}

                if 'vectors' in data:
                    self.vectors = data['vectors']
                    print(f"加载了 {len(self.vectors)} 个向量项目")
                else:
                    print("加载的向量数据中无vectors属性")
                    self.vectors = {}

                # 检查两者是否为空，如果都为空，尝试将数据本身作为向量
                if not self.collections and not self.vectors:
                    print("尝试将整个数据作为向量集合")
                    # 如果数据结构看起来像向量集合
                    if all(isinstance(key, str) for key in data.keys()):
                        self.vectors = data
                        print(f"从直接数据加载了 {len(self.vectors)} 个向量")
            else:
                print(f"警告: 向量数据格式不是字典: {type(data)}")
                return False

            # 验证向量数据是否正确加载
            if not self.vectors:
                print("[WARNING] 向量数据加载失败或为空")
                # 如果vectors为空，但collections不为空，尝试从collections初始化vectors
                if self.collections:
                    print("尝试从collections创建vectors")
                    for coll_name, coll_data in self.collections.items():
                        if isinstance(coll_data, dict) and 'vectors' in coll_data and 'texts' in coll_data:
                            vectors = coll_data['vectors']
                            texts = coll_data['texts']
                            for i, (vector, text) in enumerate(zip(vectors, texts)):
                                vector_id = f"v_{coll_name}_{i}_{int(time.time())}"
                                self.vectors[vector_id] = {
                                    'vector': vector,
                                    'text': text,
                                    'metadata': {}
                                }
                    print(f"从collections创建了 {len(self.vectors)} 个向量")

            print(f"已加载向量数据库，包含 {len(self.vectors)} 个向量项目")
            return True
        except Exception as e:
            print(f"加载向量数据时出错: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _reset_data_structures(self):
        """重置数据结构"""
        print("重置向量数据库...")
        # 重置向量集合
        self.default_collection = "default"
        self.collections = {
            self.default_collection: {
                'vectors': [],
                'texts': [],
                'metadata': []
            }
        }

        # 重置向量字典
        self.vectors = {}

        # 重新保存为新文件
        try:
            self.save()
            print("向量数据库已重置并创建新的空数据文件")
        except Exception as e:
            print(f"重置向量数据库失败: {e}")

        return True

    def clear(self):
        """清空向量数据"""
        self.vectors = {}
        return True

    def set_model(self, model_info):
        """设置要使用的向量模型"""
        if not model_info:
            print("警告: 传入的向量模型信息为空")
            return False

        self.model_info = model_info
        self.model_path = model_info["path"]

        # 校准BGE-M3模型路径 - 检查模型文件是否存在
        if "bge-m3" in self.model_path.lower():
            # 获取项目根目录
            current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

            # 模型可能存在的路径
            potential_paths = [
                # 首选：应用内路径
                os.path.join(current_dir, "BAAI", "bge-m3"),
                # 其他可能的路径
                os.path.join(current_dir, "BAAI", "models", "BAAI", "bge-m3"),
                os.path.join("D:", "AI_project", "vllm_模型应用", "BAAI", "bge-m3")
            ]

            for path in potential_paths:
                if os.path.exists(path) and os.path.isdir(path):
                    # 检查关键文件是否存在
                    modules_path = os.path.join(path, "modules.json")
                    tokenizer_path = os.path.join(path, "tokenizer.json")

                    if os.path.exists(modules_path) and os.path.exists(tokenizer_path):
                        print(f"选择BGE-M3模型路径: {path}")
                        self.model_path = path
                        self.model_info["path"] = path
                        break

        print(f"开始加载向量模型: {self.model_path}")

        # 获取设备信息
        device = "cpu"
        if "device" in model_info:
            device = model_info["device"]
        else:
            # 自动检测设备
            try:
                import torch
                if torch.cuda.is_available():
                    device = "cuda"
                    print(f"自动选择GPU设备: {torch.cuda.get_device_name(0)}")
                else:
                    print("GPU不可用，使用CPU")
            except Exception as e:
                print(f"设备检测错误: {e}")

        # 检查模型是否已经提供
        if "model" in model_info and model_info["model"] is not None:
            print("使用提供的预加载模型")
            self.model = model_info["model"]
            self.model_type = model_info.get("type", "unknown")
            return True

        try:
            # 尝试加载BGE-M3模型
            if "bge-m3" in self.model_path.lower():
                print(f"检测到BGE-M3模型，路径: {self.model_path}")

                # 检查必要文件是否存在
                required_files = ["modules.json", "tokenizer.json", "config.json"]
                missing_files = []
                for file in required_files:
                    full_path = os.path.join(self.model_path, file)
                    if not os.path.exists(full_path):
                        missing_files.append(file)

                if missing_files:
                    print(f"模型文件缺失: {', '.join(missing_files)}")
                    return False

                # 直接使用SentenceTransformers加载
                try:
                    from sentence_transformers import SentenceTransformer
                    print(f"使用SentenceTransformers加载BGE-M3模型到{device}设备...")
                    self.model = SentenceTransformer(self.model_path, device=device)
                    self.model_type = "sentence-transformer"
                    print("成功加载BGE-M3模型")

                    # 测试模型
                    test_text = "这是一个测试句子"
                    try:
                        embedding = self.model.encode(test_text)
                        print(f"模型测试成功，向量维度: {len(embedding)}")
                    except Exception as e:
                        print(f"模型测试失败: {e}")
                        return False

                    return True
                except Exception as e:
                    print(f"使用SentenceTransformers加载失败: {e}")

                    # 备选方案：尝试使用FlagEmbedding
                    try:
                        from FlagEmbedding import BGEM3FlagModel
                        print(f"尝试使用FlagEmbedding加载BGE-M3模型...")
                        self.model = BGEM3FlagModel(self.model_path, device=device)
                        self.model_type = "bge-m3"
                        print("成功使用FlagEmbedding加载BGE-M3模型")
                        return True
                    except Exception as e2:
                        print(f"使用FlagEmbedding加载失败: {e2}")

                        # 尝试使用基础Transformers
                        try:
                            self._load_with_transformers(device)
                            return True
                        except Exception as e3:
                            print(f"所有加载方法都失败: {e3}")
                            print("请确保已安装必要的依赖：pip install sentence-transformers>=2.2.2 FlagEmbedding>=1.2.0")
                            return False
            else:
                # 其他类型的向量模型
                from sentence_transformers import SentenceTransformer
                self.model = SentenceTransformer(self.model_path)
                self.model_type = "sentence-transformer"
                print("成功加载向量模型")
                return True
        except Exception as e:
            print(f"加载向量模型最终失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _load_with_flagembedding(self):
        """使用FlagEmbedding加载BGE-M3模型"""
        # 导入BGEM3FlagModel
        from FlagEmbedding import BGEM3FlagModel

        # 加载BGE-M3模型
        print(f"使用FlagEmbedding加载BGE-M3模型，路径: {self.model_path}")
        self.model = BGEM3FlagModel(
            self.model_path,
            use_fp16=True  # 使用FP16加速
        )
        print("成功加载BGE-M3模型!")
        self.model_type = "bge-m3"

    def _load_with_sentence_transformers(self):
        """使用SentenceTransformers加载模型"""
        from sentence_transformers import SentenceTransformer
        print(f"使用SentenceTransformers加载模型: {self.model_path}")
        self.model = SentenceTransformer(self.model_path)
        print("成功使用SentenceTransformers加载模型")
        self.model_type = "sentence-transformer"

    def _load_with_transformers(self, device):
        """使用Transformers直接加载模型"""
        from transformers import AutoModel, AutoTokenizer
        import torch

        print(f"使用Transformers加载模型: {self.model_path}")
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_path)
        self.hf_model = AutoModel.from_pretrained(self.model_path)

        # 创建一个兼容encode方法的包装
        def encode_function(texts):
            # 确保输入是列表
            if isinstance(texts, str):
                texts = [texts]

            # 编码
            inputs = self.tokenizer(texts, padding=True, truncation=True, return_tensors="pt")
            with torch.no_grad():
                outputs = self.hf_model(**inputs)

            # 使用最后一层的[CLS]向量作为句子表示
            embeddings = outputs.last_hidden_state[:, 0]
            # 归一化
            embeddings = torch.nn.functional.normalize(embeddings, p=2, dim=1)

            # 如果只有一个输入，返回单个向量
            if len(texts) == 1:
                return embeddings[0].numpy()
            return embeddings.numpy()

        # 将encode方法附加到自身
        self.model = type('', (), {})()
        self.model.encode = encode_function

        print("成功使用Transformers加载模型")
        self.model_type = "transformers"

    def check_model_ready(self):
        """检查模型是否准备就绪"""
        if not hasattr(self, 'model') or self.model is None:
            if hasattr(self, 'model_info') and self.model_info:
                # 尝试重新加载模型
                print("重新尝试加载向量模型...")
                return self.set_model(self.model_info)
            else:
                # 尝试检查是否存在BGE-M3模型
                print("尝试查找BGE-M3模型...")

                # 获取当前脚本所在的目录
                current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

                # 优先搜索项目内部的模型路径
                bge_paths = [
                    os.path.join(current_dir, "BAAI", "models", "BAAI", "bge-m3"),  # 项目内
                    os.path.join(current_dir, "BAAI", "bge-m3"),                    # 项目内简化路径
                    os.path.join("D:", "AI_project", "vllm_模型应用", "BAAI", "models", "BAAI", "bge-m3"),  # 绝对路径
                    os.path.join("D:", "AI_project", "BAAI", "models", "BAAI", "bge-m3")  # 旧路径
                ]

                for path in bge_paths:
                    if os.path.exists(path):
                        print(f"找到BGE-M3模型: {path}")
                        model_info = {
                            "name": "BGE-M3",
                            "path": path,
                            "type": "embedding"
                        }
                        self.model_info = model_info
                        return self.set_model(model_info)

                print("未找到BGE-M3模型")
                return False
        return True

    def encode_text(self, text):
        """编码文本为向量，优化版本支持多种模型类型"""
        # 检查参数
        if not text or not isinstance(text, str):
            print(f"警告: 无效文本输入: {type(text)}")
            return None

        # 检查模型是否就绪
        if not self.check_model_ready():
            print("错误: 向量模型未就绪，无法进行编码")
            return None

        try:
            # 处理不同类型的模型
            if hasattr(self, 'model_type'):
                print(f"使用{self.model_type}类型模型编码文本...")

                if self.model_type == "bge-m3":
                    # BGE-M3特殊处理
                    try:
                        output = self.model.encode(
                            text,
                            return_dense=True,
                            return_sparse=False,
                            return_colbert_vecs=False
                        )
                        return output['dense'] if isinstance(output, dict) and 'dense' in output else output
                    except Exception as e:
                        print(f"BGE-M3高级编码失败: {e}，尝试基本编码方式")
                        try:
                            return self.model.encode(text)
                        except Exception as e2:
                            print(f"BGE-M3基本编码也失败: {e2}")
                            return None

                elif self.model_type == "sentence-transformer":
                    # SentenceTransformers处理
                    try:
                        # 尝试规范输入格式
                        if isinstance(text, list):
                            vectors = self.model.encode(text)
                            return vectors
                        else:
                            vector = self.model.encode(text)
                            return vector
                    except Exception as e:
                        print(f"SentenceTransformers编码失败: {e}")
                        return None

                else:
                    # 其他类型的模型
                    print(f"使用通用方式处理{self.model_type}类型模型")

            # 默认编码方式
            try:
                return self.model.encode(text)
            except Exception as e:
                print(f"默认编码失败: {e}")

                # 尝试调整编码方式
                try:
                    if hasattr(self.model, 'encode') and callable(self.model.encode):
                        if isinstance(text, list):
                            return self.model.encode(text)
                        else:
                            return self.model.encode([text])[0]
                    elif hasattr(self.model, 'embedding') and callable(self.model.embedding):
                        return self.model.embedding(text)
                    else:
                        print("无法找到有效的编码方法")
                        return None
                except Exception as e2:
                    print(f"所有编码方法都失败: {e2}")
                    # 创建空向量作为替代
                    import numpy as np
                    print("返回空向量作为替代")
                    return np.zeros(768)  # 使用默认向量维度

        except Exception as e:
            print(f"编码文本过程中出现错误: {e}")
            import traceback
            traceback.print_exc()
            return None

    def compute_similarity(self, vec1, vec2):
        """兼容性方法 - 调用cosine_similarity"""
        return self._cosine_similarity(vec1, vec2)

    def get_embedding(self, text):
        """获取文本的向量嵌入"""
        if not self.model:
            print("向量模型未加载")
            return None

        try:
            # 确保输入是字符串类型
            if not isinstance(text, str):
                print(f"警告：输入文本不是字符串类型，正在转换 (类型: {type(text)})")
                text = str(text)

            # 使用已加载的模型创建嵌入向量
            if hasattr(self, 'model_type') and self.model_type == "bge-m3":
                print(f"使用BGE-M3模型编码文本: '{text[:30]}...'")
                try:
                    # 确保文本是列表格式，修复索引错误
                    output = self.model.encode([text],
                        return_dense=True,
                        return_sparse=True,
                        return_colbert_vecs=True
                    )
                    # 返回向量结果
                    if isinstance(output, dict) and 'dense' in output:
                        return output['dense']
                    # 如果返回的是列表（多个文本的嵌入）
                    elif isinstance(output, list) and len(output) > 0:
                        return output[0]
                    else:
                        print(f"意外的输出格式: {type(output)}")
                        return None
                except Exception as e:
                    print(f"BGE-M3编码失败，尝试基本编码: {e}")
                    import traceback
                    traceback.print_exc()
                    # 基本编码模式
                    return self.model.encode([text])[0]  # 确保输入是列表
            else:
                # 通用向量模型
                print(f"使用通用向量模型编码文本: '{text[:30]}...'")
                return self.model.encode([text])[0]  # 确保输入是列表
        except Exception as e:
            print(f"编码文本失败: {e}")
            import traceback
            traceback.print_exc()
            return None

    def get_collection(self, collection_name=None):
        """获取向量集合"""
        # 确保collections字典存在
        if not hasattr(self, 'collections'):
            self.collections = {}

        # 确保default_collection属性存在
        if not hasattr(self, 'default_collection'):
            self.default_collection = "default"

        # 使用提供的集合名或默认集合
        if collection_name is None:
            collection_name = self.default_collection

        # 检查集合是否存在
        if collection_name in self.collections:
            return self.collections[collection_name]
        else:
            print(f"警告: 集合 '{collection_name}' 不存在，返回默认集合")
            # 创建并返回默认集合
            if self.default_collection not in self.collections:
                self.collections[self.default_collection] = {
                    'vectors': [],
                    'texts': [],
                    'metadata': []
                }
            return self.collections[self.default_collection]

    def _fix_empty_collections(self):
        """修复空集合问题 - 将旧数据迁移到集合中"""
        if hasattr(self, 'vectors') and self.vectors and hasattr(self, 'collections'):
            # 检查集合是否为空
            is_empty = True
            for collection in self.collections.values():
                if collection['vectors']:
                    is_empty = False
                    break

            # 如果集合为空但vectors不为空，则迁移数据
            if is_empty and self.vectors:
                print(f"检测到集合为空但有 {len(self.vectors)} 个向量数据，进行迁移...")

                # 确保默认集合存在
                if self.default_collection not in self.collections:
                    self.collections[self.default_collection] = {
                        'vectors': [],
                        'texts': [],
                        'metadata': []
                    }

                # 迁移数据
                migrated = 0
                for vector_id, item in self.vectors.items():
                    vector = item.get('vector')
                    if vector is None and 'dense' in item:
                        vector = item['dense']

                    if vector is not None:
                        text = item.get('text', '')
                        metadata = item.get('metadata', {})
                        metadata['id'] = vector_id

                        # 添加到默认集合
                        self.collections[self.default_collection]['vectors'].append(vector)
                        self.collections[self.default_collection]['texts'].append(text)
                        self.collections[self.default_collection]['metadata'].append(metadata)
                        migrated += 1

                print(f"已将 {migrated} 个向量从旧格式迁移到集合")

                # 保存更新后的集合
                self.save()
                return True

        return False

    def initialize(self):
        """初始化向量数据库"""
        # 导入必要的模块
        import os
        import json

        # 确保目录存在
        self.ensure_dir_exists(self.vector_path)

        # 检查向量文件是否存在，如果存在则尝试加载
        vector_file = os.path.join(self.vector_path, 'vectors.json')
        if os.path.exists(vector_file):
            try:
                # 尝试使用文本编辑器打开文件检查格式
                with open(vector_file, 'r', encoding='utf-8') as f:
                    try:
                        # 只尝试解析，不保存结果
                        json.load(f)
                    except json.JSONDecodeError:
                        print(f"向量数据文件已损坏，将创建新文件")
                        # 将损坏文件重命名为备份
                        backup_file = f"{vector_file}.corrupted"
                        try:
                            if os.path.exists(backup_file):
                                os.remove(backup_file)
                            os.rename(vector_file, backup_file)
                            print(f"已将损坏的文件重命名为: {backup_file}")
                        except Exception as re:
                            print(f"重命名损坏文件失败: {re}")
                            # 如果重命名失败，尝试直接删除
                            try:
                                os.remove(vector_file)
                                print(f"已删除损坏的文件: {vector_file}")
                            except Exception as de:
                                print(f"删除损坏文件失败: {de}")
            except Exception as e:
                print(f"检查向量数据文件时出错: {e}")

        # 加载向量数据
        self.load()

        # 修复集合问题
        self._fix_empty_collections()

        return True