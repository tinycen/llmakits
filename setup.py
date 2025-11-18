from setuptools import setup, find_packages

# 读取README文件
try:
    with open('README.md', 'r', encoding='utf-8') as f:
        long_description = f.read()
except FileNotFoundError:
    long_description = ''

# 读取requirements.txt文件
try:
    with open('requirements.txt', 'r', encoding='utf-8') as f:
        install_requires = [line.strip() for line in f if line.strip() and not line.startswith('#')]
except FileNotFoundError:
    install_requires = []

setup(
    name='llmakits',
    version='0.6.23',
    packages=find_packages(),
    install_requires=install_requires,
    author='tinycen',
    author_email='sky_ruocen@qq.com',
    description='A powerful Python toolkit for simplifying LLM integration and management with multi-model scheduling, fault tolerance, and load balancing support',
    keywords='llm, ai, chatgpt, openai, zhipu, dashscope, modelscope, multi-model, scheduling, fault-tolerance',
    project_urls={
        'Source': 'https://github.com/tinycen/llmakits',
        'Documentation': 'https://github.com/tinycen/llmakits#readme',
        'Bug Reports': 'https://github.com/tinycen/llmakits/issues',
    },
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/tinycen/llmakits',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Scientific/Engineering :: Artificial Intelligence',
        'Topic :: Text Processing :: Linguistic',
    ],
    python_requires='>=3.10',
    extras_require={
        'dev': [
            'pytest>=6.0',
            'pytest-cov>=2.0',
            'black>=21.0',
            'flake8>=3.8',
            'mypy>=0.812',
        ],
    },
    include_package_data=True,
    zip_safe=False,
)
