#!/usr/bin/env python3
"""
自动化导入测试模块
用于测试所有__init__.py中暴露的方法是否能正常导入，避免循环引用问题
"""

import os
import sys
import importlib
import traceback
from pathlib import Path
from typing import List, Dict, Any


class ImportTester:
    """导入测试器"""

    def __init__(self, project_root: str = ""):
        """初始化测试器"""
        if not project_root:
            self.project_root = Path(__file__).parent.parent.parent
        else:
            self.project_root = Path(project_root)
        # pyright: ignore[reportArgumentType]

        self.llmakits_path = self.project_root / 'llmakits'
        self.results = []

    def find_all_init_files(self) -> List[Path]:
        """找到所有__init__.py文件"""
        init_files = []
        for root, dirs, files in os.walk(self.llmakits_path):
            # 跳过__pycache__目录
            dirs[:] = [d for d in dirs if d != '__pycache__']

            for file in files:
                if file == '__init__.py':
                    init_files.append(Path(root) / file)

        return sorted(init_files)

    def extract_exports_from_init(self, init_file: Path) -> List[str]:
        """从__init__.py中提取__all__列表"""
        exports = []
        try:
            with open(init_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # 简单的__all__提取逻辑
            lines = content.split('\n')
            in_all_list = False
            current_list = []

            for line in lines:
                line = line.strip()

                # 检测__all__定义开始
                if '__all__' in line and '=' in line:
                    if '[' in line:
                        in_all_list = True
                        # 提取当前行的内容
                        start_idx = line.find('[')
                        end_idx = line.rfind(']')

                        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                            # 同一行完成
                            list_content = line[start_idx + 1 : end_idx]
                            exports.extend(
                                [item.strip().strip("'\"") for item in list_content.split(',') if item.strip()]
                            )
                            in_all_list = False
                        else:
                            # 多行列表
                            if start_idx != -1:
                                list_part = line[start_idx + 1 :]
                                if ']' in list_part:
                                    # 当前行结束
                                    end_idx = list_part.find(']')
                                    list_content = list_part[:end_idx]
                                    exports.extend(
                                        [item.strip().strip("'\"") for item in list_content.split(',') if item.strip()]
                                    )
                                    in_all_list = False
                                else:
                                    current_list.append(list_part)
                            else:
                                current_list.append(line)
                    continue

                if in_all_list:
                    if ']' in line:
                        # 列表结束
                        end_idx = line.find(']')
                        current_list.append(line[:end_idx])

                        # 处理累积的内容
                        full_content = ''.join(current_list)
                        exports.extend([item.strip().strip("'\"") for item in full_content.split(',') if item.strip()])

                        in_all_list = False
                        current_list = []
                    else:
                        current_list.append(line)

            # 清理空字符串
            exports = [exp for exp in exports if exp]

        except Exception as e:
            print(f"读取文件 {init_file} 失败: {e}")
            return []

        return exports

    def get_module_path_from_file(self, init_file: Path) -> str:
        """从文件路径获取模块导入路径"""
        relative_path = init_file.relative_to(self.project_root)

        # 转换为模块路径
        module_parts = list(relative_path.parts[:-1])  # 移除文件名

        # 如果模块名是llmakits，直接使用
        if module_parts[0] == 'llmakits':
            return '.'.join(module_parts)
        else:
            # 添加llmakits前缀
            return 'llmakits.' + '.'.join(module_parts)

    def test_import_item(self, module_path: str, item_name: str) -> Dict[str, Any]:
        """测试单个导入项"""
        result = {
            'module_path': module_path,
            'item_name': item_name,
            'success': False,
            'error': None,
            'error_type': None,
        }

        try:
            # 动态导入模块
            module = importlib.import_module(module_path)

            # 尝试获取导入项
            if hasattr(module, item_name):
                result['success'] = True
            else:
                result['error'] = f"模块 {module_path} 中没有找到 {item_name}"
                result['error_type'] = 'AttributeError'

        except ImportError as e:
            result['error'] = str(e)
            result['error_type'] = 'ImportError'
            result['traceback'] = traceback.format_exc()

        except Exception as e:
            result['error'] = str(e)
            result['error_type'] = type(e).__name__
            result['traceback'] = traceback.format_exc()

        return result

    def run_all_tests(self) -> Dict[str, Any]:
        """运行所有导入测试"""
        print("🔍 开始扫描所有__init__.py文件...")
        init_files = self.find_all_init_files()
        print(f"📁 找到 {len(init_files)} 个__init__.py文件")

        all_results = []
        total_tests = 0
        failed_tests = 0

        for init_file in init_files:
            print(f"\n📄 处理文件: {init_file.relative_to(self.project_root)}")

            # 获取模块路径
            module_path = self.get_module_path_from_file(init_file)
            print(f"   模块路径: {module_path}")

            # 提取导出项
            exports = self.extract_exports_from_init(init_file)
            print(f"   发现 {len(exports)} 个导出项: {exports}")

            if not exports:
                print("   ⚠️  未找到导出项，跳过")
                continue

            # 测试每个导出项
            for item_name in exports:
                total_tests += 1
                print(f"   🧪 测试导入: {module_path}.{item_name}")

                result = self.test_import_item(module_path, item_name)
                all_results.append(result)

                if result['success']:
                    print("      ✅ 成功")
                else:
                    failed_tests += 1
                    print(f"      ❌ 失败: {result['error']}")
                    if 'traceback' in result:
                        print(f"      📋 错误详情: {result['traceback']}")

        # 汇总结果
        summary = {
            'total_tests': total_tests,
            'passed_tests': total_tests - failed_tests,
            'failed_tests': failed_tests,
            'success_rate': (total_tests - failed_tests) / total_tests * 100 if total_tests > 0 else 0,
            'all_results': all_results,
        }

        return summary

    def generate_report(self, summary: Dict[str, Any]) -> str:
        """生成测试报告"""
        report = []
        report.append("=" * 60)
        report.append("🧪 LLMAKits 导入测试报告")
        report.append("=" * 60)
        report.append(f"总测试数: {summary['total_tests']}")
        report.append(f"通过数: {summary['passed_tests']}")
        report.append(f"失败数: {summary['failed_tests']}")
        report.append(f"成功率: {summary['success_rate']:.1f}%")
        report.append("")

        if summary['failed_tests'] > 0:
            report.append("❌ 失败的测试:")
            for result in summary['all_results']:
                if not result['success']:
                    report.append(f"   - {result['module_path']}.{result['item_name']}: {result['error']}")
        else:
            report.append("✅ 所有测试均通过！")

        return "\n".join(report)


def main():
    """主函数"""
    print("🚀 启动LLMAKits导入测试...")

    # 创建测试器
    tester = ImportTester()

    # 运行所有测试
    summary = tester.run_all_tests()

    # 生成报告
    report = tester.generate_report(summary)
    print("\n" + report)

    # 保存详细结果到文件
    results_file = Path(__file__).parent / 'import_test_results.json'
    import json

    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f"\n💾 详细结果已保存到: {results_file}")

    # 返回退出码
    sys.exit(0 if summary['failed_tests'] == 0 else 1)


if __name__ == "__main__":
    main()
