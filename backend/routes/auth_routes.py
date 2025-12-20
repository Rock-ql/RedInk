"""
认证相关 API 路由

包含功能：
- 用户注册
- 用户登录
- 用户登出
- 获取当前用户信息
- 刷新 Token
"""
import logging
from datetime import datetime

from flask import Blueprint, request, jsonify

from backend.models import db, User
from backend.utils.auth import (
    hash_password,
    verify_password,
    generate_token,
    jwt_required,
    get_current_user
)

logger = logging.getLogger(__name__)


def create_auth_blueprint():
    """创建认证路由蓝图"""
    auth_bp = Blueprint('auth', __name__)

    @auth_bp.route('/auth/register', methods=['POST'])
    def register():
        """
        用户注册

        请求体：
        - username: 用户名（必填，3-50字符）
        - password: 密码（必填，6位以上）

        返回：
        - success: 是否成功
        - user: 用户信息
        - token: JWT Token
        """
        try:
            data = request.get_json()

            username = data.get('username', '').strip()
            password = data.get('password', '')

            # 验证用户名
            if not username:
                return jsonify({
                    'success': False,
                    'error': '用户名不能为空'
                }), 400

            if len(username) < 3 or len(username) > 50:
                return jsonify({
                    'success': False,
                    'error': '用户名长度需在 3-50 个字符之间'
                }), 400

            # 验证密码
            if not password:
                return jsonify({
                    'success': False,
                    'error': '密码不能为空'
                }), 400

            if len(password) < 6:
                return jsonify({
                    'success': False,
                    'error': '密码长度不能少于 6 位'
                }), 400

            # 检查用户名是否已存在
            existing_user = User.query.filter_by(username=username).first()
            if existing_user:
                return jsonify({
                    'success': False,
                    'error': '用户名已被使用'
                }), 400

            # 创建用户
            user = User(
                username=username,
                password_hash=hash_password(password),
                is_active=True,
                created_at=datetime.utcnow()
            )
            db.session.add(user)
            db.session.commit()

            # 生成 Token
            token = generate_token(user.id, user.username)

            logger.info(f"✅ 用户注册成功: {username}")

            return jsonify({
                'success': True,
                'user': user.to_dict(),
                'token': token
            }), 201

        except Exception as e:
            db.session.rollback()
            logger.error(f"❌ 用户注册失败: {e}")
            return jsonify({
                'success': False,
                'error': f'注册失败: {str(e)}'
            }), 500

    @auth_bp.route('/auth/login', methods=['POST'])
    def login():
        """
        用户登录

        请求体：
        - username: 用户名
        - password: 密码

        返回：
        - success: 是否成功
        - user: 用户信息
        - token: JWT Token
        """
        try:
            data = request.get_json()

            username = data.get('username', '').strip()
            password = data.get('password', '')

            if not username or not password:
                return jsonify({
                    'success': False,
                    'error': '用户名和密码不能为空'
                }), 400

            # 查找用户
            user = User.query.filter_by(username=username).first()

            if not user:
                return jsonify({
                    'success': False,
                    'error': '用户名或密码错误'
                }), 401

            # 验证密码
            if not verify_password(password, user.password_hash):
                return jsonify({
                    'success': False,
                    'error': '用户名或密码错误'
                }), 401

            # 检查账户状态
            if not user.is_active:
                return jsonify({
                    'success': False,
                    'error': '账户已被禁用'
                }), 403

            # 更新最后登录时间
            user.last_login_at = datetime.utcnow()
            db.session.commit()

            # 生成 Token
            token = generate_token(user.id, user.username)

            logger.info(f"✅ 用户登录成功: {username}")

            return jsonify({
                'success': True,
                'user': user.to_dict(),
                'token': token
            }), 200

        except Exception as e:
            logger.error(f"❌ 用户登录失败: {e}")
            return jsonify({
                'success': False,
                'error': f'登录失败: {str(e)}'
            }), 500

    @auth_bp.route('/auth/logout', methods=['POST'])
    @jwt_required
    def logout():
        """
        用户登出

        注意：JWT 是无状态的，登出主要由前端清除 Token 实现
        这个接口主要用于记录日志或未来实现 Token 黑名单

        返回：
        - success: 是否成功
        """
        user = get_current_user()
        logger.info(f"✅ 用户登出: {user.username}")

        return jsonify({
            'success': True,
            'message': '登出成功'
        }), 200

    @auth_bp.route('/auth/me', methods=['GET'])
    @jwt_required
    def get_me():
        """
        获取当前用户信息

        返回：
        - success: 是否成功
        - user: 用户信息
        """
        user = get_current_user()

        return jsonify({
            'success': True,
            'user': user.to_dict()
        }), 200

    @auth_bp.route('/auth/refresh', methods=['POST'])
    @jwt_required
    def refresh_token():
        """
        刷新 Token

        返回：
        - success: 是否成功
        - token: 新的 JWT Token
        """
        user = get_current_user()
        token = generate_token(user.id, user.username)

        return jsonify({
            'success': True,
            'token': token
        }), 200

    return auth_bp
