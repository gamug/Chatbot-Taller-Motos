import os
import config

def check_directories():
    """Ensure that all configured directories exist on the filesystem.

    This function iterates over the directory paths defined in the configuration
    and creates any that do not already exist.

    Args:
        None

    Returns:
        None
    """
    for dir in config.path.values():
        os.makedirs(dir, exist_ok=True)