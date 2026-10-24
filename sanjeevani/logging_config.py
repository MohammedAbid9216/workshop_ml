import logging, os
from .config import settings

def setup_logging():
    os.makedirs(settings.log_dir, exist_ok=True)
    root = logging.getLogger("sanjeevani")
    if root.handlers:
        return root
    root.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    for name in ("app", "auth", "chatbot", "database", "payment", "audit", "error"):
        logger = logging.getLogger(f"sanjeevani.{name}")
        logger.setLevel(logging.INFO)
        fh = logging.FileHandler(os.path.join(settings.log_dir, f"{name}.log"), encoding="utf-8")
        fh.setFormatter(fmt)
        logger.addHandler(fh)
    return root
