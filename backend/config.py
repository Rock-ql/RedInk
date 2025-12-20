"""
配置管理模块 - SQLAlchemy 实现
"""
import logging
import json
from pathlib import Path

logger = logging.getLogger(__name__)


class Config:
    """应用配置类"""
    DEBUG = True
    HOST = '0.0.0.0'
    PORT = 12398
    CORS_ORIGINS = ['http://localhost:5173', 'http://localhost:3000']
    OUTPUT_DIR = 'output'

    # 配置缓存
    _image_providers_config = None
    _text_providers_config = None

    @classmethod
    def _get_providers_from_db(cls, category: str) -> dict:
        """
        从数据库获取服务商配置

        Args:
            category: 配置类别 ('text' 或 'image')

        Returns:
            配置字典，格式与原 YAML 结构一致
        """
        from backend.models import ProviderConfig

        providers = ProviderConfig.query.filter_by(category=category).all()

        if not providers:
            return {
                'active_provider': '',
                'providers': {}
            }

        # 构建配置字典
        result = {
            'active_provider': '',
            'providers': {}
        }

        for p in providers:
            if p.is_active:
                result['active_provider'] = p.name

            # 解析额外配置
            extra = json.loads(p.extra_config) if p.extra_config else {}

            # 构建服务商配置
            provider_config = {
                'type': p.provider_type,
                'api_key': p.api_key or '',
                'model': p.model,
                **extra
            }

            if p.base_url:
                provider_config['base_url'] = p.base_url

            # 移除空值
            provider_config = {k: v for k, v in provider_config.items() if v is not None}

            result['providers'][p.name] = provider_config

        return result

    @classmethod
    def load_image_providers_config(cls):
        """加载图片生成服务商配置"""
        if cls._image_providers_config is not None:
            return cls._image_providers_config

        logger.debug("从数据库加载图片服务商配置")
        cls._image_providers_config = cls._get_providers_from_db('image')

        if cls._image_providers_config['providers']:
            logger.debug(f"图片配置加载成功: {list(cls._image_providers_config['providers'].keys())}")
        else:
            logger.warning("未配置任何图片服务商")

        return cls._image_providers_config

    @classmethod
    def load_text_providers_config(cls):
        """加载文本生成服务商配置"""
        if cls._text_providers_config is not None:
            return cls._text_providers_config

        logger.debug("从数据库加载文本服务商配置")
        cls._text_providers_config = cls._get_providers_from_db('text')

        if cls._text_providers_config['providers']:
            logger.debug(f"文本配置加载成功: {list(cls._text_providers_config['providers'].keys())}")
        else:
            logger.warning("未配置任何文本服务商")

        return cls._text_providers_config

    @classmethod
    def get_active_image_provider(cls):
        """获取当前激活的图片服务商名称"""
        config = cls.load_image_providers_config()
        active = config.get('active_provider', '')
        logger.debug(f"当前激活的图片服务商: {active}")
        return active

    @classmethod
    def get_active_text_provider(cls):
        """获取当前激活的文本服务商名称"""
        config = cls.load_text_providers_config()
        active = config.get('active_provider', '')
        logger.debug(f"当前激活的文本服务商: {active}")
        return active

    @classmethod
    def get_image_provider_config(cls, provider_name: str = None):
        """
        获取图片服务商配置

        Args:
            provider_name: 服务商名称，为 None 时使用当前激活的服务商

        Returns:
            服务商配置字典

        Raises:
            ValueError: 配置不存在或不完整
        """
        config = cls.load_image_providers_config()

        if provider_name is None:
            provider_name = cls.get_active_image_provider()

        logger.info(f"获取图片服务商配置: {provider_name}")

        providers = config.get('providers', {})
        if not providers:
            raise ValueError(
                "未找到任何图片生成服务商配置。\n"
                "解决方案：\n"
                "1. 在系统设置页面添加图片生成服务商\n"
                "2. 确保已配置并激活服务商"
            )

        if provider_name not in providers:
            available = ', '.join(providers.keys()) if providers else '无'
            logger.error(f"图片服务商 [{provider_name}] 不存在，可用服务商: {available}")
            raise ValueError(
                f"未找到图片生成服务商配置: {provider_name}\n"
                f"可用的服务商: {available}\n"
                "解决方案：\n"
                "1. 在系统设置页面添加该服务商\n"
                "2. 或修改激活的服务商为已存在的服务商"
            )

        provider_config = providers[provider_name].copy()

        # 验证必要字段
        if not provider_config.get('api_key'):
            logger.error(f"图片服务商 [{provider_name}] 未配置 API Key")
            raise ValueError(
                f"服务商 {provider_name} 未配置 API Key\n"
                "解决方案：在系统设置页面编辑该服务商，填写 API Key"
            )

        provider_type = provider_config.get('type', provider_name)
        if provider_type in ['openai', 'openai_compatible', 'image_api']:
            if not provider_config.get('base_url'):
                logger.error(f"服务商 [{provider_name}] 类型为 {provider_type}，但未配置 base_url")
                raise ValueError(
                    f"服务商 {provider_name} 未配置 Base URL\n"
                    f"服务商类型 {provider_type} 需要配置 base_url\n"
                    "解决方案：在系统设置页面编辑该服务商，填写 Base URL"
                )

        logger.info(f"图片服务商配置验证通过: {provider_name} (type={provider_type})")
        return provider_config

    @classmethod
    def get_text_provider_config(cls, provider_name: str = None):
        """
        获取文本服务商配置

        Args:
            provider_name: 服务商名称，为 None 时使用当前激活的服务商

        Returns:
            服务商配置字典

        Raises:
            ValueError: 配置不存在或不完整
        """
        config = cls.load_text_providers_config()

        if provider_name is None:
            provider_name = cls.get_active_text_provider()

        logger.info(f"获取文本服务商配置: {provider_name}")

        providers = config.get('providers', {})
        if not providers:
            raise ValueError(
                "未找到任何文本生成服务商配置。\n"
                "解决方案：\n"
                "1. 在系统设置页面添加文本生成服务商\n"
                "2. 确保已配置并激活服务商"
            )

        if provider_name not in providers:
            available = ', '.join(providers.keys()) if providers else '无'
            logger.error(f"文本服务商 [{provider_name}] 不存在，可用服务商: {available}")
            raise ValueError(
                f"未找到文本生成服务商配置: {provider_name}\n"
                f"可用的服务商: {available}\n"
                "解决方案：\n"
                "1. 在系统设置页面添加该服务商\n"
                "2. 或修改激活的服务商为已存在的服务商"
            )

        provider_config = providers[provider_name].copy()

        # 验证必要字段
        if not provider_config.get('api_key'):
            logger.error(f"文本服务商 [{provider_name}] 未配置 API Key")
            raise ValueError(
                f"服务商 {provider_name} 未配置 API Key\n"
                "解决方案：在系统设置页面编辑该服务商，填写 API Key"
            )

        logger.info(f"文本服务商配置验证通过: {provider_name}")
        return provider_config

    @classmethod
    def reload_config(cls):
        """重新加载配置（清除缓存）"""
        logger.info("重新加载所有配置...")
        cls._image_providers_config = None
        cls._text_providers_config = None
