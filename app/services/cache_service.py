# app/services/cache_service.py
import hashlib
import json
import structlog
import redis as redis_lib
from app.config import settings

logger = structlog.get_logger()

class LLMCache:
    def __init__(self):
        try:
            self.redis = redis_lib.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=2,
            )
            self.redis.ping()
            self.available = True
            logger.info("cache_connected", url=settings.REDIS_URL)
        except Exception as e:
            self.available = False
            logger.warning("cache_unavailable", error=str(e))

    def _cache_key(self, transcription: str, model: str, system_prompt: str) -> str:
        raw = json.dumps({
            "transcription": transcription,
            "model":         model,
            "system_prompt": system_prompt,
        }, sort_keys=True)
        return f"llm:{hashlib.sha256(raw.encode()).hexdigest()}"

    def get(self, transcription: str, model: str, system_prompt: str) -> dict | None:
        if not self.available:
            return None
        try:
            key = self._cache_key(transcription, model, system_prompt)
            cached = self.redis.get(key)
            if cached:
                logger.info("cache_hit", key=key[:16])
                result = json.loads(cached)
                result["cache_hit"] = True
                return result
        except Exception as e:
            logger.warning("cache_get_failed", error=str(e))
        return None

    def set(self, transcription: str, model: str, system_prompt: str,
            result: dict, ttl: int = 86400) -> None:
        if not self.available:
            return
        try:
            key = self._cache_key(transcription, model, system_prompt)
            data = {k: v for k, v in result.items() if k != "cache_hit"}
            self.redis.setex(key, ttl, json.dumps(data))
            logger.info("cache_set", key=key[:16], ttl=ttl)
        except Exception as e:
            logger.warning("cache_set_failed", error=str(e))

llm_cache = LLMCache()