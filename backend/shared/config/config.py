from shared.config.settings import ProjectSettings
from configparser import ConfigParser
import os


def load_settings(service_name: str) -> ProjectSettings:
    # load the .env file for the service
    env_file = f".env.{service_name}"
    if not os.path.exists(env_file):
        raise FileNotFoundError(f"Environment file not found: {env_file}")
    config = ConfigParser()
    config.read(env_file)

    # convert the config to a dictionary
    return ProjectSettings(**config)
