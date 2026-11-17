import os
from django.conf import settings
import pytest

@pytest.mark.unit
def test_vps_ip_en_allowed_hosts_y_cors():
    assert "72.61.0.102" in settings.ALLOWED_HOSTS
    assert any("72.61.0.102" in origin for origin in settings.CORS_ALLOWED_ORIGINS)
