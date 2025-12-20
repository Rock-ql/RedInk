"""
数据迁移模块：从文件存储迁移到 SQLite 数据库
"""
import os
import json
import shutil
import logging
import secrets
from pathlib import Path
from datetime import datetime
import yaml

from backend.models import db, HistoryRecord, OutlinePage, TaskImage, ProviderConfig, User
from backend.utils.auth import hash_password

logger = logging.getLogger(__name__)


def ensure_users_table():
    """
    确保 users 表存在

    使用原生 SQL 检查和创建，避免 ORM 模型与数据库不一致的问题
    """
    from sqlalchemy import text, inspect

    inspector = inspect(db.engine)
    tables = inspector.get_table_names()

    if 'users' not in tables:
        logger.info("📋 创建 users 表...")
        db.session.execute(text("""
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username VARCHAR(50) NOT NULL UNIQUE,
                password_hash VARCHAR(255) NOT NULL,
                is_active BOOLEAN DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_login_at DATETIME
            )
        """))
        db.session.commit()
        logger.info("✅ users 表创建完成")


def ensure_user_id_columns():
    """
    确保 history_records 和 provider_configs 表有 user_id 列

    使用原生 SQL 进行 schema 迁移，避免 ORM 查询失败
    """
    from sqlalchemy import text, inspect

    inspector = inspect(db.engine)

    # 检查 history_records 表
    if 'history_records' in inspector.get_table_names():
        columns = [col['name'] for col in inspector.get_columns('history_records')]
        if 'user_id' not in columns:
            logger.info("📋 为 history_records 表添加 user_id 列...")
            db.session.execute(text(
                "ALTER TABLE history_records ADD COLUMN user_id INTEGER REFERENCES users(id)"
            ))
            db.session.commit()
            logger.info("✅ history_records.user_id 列添加完成")

    # 检查 provider_configs 表
    if 'provider_configs' in inspector.get_table_names():
        columns = [col['name'] for col in inspector.get_columns('provider_configs')]
        if 'user_id' not in columns:
            logger.info("📋 为 provider_configs 表添加 user_id 列...")
            db.session.execute(text(
                "ALTER TABLE provider_configs ADD COLUMN user_id INTEGER REFERENCES users(id)"
            ))
            db.session.commit()
            logger.info("✅ provider_configs.user_id 列添加完成")


def get_project_root() -> Path:
    """获取项目根目录"""
    return Path(__file__).parent.parent


def backup_old_files():
    """备份旧的数据文件"""
    project_root = get_project_root()
    backup_dir = project_root / 'backup' / datetime.now().strftime('%Y%m%d_%H%M%S')

    files_to_backup = [
        project_root / 'history' / 'index.json',
        project_root / 'text_providers.yaml',
        project_root / 'image_providers.yaml',
    ]

    # 检查是否有需要备份的文件
    has_files = False
    for f in files_to_backup:
        if f.exists():
            has_files = True
            break

    if not has_files:
        logger.info("📁 没有找到需要备份的旧数据文件")
        return None

    # 创建备份目录
    backup_dir.mkdir(parents=True, exist_ok=True)

    # 备份文件
    for f in files_to_backup:
        if f.exists():
            dest = backup_dir / f.name
            shutil.copy2(f, dest)
            logger.info(f"📦 已备份: {f.name} -> {dest}")

    # 备份历史记录 JSON 文件
    history_dir = project_root / 'history'
    if history_dir.exists():
        for json_file in history_dir.glob('*.json'):
            if json_file.name != 'index.json':
                dest = backup_dir / json_file.name
                shutil.copy2(json_file, dest)
                logger.info(f"📦 已备份: {json_file.name}")

    logger.info(f"✅ 备份完成: {backup_dir}")
    return backup_dir


