import os

def create_data_directories():
    """创建应用程序所需的数据目录结构"""
    # 主数据目录
    data_dir = "data"
    
    # 子目录
    subdirs = [
        "knowledge",  # 知识库数据
        "terms",      # 术语库数据
        "vectors"     # 向量数据
    ]
    
    # 创建主目录
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        print(f"已创建目录: {data_dir}")
    
    # 创建子目录
    for subdir in subdirs:
        path = os.path.join(data_dir, subdir)
        if not os.path.exists(path):
            os.makedirs(path)
            print(f"已创建目录: {path}")

if __name__ == "__main__":
    create_data_directories()
    print("所有数据目录已创建完成!") 