"""
配置管理相关 API 路由 - SQLAlchemy 实现

包含功能：
- 获取当前配置
- 更新配置
- 测试服务商连接
"""

import logging
import json
from flask import Blueprint, request, jsonify
from backend.models import db, ProviderConfig
from backend.config import Config
from .utils import prepare_providers_for_response

logger = logging.getLogger(__name__)


def create_config_blueprint():
    """创建配置路由蓝图（工厂函数，支持多次调用）"""
    config_bp = Blueprint('config', __name__)

    # ==================== 配置读写 ====================

    @config_bp.route('/config', methods=['GET'])
    def get_config():
        """
        获取当前配置

        返回：
        - success: 是否成功
        - config: 配置对象
          - text_generation: 文本生成配置
          - image_generation: 图片生成配置
        """
        try:
            # 从数据库读取图片生成配置
            image_config = _get_config_from_db('image')

            # 从数据库读取文本生成配置
            text_config = _get_config_from_db('text')

            return jsonify({
                "success": True,
                "config": {
                    "text_generation": {
                        "active_provider": text_config.get('active_provider', ''),
                        "providers": prepare_providers_for_response(
                            text_config.get('providers', {})
                        )
                    },
                    "image_generation": {
                        "active_provider": image_config.get('active_provider', ''),
                        "providers": prepare_providers_for_response(
                            image_config.get('providers', {})
                        )
                    }
                }
            })

        except Exception as e:
            logger.error(f"获取配置失败: {e}")
            return jsonify({
                "success": False,
                "error": f"获取配置失败: {str(e)}"
            }), 500

    @config_bp.route('/config', methods=['POST'])
    def update_config():
        """
        更新配置

        请求体：
        - image_generation: 图片生成配置（可选）
        - text_generation: 文本生成配置（可选）

        返回：
        - success: 是否成功
        - message: 结果消息
        """
        try:
            data = request.get_json()

            # 更新图片生成配置
            if 'image_generation' in data:
                _update_provider_config_in_db('image', data['image_generation'])

            # 更新文本生成配置
            if 'text_generation' in data:
                _update_provider_config_in_db('text', data['text_generation'])

            # 清除配置缓存
            _clear_config_cache()

            return jsonify({
                "success": True,
                "message": "配置已保存"
            })

        except Exception as e:
            logger.error(f"更新配置失败: {e}")
            return jsonify({
                "success": False,
                "error": f"更新配置失败: {str(e)}"
            }), 500

    # ==================== 连接测试 ====================

    @config_bp.route('/config/test', methods=['POST'])
    def test_connection():
        """
        测试服务商连接

        请求体：
        - type: 服务商类型（google_genai/google_gemini/openai_compatible/image_api）
        - provider_name: 服务商名称（用于从配置读取 API Key）
        - api_key: API Key（可选，若不提供则从配置读取）
        - base_url: Base URL（可选）
        - model: 模型名称（可选）

        返回：
        - success: 是否成功
        - message: 测试结果消息
        """
        try:
            data = request.get_json()
            provider_type = data.get('type')
            provider_name = data.get('provider_name')

            if not provider_type:
                return jsonify({"success": False, "error": "缺少 type 参数"}), 400

            # 构建配置
            config = {
                'api_key': data.get('api_key'),
                'base_url': data.get('base_url'),
                'model': data.get('model')
            }

            # 如果没有提供 api_key，从数据库读取
            if not config['api_key'] and provider_name:
                config = _load_provider_config_from_db(provider_type, provider_name, config)

            if not config['api_key']:
                return jsonify({"success": False, "error": "API Key 未配置"}), 400

            # 根据类型执行测试
            result = _test_provider_connection(provider_type, config)
            return jsonify(result), 200 if result['success'] else 400

        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 400

    return config_bp


# ==================== 数据库辅助函数 ====================

def _get_config_from_db(category: str) -> dict:
    """
    从数据库获取配置

    Args:
        category: 配置类别 ('text' 或 'image')

    Returns:
        配置字典
    """
    providers = ProviderConfig.query.filter_by(category=category).all()

    if not providers:
        return {
            'active_provider': '',
            'providers': {}
        }

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


def _update_provider_config_in_db(category: str, new_data: dict):
    """
    更新数据库中的服务商配置

    Args:
        category: 配置类别 ('text' 或 'image')
        new_data: 新的配置数据
    """
    # 更新 active_provider
    new_active = new_data.get('active_provider', '')

    # 先将所有服务商设为非激活
    if new_active:
        ProviderConfig.query.filter_by(category=category).update({'is_active': False})
        # 激活指定的服务商
        ProviderConfig.query.filter_by(category=category, name=new_active).update({'is_active': True})

    # 更新 providers
    if 'providers' in new_data:
        new_providers = new_data['providers']

        for name, provider_config in new_providers.items():
            # 查找现有记录
            existing = ProviderConfig.query.filter_by(category=category, name=name).first()

            # 处理 API Key：如果是空值，保留原有的
            api_key = provider_config.get('api_key')
            if api_key in [True, False, '', None]:
                if existing and existing.api_key:
                    api_key = existing.api_key
                else:
                    api_key = ''

            # 提取核心字段，其余放入 extra_config
            provider_type = provider_config.get('type', '')
            base_url = provider_config.get('base_url')
            model = provider_config.get('model')

            # 额外配置字段
            extra_fields = ['high_concurrency', 'short_prompt', 'default_aspect_ratio',
                           'temperature', 'max_output_tokens', 'image_size', 'endpoint_type']
            extra = {k: provider_config[k] for k in extra_fields if k in provider_config}

            is_active = (name == new_active)

            if existing:
                # 更新现有记录
                existing.provider_type = provider_type
                existing.api_key = api_key
                existing.base_url = base_url
                existing.model = model
                existing.is_active = is_active
                existing.extra_config = json.dumps(extra) if extra else None
            else:
                # 创建新记录
                new_provider = ProviderConfig(
                    category=category,
                    name=name,
                    provider_type=provider_type,
                    api_key=api_key,
                    base_url=base_url,
                    model=model,
                    is_active=is_active,
                    extra_config=json.dumps(extra) if extra else None
                )
                db.session.add(new_provider)

        # 删除不在新配置中的服务商
        existing_names = set(new_providers.keys())
        ProviderConfig.query.filter(
            ProviderConfig.category == category,
            ~ProviderConfig.name.in_(existing_names)
        ).delete(synchronize_session=False)

    db.session.commit()


