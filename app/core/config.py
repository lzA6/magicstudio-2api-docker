from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional, List

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding='utf-8',
        extra="ignore"
    )

    APP_NAME: str = "magicstudio-2api"
    APP_VERSION: str = "1.0.0"
    DESCRIPTION: str = "一个将 Magic Studio AI Art Generator 转换为兼容 OpenAI 格式 API 的高性能并发代理。"

    API_MASTER_KEY: Optional[str] = None
    NGINX_PORT: int = 8088

    # 上游请求配置
    API_REQUEST_TIMEOUT: int = 180
    UPSTREAM_MAX_RETRIES: int = 3
    UPSTREAM_RETRY_DELAY: int = 2 # 秒

    # 上游API固定参数
    UPSTREAM_CLIENT_ID: str = "pSgX7WgjukXCBoYwDM8G8GLnRRkvAoJlqa5eAVvj95o"

    # 模型配置
    DEFAULT_MODEL: str = "magic-art-generator"
    KNOWN_MODELS: List[str] = ["magic-art-generator"]

settings = Settings()
