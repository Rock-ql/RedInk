"""
历史记录服务 - SQLAlchemy 实现
"""
import os
import shutil
import uuid
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

from backend.models import db, HistoryRecord, OutlinePage, TaskImage

logger = logging.getLogger(__name__)


class HistoryService:
    """历史记录服务类"""

    def __init__(self):
        self.history_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "history"
        )
        os.makedirs(self.history_dir, exist_ok=True)

    def create_record(
        self,
        topic: str,
        outline: Dict,
        task_id: Optional[str] = None
    ) -> str:
        """
        创建历史记录

        Args:
            topic: 主题标题
            outline: 大纲数据 {'raw': str, 'pages': [...]}
            task_id: 任务ID（可选）

        Returns:
            新创建的记录ID
        """
        record_id = str(uuid.uuid4())
        now = datetime.utcnow()

        # 创建历史记录
        record = HistoryRecord(
            id=record_id,
            title=topic,
            status='draft',
            task_id=task_id,
            outline_text=outline.get('raw', ''),
            created_at=now,
            updated_at=now
        )
        db.session.add(record)

        # 创建大纲页面
        pages = outline.get('pages', [])
        for page in pages:
            outline_page = OutlinePage(
                record_id=record_id,
                page_index=page.get('index', 0),
                page_type=page.get('type', 'content'),
                content=page.get('content', '')
            )
            db.session.add(outline_page)

        try:
            db.session.commit()
            logger.info(f"✅ 创建历史记录: {record_id}")
        except Exception as e:
            db.session.rollback()
            logger.error(f"❌ 创建历史记录失败: {e}")
            raise

        return record_id

    def get_record(self, record_id: str) -> Optional[Dict]:
        """
        获取单条历史记录详情

        Args:
            record_id: 记录ID

        Returns:
            记录详情字典，不存在则返回 None
        """
        record = HistoryRecord.query.get(record_id)
        if not record:
            return None
        return record.to_full_dict()

    def update_record(
        self,
        record_id: str,
        outline: Optional[Dict] = None,
        images: Optional[Dict] = None,
        status: Optional[str] = None,
        thumbnail: Optional[str] = None
    ) -> bool:
        """
        更新历史记录

        Args:
            record_id: 记录ID
            outline: 大纲数据（可选）
            images: 图片数据（可选）
            status: 状态（可选）
            thumbnail: 缩略图（可选）

        Returns:
            是否更新成功
        """
        record = HistoryRecord.query.get(record_id)
        if not record:
            return False

        try:
            record.updated_at = datetime.utcnow()

            if outline is not None:
                record.outline_text = outline.get('raw', '')
                # 删除旧的页面，创建新的
                OutlinePage.query.filter_by(record_id=record_id).delete()
                for page in outline.get('pages', []):
                    outline_page = OutlinePage(
                        record_id=record_id,
                        page_index=page.get('index', 0),
                        page_type=page.get('type', 'content'),
                        content=page.get('content', '')
                    )
                    db.session.add(outline_page)

            if images is not None:
                task_id = images.get('task_id')
                if task_id:
                    record.task_id = task_id

                # 更新图片列表
                generated = images.get('generated', [])
                if generated:
                    # 删除旧的图片记录
                    TaskImage.query.filter_by(record_id=record_id).delete()
                    # 创建新的图片记录
                    for idx, filename in enumerate(generated):
                        task_image = TaskImage(
                            record_id=record_id,
                            image_index=idx,
                            filename=filename
                        )
                        db.session.add(task_image)

            if status is not None:
                record.status = status

            if thumbnail is not None:
                record.thumbnail = thumbnail

            db.session.commit()
            logger.debug(f"✅ 更新历史记录: {record_id}")
            return True

        except Exception as e:
            db.session.rollback()
            logger.error(f"❌ 更新历史记录失败: {e}")
            return False

    def delete_record(self, record_id: str) -> bool:
        """
        删除历史记录

        Args:
            record_id: 记录ID

        Returns:
            是否删除成功
        """
        record = HistoryRecord.query.get(record_id)
        if not record:
            return False

        # 删除任务图片目录
        if record.task_id:
            task_dir = os.path.join(self.history_dir, record.task_id)
            if os.path.exists(task_dir) and os.path.isdir(task_dir):
                try:
                    shutil.rmtree(task_dir)
                    logger.info(f"已删除任务目录: {task_dir}")
                except Exception as e:
                    logger.warning(f"删除任务目录失败: {task_dir}, {e}")

        try:
            # 级联删除会自动删除关联的 pages 和 images
            db.session.delete(record)
            db.session.commit()
            logger.info(f"✅ 删除历史记录: {record_id}")
            return True
        except Exception as e:
            db.session.rollback()
            logger.error(f"❌ 删除历史记录失败: {e}")
            return False

    def list_records(
        self,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None
    ) -> Dict:
        """
        获取历史记录列表（分页）

        Args:
            page: 页码（从1开始）
            page_size: 每页数量
            status: 状态过滤（可选）

        Returns:
            分页结果
        """
        query = HistoryRecord.query

        if status:
            query = query.filter_by(status=status)

        # 按创建时间倒序
        query = query.order_by(HistoryRecord.created_at.desc())

        # 获取总数
        total = query.count()

        # 分页
        records = query.offset((page - 1) * page_size).limit(page_size).all()

        return {
            "records": [r.to_index_dict() for r in records],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size
        }

    def search_records(self, keyword: str) -> List[Dict]:
        """
        搜索历史记录

        Args:
            keyword: 搜索关键词

        Returns:
            匹配的记录列表
        """
        records = HistoryRecord.query.filter(
            HistoryRecord.title.ilike(f'%{keyword}%')
        ).order_by(HistoryRecord.created_at.desc()).all()

        return [r.to_index_dict() for r in records]

    def get_statistics(self) -> Dict:
        """
        获取统计信息

        Returns:
            统计数据
        """
        total = HistoryRecord.query.count()

        # 按状态分组统计
        from sqlalchemy import func
        status_counts = db.session.query(
            HistoryRecord.status,
            func.count(HistoryRecord.id)
        ).group_by(HistoryRecord.status).all()

        status_count = {status: count for status, count in status_counts}

        return {
            "total": total,
            "by_status": status_count
        }

    def scan_and_sync_task_images(self, task_id: str) -> Dict[str, Any]:
        """
        扫描任务文件夹，同步图片列表

        Args:
            task_id: 任务ID

        Returns:
            扫描结果
        """
        task_dir = os.path.join(self.history_dir, task_id)

        if not os.path.exists(task_dir) or not os.path.isdir(task_dir):
            return {
                "success": False,
                "error": f"任务目录不存在: {task_id}"
            }

        try:
            # 扫描目录下所有图片文件（排除缩略图）
            image_files = []
            for filename in os.listdir(task_dir):
                if filename.startswith('thumb_'):
                    continue
                if filename.endswith(('.png', '.jpg', '.jpeg')):
                    image_files.append(filename)

            # 按文件名排序（数字排序）
            def get_index(filename):
                try:
                    return int(filename.split('.')[0])
                except:
                    return 999

            image_files.sort(key=get_index)

            # 查找关联的历史记录
            record = HistoryRecord.query.filter_by(task_id=task_id).first()

            if record:
                # 判断状态
                expected_count = record.pages.count()
                actual_count = len(image_files)

                if actual_count == 0:
                    status = "draft"
                elif actual_count >= expected_count:
                    status = "completed"
                else:
                    status = "partial"

                # 更新记录
                self.update_record(
                    record.id,
                    images={
                        "task_id": task_id,
                        "generated": image_files
                    },
                    status=status,
                    thumbnail=image_files[0] if image_files else None
                )

                return {
                    "success": True,
                    "record_id": record.id,
                    "task_id": task_id,
                    "images_count": len(image_files),
                    "images": image_files,
                    "status": status
                }

            # 没有关联的记录
            return {
                "success": True,
                "task_id": task_id,
                "images_count": len(image_files),
                "images": image_files,
                "no_record": True
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"扫描任务失败: {str(e)}"
            }

    def scan_all_tasks(self) -> Dict[str, Any]:
        """
        扫描所有任务文件夹，同步图片列表

        Returns:
            扫描结果统计
        """
        if not os.path.exists(self.history_dir):
            return {
                "success": False,
                "error": "历史记录目录不存在"
            }

        try:
            synced_count = 0
            failed_count = 0
            orphan_tasks = []
            results = []

            # 遍历 history 目录
            for item in os.listdir(self.history_dir):
                item_path = os.path.join(self.history_dir, item)

                # 只处理目录（任务文件夹）
                if not os.path.isdir(item_path):
                    continue

                task_id = item
                result = self.scan_and_sync_task_images(task_id)
                results.append(result)

                if result.get("success"):
                    if result.get("no_record"):
                        orphan_tasks.append(task_id)
                    else:
                        synced_count += 1
                else:
                    failed_count += 1

            return {
                "success": True,
                "total_tasks": len(results),
                "synced": synced_count,
                "failed": failed_count,
                "orphan_tasks": orphan_tasks,
                "results": results
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"扫描所有任务失败: {str(e)}"
            }


_service_instance = None


def get_history_service() -> HistoryService:
    """获取历史记录服务单例"""
    global _service_instance
    if _service_instance is None:
        _service_instance = HistoryService()
    return _service_instance
