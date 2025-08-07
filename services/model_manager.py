import json
import os
from typing import Dict, Any, Optional, List, Union
import logging
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_community.chat_models import ChatZhipuAI
from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.outputs import ChatResult, ChatGeneration
from langchain_core.messages import BaseMessage
from langchain_community.chat_models.moonshot import MoonshotChat

logger = logging.getLogger(__name__)

class LangChainModelManager:
    """基于LangChain的统一模型管理器"""
    
    def __init__(self, config_path: str = "config/models_config.json"):
        self.config_path = config_path
        self.config = self._load_config()
        self.models: Dict[str, BaseChatModel] = {}
        self.task_models = {}
        self._initialize_models()
    
    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        with open(self.config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        return config
    
    def _save_config(self, config: Dict[str, Any]):
        """保存配置文件"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"保存配置文件失败: {e}")
    
    def _initialize_models(self):
        """初始化所有可用的模型"""
        default_models = self.config.get("default_models", {})

        try:
            for task, full_model_id in default_models.items():
                provider_name, model_id = full_model_id.split("/")
                provider_config = self.config["models"][provider_name]
                model_config = self.config["models"][provider_name]['models'][model_id]
                if full_model_id in self.models:
                    model = self.get_model(full_model_id)
                else:
                    model = self._create_model(provider_name, provider_config, model_config)
                
                if model:
                    self.task_models[task] = model
                    logger.info(f"成功初始化模型: {full_model_id}")
        except Exception as e:
            logger.error(f"初始化 {full_model_id} 模型失败: {e}")
        
    
    def _create_model(self, provider_name: str, provider_config: Dict[str, Any], 
                     model_config: Dict[str, Any]) -> Optional[BaseChatModel]:
        """创建具体的模型实例"""
        try:
            if provider_name == "openai":
                return ChatOpenAI(
                    api_key=provider_config["api_key"],
                    base_url=provider_config.get("base_url"),
                    model=model_config["model_name"],
                    temperature=model_config["temperature"],
                    max_tokens=model_config["max_tokens"]
                )
            
            elif provider_name == "anthropic":
                return ChatAnthropic(
                    api_key=provider_config["api_key"],
                    model=model_config["model_name"],
                    temperature=model_config["temperature"],
                    max_tokens=model_config["max_tokens"]
                )
            
            elif provider_name == "zhipu":
                return ChatZhipuAI(
                    api_key=provider_config["api_key"],
                    model=model_config["model_name"],
                    temperature=model_config["temperature"],
                    max_tokens=model_config["max_tokens"]
                )
            elif provider_name == "kimi":
                return MoonshotChat(
                    api_key=provider_config["api_key"],
                    model=model_config["model_name"],
                    #temperature=model_config["temperature"],
                    #max_tokens=model_config["max_tokens"]
                )
            elif provider_name in ["qwen"]:
                # 使用自定义模型类
                return CustomChatModel(
                    api_key=provider_config["api_key"],
                    base_url=provider_config["base_url"],
                    model_name=model_config["model_name"],
                    temperature=model_config["temperature"],
                    max_tokens=model_config["max_tokens"]
                )
            
            elif provider_name == "aihubmix":
                # 使用OpenAI兼容接口处理aihubmix
                return ChatOpenAI(
                    api_key=provider_config["api_key"],
                    base_url=provider_config["base_url"],
                    model=model_config["model_name"],
                    temperature=model_config.get("temperature", 0.3),
                    #max_tokens=model_config.get("max_tokens", 4000)
                )
            
            else:
                logger.warning(f"不支持的模型提供商: {provider_name}")
                return None
                
        except Exception as e:
            logger.error(f"创建模型失败 {provider_name}: {e}")
            return None
    
    def get_model(self, model_id: str) -> Optional[BaseChatModel]:
        """获取指定的模型实例"""
        return self.models.get(model_id)
    
    def invoke_model(self, model_id: str, messages: Union[str, List[Dict[str, str]]], 
                    **kwargs) -> str:
        """调用指定模型"""
        model = self.get_model(model_id)
        if not model:
            raise ValueError(f"模型 {model_id} 不可用")
        
        # 转换消息格式
        if isinstance(messages, str):
            langchain_messages = [HumanMessage(content=messages)]
        else:
            langchain_messages = []
            for msg in messages:
                if msg["role"] == "system":
                    langchain_messages.append(SystemMessage(content=msg["content"]))
                elif msg["role"] == "user":
                    langchain_messages.append(HumanMessage(content=msg["content"]))
                elif msg["role"] == "assistant":
                    langchain_messages.append(AIMessage(content=msg["content"]))
        
        # 调用模型
        try:
            response = model.invoke(langchain_messages, **kwargs)
            return response.content
        except Exception as e:
            logger.error(f"调用模型 {model_id} 失败: {e}")
            raise
    
    def get_default_model(self, task: str) -> str:
        """获取指定任务的默认模型"""
        return self.config["default_models"].get(task, "openai/gpt-4")

    def invoke_task_model(self, task: str, messages: Union[str, List[Dict[str, str]]], 
                         **kwargs) -> str:
        """使用任务特定的模型进行调用"""
        model = self.task_models.get(task)
        
        # 转换消息格式
        if isinstance(messages, str):
            langchain_messages = [HumanMessage(content=messages)]
        else:
            langchain_messages = []
            for msg in messages:
                if msg["role"] == "system":
                    langchain_messages.append(SystemMessage(content=msg["content"]))
                elif msg["role"] == "user":
                    langchain_messages.append(HumanMessage(content=msg["content"]))
                elif msg["role"] == "assistant":
                    langchain_messages.append(AIMessage(content=msg["content"]))
        
        # 调用模型
        try:
            response = model.invoke(langchain_messages, **kwargs)
            return response.content
        except Exception as e:
            task_model_id = self.get_default_model(task)
            logger.error(f"调用任务 '{task}' 的模型失败: {e}，模型ID: {task_model_id}")
            raise
