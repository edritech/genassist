from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class ProjectSettings(BaseSettings):
    def __init__(self, **values):
        super().__init__(**values)

    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # ignore unknown fields instead of raising an error
    )


settings = ProjectSettings()
