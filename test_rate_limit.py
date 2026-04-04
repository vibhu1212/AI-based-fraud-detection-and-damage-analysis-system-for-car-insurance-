import sys
import os
from unittest.mock import patch, MagicMock

# Add backend directory to sys.path to allow importing app modules
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'backend'))
sys.path.insert(0, backend_dir)

# Mock required modules
mock_redis = MagicMock()
mock_redis_client = MagicMock()
mock_redis.from_url.return_value = mock_redis_client

sys.modules['redis'] = mock_redis
sys.modules['jose'] = MagicMock()
sys.modules['passlib.context'] = MagicMock()
sys.modules['pydantic_settings'] = MagicMock()
sys.modules['pydantic'] = MagicMock()

from app.services.auth import auth_service

def test_check_verify_rate_limit():
    phone = "1234567890"
    key = f"otp_verify_rate:{phone}"

    # Reset mock
    mock_redis_client.reset_mock()

    # Test 1: First request (count is None)
    mock_redis_client.get.return_value = None
    result = auth_service.check_verify_rate_limit(phone)
    assert result is True
    mock_redis_client.setex.assert_called_with(key, auth_service.OTP_VERIFY_RATE_LIMIT_WINDOW, 1)

    # Reset mock
    mock_redis_client.reset_mock()

    # Test 2: Subsequent request within limit
    mock_redis_client.get.return_value = "2"
    result = auth_service.check_verify_rate_limit(phone)
    assert result is True
    mock_redis_client.incr.assert_called_with(key)

    # Reset mock
    mock_redis_client.reset_mock()

    # Test 3: Request exceeding limit
    mock_redis_client.get.return_value = str(auth_service.OTP_VERIFY_RATE_LIMIT_MAX)
    result = auth_service.check_verify_rate_limit(phone)
    assert result is False

if __name__ == "__main__":
    test_check_verify_rate_limit()
    print("Tests passed!")