def _load_provider_config_from_db(provider_type: str, provider_name: str, config: dict) -> dict:
    """
    从数据库加载服务商配置

    Args:
        provider_type: 服务商类型
        provider_name: 服务商名称
        config: 当前配置（会被合并）

    Returns:
        合并后的配置
    """
    # 确定配置类别
    if provider_type in ['openai_compatible', 'google_gemini']:
        category = 'text'
    else:
        category = 'image'

    provider = ProviderConfig.query.filter_by(category=category, name=provider_name).first()

    if provider:
        config['api_key'] = provider.api_key

        if not config.get('base_url'):
            config['base_url'] = provider.base_url
        if not config.get('model'):
            config['model'] = provider.model

    return config


def _clear_config_cache():
    """清除配置缓存"""
    try:
        Config.reload_config()
    except Exception:
        pass

    try:
        from backend.services.image import reset_image_service
        reset_image_service()
    except Exception:
        pass


# ==================== 连接测试函数 ====================

def _test_provider_connection(provider_type: str, config: dict) -> dict:
    """
    测试服务商连接

    Args:
        provider_type: 服务商类型
        config: 服务商配置

    Returns:
        测试结果
    """
    test_prompt = "请回复'你好，红墨'"

    if provider_type == 'google_genai':
        return _test_google_genai(config)

    elif provider_type == 'google_gemini':
        return _test_google_gemini(config, test_prompt)

    elif provider_type == 'openai_compatible':
        return _test_openai_compatible(config, test_prompt)

    elif provider_type == 'image_api':
        return _test_image_api(config)

    else:
        raise ValueError(f"不支持的类型: {provider_type}")


def _test_google_genai(config: dict) -> dict:
    """测试 Google GenAI 图片生成服务"""
    from google import genai

    if config.get('base_url'):
        client = genai.Client(
            api_key=config['api_key'],
            http_options={
                'base_url': config['base_url'],
                'api_version': 'v1beta'
            },
            vertexai=False
        )
        try:
            list(client.models.list())
            return {
                "success": True,
                "message": "连接成功！仅代表连接稳定，不确定是否可以稳定支持图片生成"
            }
        except Exception as e:
            raise Exception(f"连接测试失败: {str(e)}")
    else:
        return {
            "success": True,
            "message": "Vertex AI 无法通过 API Key 测试连接（需要 OAuth2 认证）。请在实际生成图片时验证配置是否正确。"
        }


def _test_google_gemini(config: dict, test_prompt: str) -> dict:
    """测试 Google Gemini 文本生成服务"""
    from google import genai

    if config.get('base_url'):
        client = genai.Client(
            api_key=config['api_key'],
            http_options={
                'base_url': config['base_url'],
                'api_version': 'v1beta'
            },
            vertexai=False
        )
    else:
        client = genai.Client(
            api_key=config['api_key'],
            vertexai=True
        )

    model = config.get('model') or 'gemini-2.0-flash-exp'
    response = client.models.generate_content(
        model=model,
        contents=test_prompt
    )
    result_text = response.text if hasattr(response, 'text') else str(response)

    return _check_response(result_text)


def _test_openai_compatible(config: dict, test_prompt: str) -> dict:
    """测试 OpenAI 兼容接口"""
    import requests

    base_url = config['base_url'].rstrip('/').rstrip('/v1') if config.get('base_url') else 'https://api.openai.com'
    url = f"{base_url}/v1/chat/completions"

    payload = {
        "model": config.get('model') or 'gpt-3.5-turbo',
        "messages": [{"role": "user", "content": test_prompt}],
        "max_tokens": 50
    }

    response = requests.post(
        url,
        headers={
            'Authorization': f"Bearer {config['api_key']}",
            'Content-Type': 'application/json'
        },
        json=payload,
        timeout=30
    )

    if response.status_code != 200:
        raise Exception(f"HTTP {response.status_code}: {response.text[:200]}")

    result = response.json()
    result_text = result['choices'][0]['message']['content']

    return _check_response(result_text)


def _test_image_api(config: dict) -> dict:
    """测试图片 API 连接"""
    import requests

    base_url = config['base_url'].rstrip('/').rstrip('/v1') if config.get('base_url') else 'https://api.openai.com'
    url = f"{base_url}/v1/models"

    response = requests.get(
        url,
        headers={'Authorization': f"Bearer {config['api_key']}"},
        timeout=30
    )

    if response.status_code == 200:
        return {
            "success": True,
            "message": "连接成功！仅代表连接稳定，不确定是否可以稳定支持图片生成"
        }
    else:
        raise Exception(f"HTTP {response.status_code}: {response.text[:200]}")


def _check_response(result_text: str) -> dict:
    """检查响应是否符合预期"""
    if "你好" in result_text and "红墨" in result_text:
        return {
            "success": True,
            "message": f"连接成功！响应: {result_text[:100]}"
        }
    else:
        return {
            "success": True,
            "message": f"连接成功，但响应内容不符合预期: {result_text[:100]}"
        }
