import os
import py_eureka_client.eureka_client as eureka_client

HOST = os.getenv(
    "HOSTNAME",
    "ocr-dr2b.onrender.com"
)

PORT = int(os.getenv("PORT", "8000"))

EUREKA_SERVER = os.getenv(
    "EUREKA_SERVER",
    "https://admin:admin123@eurekadiscoveryserver-ick0.onrender.com/eureka/"
)

async def register():
    await eureka_client.init_async(
        eureka_server=EUREKA_SERVER,
        app_name="OCR-SERVICE",
        instance_host=HOST,
        instance_port=PORT,
        instance_id=f"{HOST}:{PORT}",
        home_page_url=f"https://{HOST}",
        status_page_url=f"https://{HOST}/health",
        health_check_url=f"https://{HOST}/health",
    )