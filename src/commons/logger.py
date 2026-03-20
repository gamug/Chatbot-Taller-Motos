import logging, os
import config
from logging.handlers import RotatingFileHandler

class AppLogger(logging.Logger):
    def __init__(self, name: str, level=logging.DEBUG):
        super().__init__(name, level)

        # Messages format
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

        # Rotation file Handler
        file_handler = RotatingFileHandler(
            os.path.join(config.path['logs'], 'app.log'), maxBytes=5*1024*1024, backupCount=3
        )
        file_handler.setFormatter(formatter)
        file_handler.stream.reconfigure(encoding='utf-8')

        # Console Handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)

        # Add handlers to the logger
        self.addHandler(file_handler)
        self.addHandler(console_handler)

    # Succeeded logs
    def success(self, message: str) -> None:
        """Personalized log for successes"""
        self.log(logging.INFO, f"SUCCESS ✅: {message}")
    
    # Warning logs
    def warning(self, msg: object) -> None:
        """Personalized log for warnings"""
        self.log(logging.WARNING, f"⚠️ {msg}")
