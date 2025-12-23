import logging
import os
import re
import json
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
from backend.utils.text_client import get_text_chat_client
from backend.utils.logger import get_detailed_logger

logger = logging.getLogger(__name__)
detailed_logger = get_detailed_logger(__name__)


class OutlineService:
    def __init__(self, user_id: Optional[int] = None):
        logger.debug("初始化 OutlineService...")
        self.user_id = user_id
        self.text_config = self._load_text_config()
        self.client = self._get_client()
        self.prompt_template = self._load_prompt_template()
        logger.info(f"OutlineService 初始化完成，使用服务商: {self.text_config.get('active_provider')}")

    def _load_text_config(self) -> dict:
        """从数据库加载文本生成配置"""
        from backend.models import ProviderConfig

        logger.debug(f"从数据库加载文本配置 (user_id={self.user_id})...")

        # 查询用户的文本服务商配置
        query = ProviderConfig.query.filter_by(category='text')
        if self.user_id:
            query = query.filter_by(user_id=self.user_id)

        providers_db = query.all()

        if not providers_db:
            logger.warning("数据库中没有文本服务商配置")
            raise ValueError(
                "未找到任何文本生成服务商配置。\n"
                "解决方案：在系统设置页面添加文本生成服务商"
            )

        # 构建配置字典
        providers = {}
        active_provider = None

        for p in providers_db:
            config = {
                'type': p.provider_type,
                'api_key': p.api_key,
                'base_url': p.base_url,
                'model': p.model,
            }
            # 合并 extra_config
            if p.extra_config:
                try:
                    extra = json.loads(p.extra_config)
                    config.update(extra)
                except json.JSONDecodeError:
                    pass

            providers[p.name] = config

            if p.is_active:
                active_provider = p.name

        if not active_provider:
            logger.warning("没有激活的文本服务商")
            raise ValueError(
                "未找到激活的文本生成服务商。\n"
                "解决方案：在系统设置页面激活一个文本生成服务商"
            )

        logger.debug(f"文本配置加载成功: active={active_provider}, providers={list(providers.keys())}")

        return {
            'active_provider': active_provider,
            'providers': providers
        }

    def _get_client(self):
        """根据配置获取客户端"""
        active_provider = self.text_config.get('active_provider')
        providers = self.text_config.get('providers', {})

        if not providers:
            logger.error("未找到任何文本生成服务商配置")
            raise ValueError(
                "未找到任何文本生成服务商配置。\n"
                "解决方案：在系统设置页面添加文本生成服务商"
            )

        if active_provider not in providers:
            available = ', '.join(providers.keys())
            logger.error(f"文本服务商 [{active_provider}] 不存在，可用: {available}")
            raise ValueError(
                f"未找到文本生成服务商配置: {active_provider}\n"
                f"可用的服务商: {available}\n"
                "解决方案：在系统设置中选择一个可用的服务商"
            )

        provider_config = providers.get(active_provider, {})

        if not provider_config.get('api_key'):
            logger.error(f"文本服务商 [{active_provider}] 未配置 API Key")
            raise ValueError(
                f"文本服务商 {active_provider} 未配置 API Key\n"
                "解决方案：在系统设置页面编辑该服务商，填写 API Key"
            )

        logger.info(f"使用文本服务商: {active_provider} (type={provider_config.get('type')})")
        return get_text_chat_client(provider_config)

    def _load_prompt_template(self) -> str:
        prompt_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "prompts",
            "outline_prompt.txt"
        )
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read()

    def _parse_outline(self, outline_text: str) -> List[Dict[str, Any]]:
        # 按 <page> 分割页面（兼容旧的 --- 分隔符）
        if '<page>' in outline_text:
            pages_raw = re.split(r'<page>', outline_text, flags=re.IGNORECASE)
        else:
            # 向后兼容：如果没有 <page> 则使用 ---
            pages_raw = outline_text.split("---")

        pages = []

        for index, page_text in enumerate(pages_raw):
            page_text = page_text.strip()
            if not page_text:
                continue

            page_type = "content"
            type_match = re.match(r"\[(\S+)\]", page_text)
            if type_match:
                type_cn = type_match.group(1)
                type_mapping = {
                    "封面": "cover",
                    "内容": "content",
                    "总结": "summary",
                }
                page_type = type_mapping.get(type_cn, "content")

            pages.append({
                "index": index,
                "type": page_type,
                "content": page_text
            })

        return pages

    def generate_outline(
        self,
        topic: str,
        images: Optional[List[bytes]] = None
    ) -> Dict[str, Any]:
        start_time = time.time()

        try:
            # 记录开始
            has_images = images is not None and len(images) > 0
            image_count = len(images) if images else 0
            detailed_logger.log_outline_start(topic, has_images, image_count)

            # 构建提示词
            prompt = self.prompt_template.format(topic=topic)

            if has_images:
                prompt += f"\n\n注意：用户提供了 {image_count} 张参考图片，请在生成大纲时考虑这些图片的内容和风格。这些图片可能是产品图、个人照片或场景图，请根据图片内容来优化大纲，使生成的内容与图片相关联。"

            # 从配置中获取模型参数
            active_provider = self.text_config.get('active_provider', 'google_gemini')
            providers = self.text_config.get('providers', {})
            provider_config = providers.get(active_provider, {})

            model = provider_config.get('model', 'gemini-2.0-flash-exp')
            temperature = provider_config.get('temperature', 1.0)
            max_output_tokens = provider_config.get('max_output_tokens', 8000)

            # 记录 API 调用详情
            detailed_logger.log_outline_api_call(
                provider=active_provider,
                model=model,
                temperature=temperature,
                max_tokens=max_output_tokens,
                prompt_length=len(prompt)
            )

            # 调用 API
            outline_text = self.client.generate_text(
                prompt=prompt,
                model=model,
                temperature=temperature,
                max_output_tokens=max_output_tokens,
                images=images
            )

            # 解析结果
            pages = self._parse_outline(outline_text)

            # 记录成功
            elapsed = time.time() - start_time
            detailed_logger.log_outline_success(
                outline_length=len(outline_text),
                page_count=len(pages),
                elapsed_time=elapsed
            )

            return {
                "success": True,
                "outline": outline_text,
                "pages": pages,
                "has_images": has_images
            }

        except Exception as e:
            error_msg = str(e)

            # 确定错误类型
            error_type = "未知错误"
            if "api_key" in error_msg.lower() or "unauthorized" in error_msg.lower() or "401" in error_msg:
                error_type = "API 认证失败"
                detailed_error = (
                    f"API 认证失败。\n"
                    f"错误详情: {error_msg}\n"
                    "可能原因：\n"
                    "1. API Key 无效或已过期\n"
                    "2. API Key 没有访问该模型的权限\n"
                    "解决方案：在系统设置页面检查并更新 API Key"
                )
            elif "model" in error_msg.lower() or "404" in error_msg:
                error_type = "模型访问失败"
                detailed_error = (
                    f"模型访问失败。\n"
                    f"错误详情: {error_msg}\n"
                    "可能原因：\n"
                    "1. 模型名称不正确\n"
                    "2. 没有访问该模型的权限\n"
                    "解决方案：在系统设置页面检查模型名称配置"
                )
            elif "timeout" in error_msg.lower() or "连接" in error_msg:
                error_type = "网络连接失败"
                detailed_error = (
                    f"网络连接失败。\n"
                    f"错误详情: {error_msg}\n"
                    "可能原因：\n"
                    "1. 网络连接不稳定\n"
                    "2. API 服务暂时不可用\n"
                    "3. Base URL 配置错误\n"
                    "解决方案：检查网络连接，稍后重试"
                )
            elif "rate" in error_msg.lower() or "429" in error_msg or "quota" in error_msg.lower():
                error_type = "API 配额限制"
                detailed_error = (
                    f"API 配额限制。\n"
                    f"错误详情: {error_msg}\n"
                    "可能原因：\n"
                    "1. API 调用次数超限\n"
                    "2. 账户配额用尽\n"
                    "解决方案：等待配额重置，或升级 API 套餐"
                )
            else:
                detailed_error = (
                    f"大纲生成失败。\n"
                    f"错误详情: {error_msg}\n"
                    "可能原因：\n"
                    "1. Text API 配置错误或密钥无效\n"
                    "2. 网络连接问题\n"
                    "3. 模型无法访问或不存在\n"
                    "建议：在系统设置页面检查文本服务商配置"
                )

            # 记录详细错误
            detailed_logger.log_outline_error(error_msg, error_type)

            return {
                "success": False,
                "error": detailed_error
            }


def get_outline_service(user_id: Optional[int] = None) -> OutlineService:
    """
    获取大纲生成服务实例
    每次调用都创建新实例以确保配置是最新的

    Args:
        user_id: 用户 ID，用于加载用户特定的配置
    """
    return OutlineService(user_id=user_id)
