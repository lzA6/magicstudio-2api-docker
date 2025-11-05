import logging
import time
import uuid
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Request, HTTPException, Depends, Header
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.providers.magicstudio_provider import MagicStudioProvider

# --- 日志配置 ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- 全局 Provider 实例 ---
provider = MagicStudioProvider()

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"应用启动中... {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info("服务已进入 'Concurrent Proxy' 模式。")
    logger.info(f"API 服务将在 http://localhost:{settings.NGINX_PORT} 上可用")
    logger.info(f"Web UI 测试界面已启用，请访问 http://localhost:{settings.NGINX_PORT}/")
    yield
    logger.info("应用关闭。")

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=settings.DESCRIPTION,
    lifespan=lifespan
)

# --- 挂载静态文件目录 ---
app.mount("/static", StaticFiles(directory="static"), name="static")

# --- 安全依赖 ---
async def verify_api_key(authorization: Optional[str] = Header(None)):
    if settings.API_MASTER_KEY and settings.API_MASTER_KEY != "1":
        if not authorization or "bearer" not in authorization.lower():
            raise HTTPException(status_code=401, detail="需要 Bearer Token 认证。")
        token = authorization.split(" ")[-1]
        if token != settings.API_MASTER_KEY:
            raise HTTPException(status_code=403, detail="无效的 API Key。")

# --- API 路由 ---
@app.post("/v1/images/generations", dependencies=[Depends(verify_api_key)])
async def image_generations(request: Request):
    try:
        request_data = await request.json()
        image_result_dict = await provider.generate_image(request_data)
        return JSONResponse(content=image_result_dict)
    except Exception as e:
        logger.error(f"处理图像生成请求时发生顶层错误: {e}", exc_info=True)
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"内部服务器错误: {str(e)}")

@app.post("/v1/chat/completions", dependencies=[Depends(verify_api_key)])
async def chat_completions(request: Request):
    try:
        request_data = await request.json()
        
        messages = request_data.get("messages", [])
        if not messages:
            raise HTTPException(status_code=400, detail="请求体中缺少 'messages' 字段。")
        
        last_user_message = next((m['content'] for m in reversed(messages) if m.get('role') == 'user'), None)
        if not last_user_message:
            raise HTTPException(status_code=400, detail="在 'messages' 中未找到用户消息。")

        model_name = request_data.get("model", settings.DEFAULT_MODEL)

        image_request_data = {
            "prompt": last_user_message,
            "model": model_name,
            "n": 1,
            "response_format": "b64_json"
        }
        
        logger.info(f"通过聊天接口适配图像生成，使用 prompt: '{last_user_message[:50]}...'")
        image_result_dict = await provider.generate_image(image_request_data)

        if not image_result_dict.get("data") or not image_result_dict["data"][0].get("b64_json"):
            raise HTTPException(status_code=502, detail="从上游服务生成图像失败。")
            
        b64_json = image_result_dict["data"][0]["b64_json"]
        
        response_content = f"![](data:image/png;base64,{b64_json})"
        
        chat_response = {
            "id": f"chatcmpl-{uuid.uuid4()}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": model_name,
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": response_content,
                },
                "finish_reason": "stop",
            }],
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        }
        
        return JSONResponse(content=chat_response)

    except Exception as e:
        logger.error(f"处理聊天生成请求时发生顶层错误: {e}", exc_info=True)
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"内部服务器错误: {str(e)}")

@app.get("/v1/models", dependencies=[Depends(verify_api_key)])
async def list_models():
    return await provider.get_models()

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def serve_ui():
    try:
        with open("static/index.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="UI 文件 (static/index.html) 未找到。")
