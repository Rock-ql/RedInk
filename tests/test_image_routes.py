import pytest

from backend.routes import image_routes


def test_validate_path_segment_blocks_traversal():
    with pytest.raises(ValueError):
        image_routes._validate_path_segment('..', 'task_id')


def test_get_image_rejects_bad_extension(client):
    response = client.get('/api/images/task_test/secret.txt')
    assert response.status_code == 400
    data = response.get_json()
    assert data["success"] is False
