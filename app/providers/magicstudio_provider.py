import time
import logging
import random
import asyncio
import uuid
import base64
from typing import Dict, Any, Optional

import httpx
from fastapi import HTTPException, Response

from app.core.config import settings

logger = logging.getLogger(__name__)

class MagicStudioProvider:
    BASE_URL = "https://ai-api.magicstudio.com/api/ai-art-generator"

    def __init__(self):
        # [修正] 移除不被支持的 'backoff_factor' 参数，以符合 httpx API
        retries = settings.UPSTREAM_MAX_RETRIES
        transport = httpx.AsyncHTTPTransport(retries=retries)
        self.client = httpx.AsyncClient(
            timeout=settings.API_REQUEST_TIMEOUT,
            transport=transport
        )

    def _prepare_headers(self) -> Dict[str, str]:
        return {
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Origin": "https://magicstudio.com",
            "Referer": "https://magicstudio.com/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36",
        }

    async def _send_single_request(self, prompt: str) -> str:
        """
        发送单个图像生成请求并返回Base64编码的图像数据。
        """
        headers = self._prepare_headers()
        data = {
            "prompt": prompt,
            "output_format": "bytes",
            "user_profile_id": "null",
            "anonymous_user_id": str(uuid.uuid4()),
            "request_timestamp": str(time.time()),
            "user_is_subscribed": "false",
            "client_id": settings.UPSTREAM_CLIENT_ID,
        }

        try:
            response = await self.client.post(self.BASE_URL, headers=headers, data=data)
            response.raise_for_status()

            content_type = response.headers.get("content-type")
            if "image" not in content_type:
                error_text = response.text
                logger.error(f"上游未返回图像，而是返回: {content_type}, 内容: {error_text[:200]}")
                raise ValueError(f"Upstream API did not return an image. Response: {error_text}")

            image_bytes = await response.aread()
            return base64.b64encode(image_bytes).decode('utf-8')

        except httpx.HTTPStatusError as e:
            logger.error(f"请求上游失败，状态码: {e.response.status_code}, 响应: {e.response.text}")
            raise HTTPException(status_code=502, detail=f"Upstream service error: {e.response.status_code}")
        except Exception as e:
            logger.error(f"发送单个请求时发生未知错误: {e}", exc_info=True)
            raise

    async def generate_image(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        prompt = request_data.get("prompt")
        if not prompt:
            raise HTTPException(status_code=400, detail="参数 'prompt' 不能为空。")

        num_images = request_data.get("n", 1)
        response_format = request_data.get("response_format", "b64_json")

        if response_format != "b64_json":
            raise HTTPException(status_code=400, detail="仅支持 'b64_json' 响应格式。")

        tasks = [self._send_single_request(prompt) for _ in range(num_images)]
        logger.info(f"准备向上游并发发送 {num_images} 个图像生成请求...")

        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            successful_results = []
            for res in results:
                if isinstance(res, Exception):
                    logger.error(f"一个并发任务失败: {res}")
                else:
                    successful_results.append(res)
            
            if not successful_results:
                raise HTTPException(status_code=502, detail="所有上游图像生成任务均失败。")

            response_data = {
                "created": int(time.time()),
                "data": [{"b64_json": b64_str} for b64_str in successful_results]
            }
            return response_data

        except Exception as e:
            logger.error(f"处理并发请求时发生严重错误: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"处理并发图像生成时出错: {str(e)}")

    async def get_models(self) -> Dict[str, Any]:
        return {
            "object": "list",
            "data": [
                {"id": name, "object": "model", "created": int(time.time()), "owned_by": "lzA6"}
                for name in settings.KNOWN_MODELS
            ]
        }
