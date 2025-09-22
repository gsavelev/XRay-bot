import os
from dotenv import load_dotenv
from pydantic import BaseModel, Field, field_validator
from typing import List

load_dotenv()

class Config(BaseModel):
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    ADMINS: List[int] = Field(default_factory=list)
    CHAT_ID: int = Field(default=os.getenv("CHAT_ID"))
    XUI_API_URL: str = os.getenv("XUI_API_URL", "http://localhost:54321")
    XUI_BASE_PATH: str = os.getenv("XUI_BASE_PATH", "/panel")
    XUI_USERNAME: str = os.getenv("XUI_USERNAME", "admin")
    XUI_PASSWORD: str = os.getenv("XUI_PASSWORD", "admin")
    XUI_HOST: str = os.getenv("XUI_HOST", "your-server.com")
    XUI_SERVER_NAME: str = os.getenv("XUI_SERVER_NAME", "domain.com")
    INBOUND_ID: int = Field(default=os.getenv("INBOUND_ID", 1))
    REALITY_PUBLIC_KEY: str = os.getenv("REALITY_PUBLIC_KEY", "")
    REALITY_FINGERPRINT: str = os.getenv("REALITY_FINGERPRINT", "chrome")
    REALITY_SNI: str = os.getenv("REALITY_SNI", "example.com")
    REALITY_SHORT_ID: str = os.getenv("REALITY_SHORT_ID", "1234567890")
    REALITY_SPIDER_X: str = os.getenv("REALITY_SPIDER_X", "/")

    @field_validator('ADMINS', mode='before')
    def parse_admins(cls, value):
        if isinstance(value, str):
            return [int(admin) for admin in value.split(",") if admin.strip()]
        return value or []

    @field_validator('CHAT_ID', mode='before')
    def parse_chat_id(cls, value):
        if isinstance(value, str):
            return int(value)
        return value
    
    @field_validator('INBOUND_ID', mode='before')
    def parse_inbound_id(cls, value):
        if isinstance(value, str):
            return int(value)
        return value or 1
    
config = Config(
    ADMINS=os.getenv("ADMINS", ""),
    CHAT_ID=os.getenv("CHAT_ID"),
    INBOUND_ID=os.getenv("INBOUND_ID", 1),
)