def migrate_history_records():
    """迁移历史记录"""
    project_root = get_project_root()
    history_dir = project_root / 'history'
    index_file = history_dir / 'index.json'

    if not index_file.exists():
        logger.info("📁 没有找到 index.json，跳过历史记录迁移")
        return 0

    # 检查数据库是否已有数据
    existing_count = HistoryRecord.query.count()
    if existing_count > 0:
        logger.info(f"📊 数据库已有 {existing_count} 条历史记录，跳过迁移")
        return 0

    try:
        with open(index_file, 'r', encoding='utf-8') as f:
            index_data = json.load(f)
    except Exception as e:
        logger.error(f"❌ 读取 index.json 失败: {e}")
        return 0

    records = index_data.get('records', [])
    migrated_count = 0

    for record_meta in records:
        record_id = record_meta.get('id')
        if not record_id:
            continue

        # 读取完整记录文件
        record_file = history_dir / f"{record_id}.json"
        if not record_file.exists():
            logger.warning(f"⚠️ 记录文件不存在: {record_file}")
            continue

        try:
            with open(record_file, 'r', encoding='utf-8') as f:
                record_data = json.load(f)
        except Exception as e:
            logger.error(f"❌ 读取记录文件失败 {record_file}: {e}")
            continue

        try:
            # 创建历史记录
            history_record = HistoryRecord(
                id=record_id,
                title=record_data.get('title', ''),
                status=record_data.get('status', 'draft'),
                thumbnail=record_data.get('thumbnail'),
                task_id=record_data.get('images', {}).get('task_id'),
                outline_text=record_data.get('outline', {}).get('raw', ''),
                created_at=datetime.fromisoformat(record_data.get('created_at', datetime.utcnow().isoformat())),
                updated_at=datetime.fromisoformat(record_data.get('updated_at', datetime.utcnow().isoformat()))
            )
            db.session.add(history_record)

            # 创建大纲页面
            pages = record_data.get('outline', {}).get('pages', [])
            for page in pages:
                outline_page = OutlinePage(
                    record_id=record_id,
                    page_index=page.get('index', 0),
                    page_type=page.get('type', 'content'),
                    content=page.get('content', '')
                )
                db.session.add(outline_page)

            # 创建任务图片记录
            images = record_data.get('images', {}).get('generated', [])
            for idx, filename in enumerate(images):
                task_image = TaskImage(
                    record_id=record_id,
                    image_index=idx,
                    filename=filename
                )
                db.session.add(task_image)

            db.session.commit()
            migrated_count += 1
            logger.debug(f"✅ 迁移记录: {record_id} - {record_data.get('title', '')[:30]}")

        except Exception as e:
            db.session.rollback()
            logger.error(f"❌ 迁移记录失败 {record_id}: {e}")
            continue

    logger.info(f"✅ 历史记录迁移完成: 共迁移 {migrated_count} 条记录")
    return migrated_count


def migrate_provider_configs():
    """迁移服务商配置"""
    project_root = get_project_root()

    # 检查数据库是否已有配置
    existing_count = ProviderConfig.query.count()
    if existing_count > 0:
        logger.info(f"📊 数据库已有 {existing_count} 条配置，跳过迁移")
        return 0

    migrated_count = 0

    # 迁移文本服务商配置
    text_config_file = project_root / 'text_providers.yaml'
    if text_config_file.exists():
        try:
            with open(text_config_file, 'r', encoding='utf-8') as f:
                text_config = yaml.safe_load(f) or {}

            active_provider = text_config.get('active_provider', '')
            providers = text_config.get('providers', {})

            for name, config in providers.items():
                # 提取核心字段，其余放入 extra_config
                extra = {}
                for key in ['temperature', 'max_output_tokens']:
                    if key in config:
                        extra[key] = config[key]

                provider = ProviderConfig(
                    category='text',
                    name=name,
                    provider_type=config.get('type', 'openai_compatible'),
                    api_key=config.get('api_key', ''),
                    base_url=config.get('base_url'),
                    model=config.get('model'),
                    is_active=(name == active_provider),
                    extra_config=json.dumps(extra) if extra else None
                )
                db.session.add(provider)
                migrated_count += 1

            db.session.commit()
            logger.info(f"✅ 文本服务商配置迁移完成: {len(providers)} 个")

        except Exception as e:
            db.session.rollback()
            logger.error(f"❌ 迁移文本配置失败: {e}")

    # 迁移图片服务商配置
    image_config_file = project_root / 'image_providers.yaml'
    if image_config_file.exists():
        try:
            with open(image_config_file, 'r', encoding='utf-8') as f:
                image_config = yaml.safe_load(f) or {}

            active_provider = image_config.get('active_provider', '')
            providers = image_config.get('providers', {})

            for name, config in providers.items():
                # 提取核心字段，其余放入 extra_config
                extra = {}
                for key in ['high_concurrency', 'short_prompt', 'default_aspect_ratio',
                            'temperature', 'image_size', 'endpoint_type']:
                    if key in config:
                        extra[key] = config[key]

                provider = ProviderConfig(
                    category='image',
                    name=name,
                    provider_type=config.get('type', 'google_genai'),
                    api_key=config.get('api_key', ''),
                    base_url=config.get('base_url'),
                    model=config.get('model'),
                    is_active=(name == active_provider),
                    extra_config=json.dumps(extra) if extra else None
                )
                db.session.add(provider)
                migrated_count += 1

            db.session.commit()
            logger.info(f"✅ 图片服务商配置迁移完成: {len(providers)} 个")

        except Exception as e:
            db.session.rollback()
            logger.error(f"❌ 迁移图片配置失败: {e}")

    return migrated_count


