import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pygoat.settings')
import pytest

@pytest.fixture(scope='session')
def django_db_setup(): pass
