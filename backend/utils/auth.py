"""
认证工具函数

包含 JWT Token 生成/验证和密码加密/验证功能
"""
import os
import logging
from datetime import datetime, timedelta
from functools import wraps

import jwt
import bcrypt
from flask import request, jsonify, g

logger = logging.getLogger(__name__)

# JWT 配置
JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'redink-secret-key-change-in-production')
JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION_HOURS = 24 * 7  # Token 有效期 7 天


def hash_password(password: str) -> str:
    """
    使用 bcrypt 加密密码

    Args:
        password: 明文密码

    Returns:
        加密后的密码哈希
    """
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')


def verify_password(password: str, password_hash: str) -> bool:
    """
    验证密码是否正确

    Args:
        password: 明文密码
        password_hash: 数据库中的密码哈希

    Returns:
        密码是否匹配
    """
    try:
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
    except Exception as e:
        logger.error(f"密码验证失败: {e}")
        return False


def generate_token(user_id: int, username: str) -> str:
    """
    生成 JWT Token

    Args:
        user_id: 用户 ID
        username: 用户名

    Returns:
        JWT Token 字符串
    """
    payload = {
        'user_id': user_id,
        'username': username,
        'exp': datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS),
        'iat': datetime.utcnow()
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """
    解码 JWT Token

    Args:
        token: JWT Token 字符串

    Returns:
        Token 载荷

    Raises:
        jwt.ExpiredSignatureError: Token 已过期
        jwt.InvalidTokenError: Token 无效
    """
    return jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])


def get_token_from_request() -> str | None:
    """
    从请求头中获取 Token

    Returns:
        Token 字符串，如果不存在则返回 None
    """
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        return auth_header[7:]
    return None


def get_current_user():
    """
    获取当前请求的用户

    Returns:
        User 对象，如果未登录则返回 None
    """
    return getattr(g, 'current_user', None)


def get_current_user_id() -> int | None:
    """
    获取当前请求的用户 ID

    Returns:
        用户 ID，如果未登录则返回 None
    """
    user = get_current_user()
    return user.id if user else None


def jwt_required(f):
    """
    JWT 认证装饰器

    用于保护需要登录才能访问的路由
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = get_token_from_request()

        if not token:
            return jsonify({
                'success': False,
                'error': '未提供认证令牌',
                'code': 'TOKEN_MISSING'
            }), 401

        try:
            payload = decode_token(token)
            user_id = payload.get('user_id')

            # 从数据库获取用户
            from backend.models import User
            user = User.query.get(user_id)

            if not user:
                return jsonify({
                    'success': False,
                    'error': '用户不存在',
                    'code': 'USER_NOT_FOUND'
                }), 401

            if not user.is_active:
                return jsonify({
                    'success': False,
                    'error': '用户已被禁用',
                    'code': 'USER_DISABLED'
                }), 401

            # 将用户信息存储到 Flask g 对象
            g.current_user = user

        except jwt.ExpiredSignatureError:
            return jsonify({
                'success': False,
                'error': '认证令牌已过期',
                'code': 'TOKEN_EXPIRED'
            }), 401
        except jwt.InvalidTokenError as e:
            logger.warning(f"无效的 Token: {e}")
            return jsonify({
                'success': False,
                'error': '无效的认证令牌',
                'code': 'TOKEN_INVALID'
            }), 401

        return f(*args, **kwargs)

    return decorated_function


def jwt_optional(f):
    """
    可选 JWT 认证装饰器

    尝试解析 Token，但不强制要求登录
    如果 Token 有效，会设置 g.current_user
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = get_token_from_request()

        if token:
            try:
                payload = decode_token(token)
                user_id = payload.get('user_id')

                from backend.models import User
                user = User.query.get(user_id)

                if user and user.is_active:
                    g.current_user = user
            except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
                pass  # Token 无效时忽略，继续处理请求

        return f(*args, **kwargs)

    return decorated_function
