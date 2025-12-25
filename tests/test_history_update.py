import pytest


def test_update_record_accepts_null_filenames(app, sample_outline):
    from backend.services.history import get_history_service
    from backend.models import TaskImage, HistoryRecord

    with app.app_context():
        service = get_history_service()
        record_id = service.create_record(
            "测试记录",
            sample_outline,
            task_id=None,
            user_id=None
        )

        success = service.update_record(
            record_id,
            images={
                "task_id": "task_test",
                "generated": ["0.png", None, "2.png"]
            }
        )

        assert success is True

        images = (
            TaskImage.query
            .filter_by(record_id=record_id)
            .order_by(TaskImage.image_index)
            .all()
        )
        assert [img.filename for img in images] == ["0.png", "", "2.png"]

        record = HistoryRecord.query.get(record_id)
        assert record.task_id == "task_test"
