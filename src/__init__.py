import config
from src.commons import check_directories
from src.commons import AppLogger

check_directories()

app_logger = AppLogger(config.agent_name)