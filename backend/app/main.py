"""FastAPI 应用入口。

可以把这个文件理解成后端服务的“总开关”：启动 Uvicorn 时，Uvicorn 会导入
这里的 ``app`` 对象，然后 FastAPI 根据注册的路由处理 HTTP 请求。

当前这里只保留最小健康检查接口，后续业务路由可以按功能模块拆分后在这里注册。
"""

from fastapi import FastAPI

from app.assessment.router import router as assessment_router
from app.auth.router import router as auth_router
from app.conversation.router import router as conversation_router
from app.profile.router import router as profile_router

# 创建 FastAPI 应用实例。
#
# title 和 version 不会改变业务逻辑，但会显示在 /docs 的接口文档中，也方便
# 运维人员通过接口确认当前运行的是哪个版本。
app = FastAPI(title="Nutrition Agent API", version="0.1.0")
app.include_router(auth_router)
app.include_router(assessment_router)
app.include_router(profile_router)
app.include_router(conversation_router)


@app.get("/health")
def health() -> dict[str, str]:
    """返回服务存活状态，供本地开发和容器健康检查使用。

    ``@app.get("/health")`` 是路由装饰器：它把下面的 Python 函数绑定到
    ``GET /health`` 请求。访问这个地址时，FastAPI 会自动调用 health()，并把
    返回的字典序列化成 JSON。
    """
    return {
        "status": "ok",
        "service": "nutrition-agent-api",
    }
