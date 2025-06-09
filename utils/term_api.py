"""术语库 API 接口，提供统一的术语功能访问点"""

import os
import sys
import json

def get_term_db_path():
    """获取术语库文件路径"""
    return os.path.join('data', 'terms', 'terms.json')

def get_term_vector_db_path():
    """获取术语向量库文件路径"""
    return os.path.join('data', 'term_vectors', 'vectors.json')

def load_terms():
    """加载术语库"""
    term_path = get_term_db_path()
    if os.path.exists(term_path):
        try:
            with open(term_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"加载术语库失败: {e}")
            return {}
    else:
        print("术语库文件不存在")
        return {}

def get_term_definition(term, source_lang='zh', target_lang='en'):
    """获取术语定义"""
    terms = load_terms()
    
    if term in terms:
        term_data = terms[term]
        
        # 检查语言匹配
        metadata = term_data.get('metadata', {})
        if (metadata.get('source_lang') == source_lang and 
            metadata.get('target_lang') == target_lang):
            return term_data.get('target_term', term_data.get('definition', ''))
    
    # 如果未找到或语言不匹配，返回空字符串
    return ""

def search_terms(query, max_results=10):
    """搜索术语库"""
    terms = load_terms()
    results = []
    
    query = query.lower()
    for term, term_data in terms.items():
        if query in term.lower():
            results.append({
                'source_term': term,
                'target_term': term_data.get('target_term', term_data.get('definition', '')),
                'metadata': term_data.get('metadata', {})
            })
            
            if len(results) >= max_results:
                break
    
    return results

def launch_term_tool():
    """启动术语工具"""
    from utils.term_tools import launch_emergency_term_tool
    return launch_emergency_term_tool() 