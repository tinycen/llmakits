from pathlib import Path
from .load_model import load_models
from .llm_client import BaseOpenai
from .dispatcher_control import dispatcher_with_repair
from .dispatcher import ModelDispatcher
from .prompt_manager import PromptManager

__version__ = (Path(__file__).parent / ".version").read_text().strip()

__all__ = ['__version__', 'load_models', 'dispatcher_with_repair',
            'BaseOpenai', 'ModelDispatcher', 'PromptManager']
