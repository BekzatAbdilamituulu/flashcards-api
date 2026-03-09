from slowapi import Limiter
from slowapi.util import get_remote_address
from app.config import settings
import uuid


def key_func(request):
    if settings.app_env == "test":
        return str(uuid.uuid4())
    return get_remote_address(request)


limiter = Limiter(key_func=key_func)