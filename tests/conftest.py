import pytest

@pytest.fixture
def dummy_context():
    return {
        "sender": "0x1234567890123456789012345678901234567890",
        "datetime": "2026-09-24T10:00:00Z"
    }
