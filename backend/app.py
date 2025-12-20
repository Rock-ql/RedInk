import logging
import sys
from pathlib import Path
from flask import Flask, send_from_directory
from flask_cors import CORS
from backend.config import Config
from backend.routes import register_routes
from backend.database import init_db


def setup_logging():
    """配置日志系统"""
    # 创建根日志器
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    # 清除已有的处理器
    root_logger.handlers.clear()

    # 控制台处理器 - 详细格式
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_format = logging.Formatter(
        '\n%(asctime)s | %(levelname)-8s | %(name)s\n'
        '  └─ %(message)s',
        datefmt='%H:%M:%S'
    )
    console_handler.setFormatter(console_format)
    root_logger.addHandler(console_handler)

    # 设置各模块的日志级别
    logging.getLogger('backend').setLevel(logging.DEBUG)
    logging.getLogger('werkzeug').setLevel(logging.INFO)
    logging.getLogger('urllib3').setLevel(logging.WARNING)

    return root_logger


def create_app():
    # 设置日志
    logger = setup_logging()
    logger.info("🚀 正在启动 红墨 AI图文生成器...")

    # 检查是否存在前端构建产物（Docker 环境）
    frontend_dist = Path(__file__).parent.parent / 'frontend' / 'dist'
    if frontend_dist.exists():
        logger.info("📦 检测到前端构建产物，启用静态文件托管模式")
        app = Flask(
            __name__,
            static_folder=str(frontend_dist),
            static_url_path=''
        )
    else:
        logger.info("🔧 开发模式，前端请单独启动")
        app = Flask(__name__)

    app.config.from_object(Config)

    # 初始化数据库
    init_db(app)

    # 执行数据迁移（如果需要）
    with app.app_context():
        from backend.migrations import check_and_migrate
        check_and_migrate()

    CORS(app, resources={
        r"/api/*": {
            "origins": Config.CORS_ORIGINS,
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"],
            "expose_headers": ["Authorization"],
            "supports_credentials": True
        }
    })

    # 注册所有 API 路由
    register_routes(app)

    # 启动时验证配置（需要在应用上下文中执行）
    with app.app_context():
        _validate_config_on_startup(logger)

    # 根据是否有前端构建产物决定根路由行为
    if frontend_dist.exists():
        @app.route('/')
        def serve_index():
            return send_from_directory(app.static_folder, 'index.html')

        # 处理 Vue Router 的 HTML5 History 模式
        @app.errorhandler(404)
        def fallback(e):
            return send_from_directory(app.static_folder, 'index.html')
    else:
        @app.route('/')
        def index():
            return {
                "message": "红墨 AI图文生成器 API",
                "version": "0.1.0",
                "endpoints": {
                    "health": "/api/health",
                    "outline": "POST /api/outline",
                    "generate": "POST /api/generate",
                    "images": "GET /api/images/<filename>"
                }
            }

    return app


def _validate_config_on_startup(logger):
    """启动时验证配置（从数据库读取）"""
    from backend.models import ProviderConfig

    logger.info("📋 检查服务商配置...")

    # 检查文本服务商配置
    text_providers = ProviderConfig.query.filter_by(category='text').all()
    active_text = ProviderConfig.query.filter_by(category='text', is_active=True).first()

    if text_providers:
        provider_names = [p.name for p in text_providers]
        active_name = active_text.name if active_text else '未设置'
        logger.info(f"✅ 文本生成配置: 激活={active_name}, 可用服务商={provider_names}")

        if active_text:
            if not active_text.api_key:
                logger.warning(f"⚠️  文本服务商 [{active_name}] 未配置 API Key")
            else:
                logger.info(f"✅ 文本服务商 [{active_name}] API Key 已配置")
    else:
        logger.warning("⚠️  未配置任何文本服务商，请在设置页面添加")

    # 检查图片服务商配置
    image_providers = ProviderConfig.query.filter_by(category='image').all()
    active_image = ProviderConfig.query.filter_by(category='image', is_active=True).first()

    if image_providers:
        provider_names = [p.name for p in image_providers]
        active_name = active_image.name if active_image else '未设置'
        logger.info(f"✅ 图片生成配置: 激活={active_name}, 可用服务商={provider_names}")

        if active_image:
            if not active_image.api_key:
                logger.warning(f"⚠️  图片服务商 [{active_name}] 未配置 API Key")
            else:
                logger.info(f"✅ 图片服务商 [{active_name}] API Key 已配置")
    else:
        logger.warning("⚠️  未配置任何图片服务商，请在设置页面添加")

    logger.info("✅ 配置检查完成")


if __name__ == '__main__':
    app = create_app()
    app.run(
        host=Config.HOST,
        port=Config.PORT,
        debug=Config.DEBUG
    )
