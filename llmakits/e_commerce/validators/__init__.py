"""
验证程序模块
包含HTML验证、字符串验证等功能
"""

from .html_validator import check_allowed_tags, check_tag_closing
from .string_validator import contains_chinese, remove_chinese

__all__ = [
    'check_allowed_tags',
    'check_tag_closing', 
    'contains_chinese',
    'remove_chinese'
]