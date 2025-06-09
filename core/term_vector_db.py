import os
import json
import numpy as np
import uuid
from datetime import datetime
from core.vector_db import VectorDB

class TermVectorDB(VectorDB):
    """术语库专用向量数据库，继承自通用向量数据库"""
    
    def __init__(self, settings_or_path=None, model=None):
        """初始化术语向量数据库，使用独立的存储路径"""
        # 设置术语向量专用路径
        term_vector_path = os.path.join('data', 'term_vectors')
        
        # 调用父类初始化，但使用术语专用的存储路径
        super().__init__(term_vector_path, model)
        
        # 覆盖默认集合名，避免与知识库冲突
        self.default_collection = 'term_default'
        self.current_collection = self.default_collection
        
        # 确保默认集合存在
        if self.default_collection not in self.collections:
            self.collections[self.default_collection] = {
                'vectors': [],
                'texts': [],
                'metadata': []
            }
        
        print(f"[INFO] 术语向量数据库初始化，路径: {self.vector_path}")
    
    def search(self, query, top_k=15, min_similarity=0.3):
        """术语库专用搜索，降低相似度阈值以提高召回率"""
        return super().search(query, top_k, min_similarity)
    
    def add(self, text, vector, metadata=None):
        """添加术语向量时自动标记类型"""
        if metadata is None:
            metadata = {}
        
        # 添加术语类型标记
        if 'type' not in metadata:
            metadata['type'] = 'term'
            
        return super().add(text, vector, metadata)

    def load_vectors(self):
        """加载向量数据"""
        if os.path.exists(self.vector_file):
            try:
                with open(self.vector_file, 'r', encoding='utf-8') as f:
                    vectors = json.load(f)
                print(f"[INFO] 术语向量库加载成功，包含 {len(vectors)} 个向量")
                return vectors
            except Exception as e:
                print(f"[ERROR] 加载术语向量库失败: {e}")
                return {}
        else:
            print("[INFO] 术语向量库文件不存在，将创建新文件")
            return {}
    
    def save_vectors(self):
        """保存向量数据"""
        try:
            with open(self.vector_file, 'w', encoding='utf-8') as f:
                json.dump(self.vectors, f, ensure_ascii=False, indent=2)
            print(f"[INFO] 术语向量库保存成功，共 {len(self.vectors)} 个向量")
            return True
        except Exception as e:
            print(f"[ERROR] 保存术语向量库失败: {e}")
            return False
    
    def get_embedding(self, text):
        """获取文本的向量嵌入"""
        if not hasattr(self, 'model') or self.model is None:
            print("[ERROR] 向量模型未加载，无法生成向量")
            return None
        
        try:
            # 使用模型生成向量
            vector = self.model.encode([text])[0]
            return np.array(vector)
        except Exception as e:
            print(f"[ERROR] 生成术语向量失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def add_vector(self, vector_id, content, vector, metadata=None):
        """添加向量"""
        if not vector_id or vector is None:
            print("[ERROR] 添加向量失败: ID或向量为空")
            return False
        
        # 确保metadata是字典
        if metadata is None:
            metadata = {}
        
        # 添加时间戳
        metadata['added_time'] = datetime.now().isoformat()
        
        # 创建向量数据
        vector_data = {
            'content': content,
            'vector': vector.tolist() if hasattr(vector, 'tolist') else vector,
            'metadata': metadata
        }
        
        # 添加到向量库
        self.vectors[vector_id] = vector_data
        
        # 保存向量库
        return self.save_vectors()
    
    def remove_vector(self, vector_id):
        """删除向量"""
        if vector_id not in self.vectors:
            print(f"[ERROR] 删除向量失败: 向量ID '{vector_id}' 不存在")
            return False
        
        # 删除向量
        del self.vectors[vector_id]
        
        # 保存向量库
        return self.save_vectors()
    
    def search_similar(self, query, top_k=15):
        """搜索相似向量"""
        if not self.model:
            print("[ERROR] 向量模型未加载，无法搜索相似术语")
            return []
        
        try:
            # 生成查询向量
            query_vector = self.get_embedding(query)
            
            if query_vector is None:
                print("[ERROR] 生成查询向量失败")
                return []
            
            # 计算相似度
            results = []
            
            for vector_id, vector_data in self.vectors.items():
                vector = np.array(vector_data['vector'])
                similarity = self.cosine_similarity(query_vector, vector)
                
                results.append({
                    'id': vector_id,
                    'content': vector_data['content'],
                    'similarity': float(similarity),
                    'metadata': vector_data.get('metadata', {})
                })
            
            # 按相似度排序
            results.sort(key=lambda x: x['similarity'], reverse=True)
            
            # 返回top_k个结果
            return results[:top_k]
        
        except Exception as e:
            print(f"[ERROR] 搜索相似术语失败: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def cosine_similarity(self, vector_a, vector_b):
        """计算余弦相似度"""
        norm_a = np.linalg.norm(vector_a)
        norm_b = np.linalg.norm(vector_b)
        
        if norm_a == 0 or norm_b == 0:
            return 0
        
        return np.dot(vector_a, vector_b) / (norm_a * norm_b) 