"""解决typing.Self兼容性问题的补丁"""
import sys
import typing

# 检查是否已经有Self定义
if not hasattr(typing, 'Self'):
    # 为旧版本Python添加Self类型
    typing.Self = typing.TypeVar('Self', bound=object)
    # 将此类型添加到typing模块的__all__
    if hasattr(typing, '__all__'):
        typing.__all__ += ['Self']
    print("已添加typing.Self兼容补丁") 