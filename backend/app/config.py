from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    PROJECT_NAME: str = "RESQROUTE Emergency Routing Engine"
    API_V1_STR: str = "/api/v1"
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    ALLOWED_ORIGINS: str = "http://localhost:5173,http://localhost:5174,http://127.0.0.1:5173,http://127.0.0.1:5174"
    OSRM_BASE_URL: str = "http://router.project-osrm.org"

    @property
    def override_cors_origins(self) -> List[str]:
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
