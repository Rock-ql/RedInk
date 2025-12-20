"""
数据库初始化模块
"""
import logging
from pathlib import Path
from backend.models import db

logger = logging.getLogger(__name__)


def init_db(app):
    """
    初始化数据库

    Args:
        app: Flask 应用实例
    """
    # 数据库文件存放在项目根目录的 data 文件夹
    db_path = Path(__file__).parent.parent / 'data' / 'redink.db'
    db_path.parent.mkdir(exist_ok=True)

    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    # 启用外键约束（SQLite 默认不启用）
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'connect_args': {'check_same_thread': False},
    }

    db.init_app(app)

    with app.app_context():
        # 启用 SQLite 外键约束
        from sqlalchemy import event
        from sqlalchemy.engine import Engine

        @event.listens_for(Engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        # 创建所有表
        db.create_all()
        logger.info(f"✅ 数据库初始化完成: {db_path}")

    return db
