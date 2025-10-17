#!/usr/bin/env python3
"""
ModelDispatcher导出配置示例

这个示例展示了如何使用ModelDispatcher的export_config方法
"""

from llmakits import ModelDispatcher


def main():
    print("=== ModelDispatcher配置导出示例 ===\n")

    # 1. 创建ModelDispatcher实例并加载配置
    print("1. 创建ModelDispatcher实例...")
    dispatcher = ModelDispatcher(
        models_config='example_configs/models_config.yaml',
        model_keys='example_configs/keys_config.yaml',
        global_config='example_configs/global_model_config.csv',
    )
    print("✓ ModelDispatcher实例创建成功\n")

    # 导出为JSON文件
    print("导出为JSON文件...")
    if dispatcher.export_config():
        print(f"✓ 基本导出成功")


if __name__ == "__main__":
    main()