def get_or_create_default_user() -> int:
    """
    获取或创建默认用户

    Returns:
        默认用户的 ID
    """
    default_username = 'default'

    # 检查是否已存在
    user = User.query.filter_by(username=default_username).first()
    if user:
        return user.id

    # 创建默认用户（使用随机密码，仅用于数据关联）
    random_password = secrets.token_urlsafe(32)
    user = User(
        username=default_username,
        password_hash=hash_password(random_password),
        is_active=True,
        created_at=datetime.utcnow()
    )
    db.session.add(user)
    db.session.commit()

    logger.info(f"✅ 已创建默认用户: {default_username}")
    return user.id


def migrate_orphan_records():
    """
    将没有 user_id 的记录关联到默认用户

    Returns:
        迁移的记录数
    """
    # 检查是否有孤儿记录
    orphan_history = HistoryRecord.query.filter_by(user_id=None).count()
    orphan_config = ProviderConfig.query.filter_by(user_id=None).count()

    if orphan_history == 0 and orphan_config == 0:
        logger.info("📊 没有需要关联用户的孤儿记录")
        return 0

    # 获取或创建默认用户
    default_user_id = get_or_create_default_user()

    # 更新 HistoryRecord
    if orphan_history > 0:
        HistoryRecord.query.filter_by(user_id=None).update({'user_id': default_user_id})
        logger.info(f"✅ 已将 {orphan_history} 条历史记录关联到默认用户")

    # 更新 ProviderConfig
    if orphan_config > 0:
        ProviderConfig.query.filter_by(user_id=None).update({'user_id': default_user_id})
        logger.info(f"✅ 已将 {orphan_config} 条配置关联到默认用户")

    db.session.commit()

    return orphan_history + orphan_config


def check_and_migrate():
    """
    检查并执行迁移

    Returns:
        bool: 是否执行了迁移
    """
    # 首先确保数据库 schema 是最新的
    # 这必须在任何 ORM 查询之前执行
    ensure_users_table()
    ensure_user_id_columns()

    project_root = get_project_root()

    # 检查是否存在旧数据文件
    has_old_data = (
        (project_root / 'history' / 'index.json').exists() or
        (project_root / 'text_providers.yaml').exists() or
        (project_root / 'image_providers.yaml').exists()
    )

    if not has_old_data:
        # 即使没有旧数据，也要检查是否有孤儿记录需要关联
        orphan_migrated = migrate_orphan_records()
        if orphan_migrated > 0:
            logger.info(f"✅ 已将 {orphan_migrated} 条记录关联到默认用户")
        else:
            logger.info("📁 没有发现旧数据文件，无需迁移")
        return orphan_migrated > 0

    # 检查数据库是否为空
    history_count = HistoryRecord.query.count()
    config_count = ProviderConfig.query.count()

    if history_count > 0 or config_count > 0:
        logger.info(f"📊 数据库已有数据 (历史记录: {history_count}, 配置: {config_count})，跳过文件迁移")
        # 即便跳过文件迁移，也要检查是否有孤儿记录
        orphan_migrated = migrate_orphan_records()
        return orphan_migrated > 0

    logger.info("🚀 开始执行数据迁移...")

    # 备份旧文件
    backup_old_files()

    # 迁移数据
    history_migrated = migrate_history_records()
    config_migrated = migrate_provider_configs()

    logger.info(f"✅ 迁移完成: 历史记录 {history_migrated} 条, 配置 {config_migrated} 条")

    # 将孤儿记录关联到默认用户
    orphan_migrated = migrate_orphan_records()
    if orphan_migrated > 0:
        logger.info(f"✅ 已将 {orphan_migrated} 条记录关联到默认用户")

    return True


def run_migration():
    """手动运行迁移（用于命令行调用）"""
    from backend.app import create_app

    app = create_app()
    with app.app_context():
        check_and_migrate()


if __name__ == '__main__':
    run_migration()
