import pytest
from reviews import celery_app, add_numbers, chek_redis

@pytest.fixture(scope="module")
def celery_worker():
    celery_app.conf.update(
        task_always_eager=True,
        task_eager_propagates=True,
    )
    return celery_app

def test_add_numbers(celery_worker):
    result = add_numbers.delay(1, 2)
    assert result.get() == 3

def test_add_numbers_task_intentional_failure(celery_worker):
    result = add_numbers.delay("a", 5)
    assert result.failed() == False
    
def test_chek_redis():
    assert chek_redis() == True



