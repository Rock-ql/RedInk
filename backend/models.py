"""
SQLAlchemy 数据库模型定义
"""
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json

db = SQLAlchemy()


class HistoryRecord(db.Model):
    """历史记录表"""
    __tablename__ = 'history_records'

    id = db.Column(db.String(36), primary_key=True)  # UUID
    title = db.Column(db.String(500), nullable=False, index=True)
    status = db.Column(db.String(20), nullable=False, default='draft')  # draft/generating/completed/partial
    thumbnail = db.Column(db.String(255), nullable=True)  # 缩略图文件名
    task_id = db.Column(db.String(50), nullable=True, index=True)  # 关联的图片生成任务ID
    outline_text = db.Column(db.Text, nullable=True)  # 原始大纲文本
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关联关系
    pages = db.relationship('OutlinePage', backref='record', lazy='dynamic',
                            cascade='all, delete-orphan', order_by='OutlinePage.page_index')
    images = db.relationship('TaskImage', backref='record', lazy='dynamic',
                             cascade='all, delete-orphan')

    def to_index_dict(self):
        """转换为索引格式（用于列表展示）"""
        return {
            'id': self.id,
            'title': self.title,
            'status': self.status,
            'thumbnail': self.thumbnail,
            'task_id': self.task_id,
            'page_count': self.pages.count(),
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

    def to_full_dict(self):
        """转换为完整格式（用于详情展示）"""
        return {
            'id': self.id,
            'title': self.title,
            'status': self.status,
            'thumbnail': self.thumbnail,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'outline': {
                'raw': self.outline_text or '',
                'pages': [page.to_dict() for page in self.pages.order_by(OutlinePage.page_index)]
            },
            'images': {
                'task_id': self.task_id,
                'generated': [img.filename for img in self.images.order_by(TaskImage.image_index)]
            }
        }


class OutlinePage(db.Model):
    """大纲页面表"""
    __tablename__ = 'outline_pages'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    record_id = db.Column(db.String(36), db.ForeignKey('history_records.id', ondelete='CASCADE'),
                          nullable=False, index=True)
    page_index = db.Column(db.Integer, nullable=False)  # 页面序号（从0开始）
    page_type = db.Column(db.String(20), nullable=False, default='content')  # cover/content/summary
    content = db.Column(db.Text, nullable=False)  # 页面内容

    __table_args__ = (
        db.UniqueConstraint('record_id', 'page_index', name='uix_record_page'),
    )

    def to_dict(self):
        return {
            'index': self.page_index,
            'type': self.page_type,
            'content': self.content
        }


class TaskImage(db.Model):
    """任务图片表"""
    __tablename__ = 'task_images'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    record_id = db.Column(db.String(36), db.ForeignKey('history_records.id', ondelete='CASCADE'),
                          nullable=False, index=True)
    image_index = db.Column(db.Integer, nullable=False)  # 图片序号
    filename = db.Column(db.String(255), nullable=False)  # 文件名（如 0.png）

    __table_args__ = (
        db.UniqueConstraint('record_id', 'image_index', name='uix_record_image'),
    )


class ProviderConfig(db.Model):
    """服务商配置表"""
    __tablename__ = 'provider_configs'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    category = db.Column(db.String(20), nullable=False)  # 'text' 或 'image'
    name = db.Column(db.String(100), nullable=False)  # 服务商名称
    provider_type = db.Column(db.String(50), nullable=False)  # google_genai/openai_compatible/image_api/google_gemini
    api_key = db.Column(db.Text, nullable=True)  # API Key
    base_url = db.Column(db.String(500), nullable=True)
    model = db.Column(db.String(100), nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=False)  # 是否为当前激活的服务商
    extra_config = db.Column(db.Text, nullable=True)  # JSON格式的额外配置
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('category', 'name', name='uix_category_name'),
    )

    def to_dict(self, mask_key=True):
        """转换为字典"""
        extra = json.loads(self.extra_config) if self.extra_config else {}
        result = {
            'type': self.provider_type,
            'api_key': self._mask_api_key(self.api_key) if mask_key else self.api_key,
            'base_url': self.base_url,
            'model': self.model,
            **extra
        }
        # 移除空值
        return {k: v for k, v in result.items() if v is not None}

    def to_full_dict(self):
        """转换为完整字典（包含未脱敏的 API Key）"""
        return self.to_dict(mask_key=False)

    @staticmethod
    def _mask_api_key(key):
        """脱敏 API Key"""
        if not key:
            return ''
        if len(key) <= 8:
            return '*' * len(key)
        return key[:4] + '*' * (len(key) - 8) + key[-4:]
