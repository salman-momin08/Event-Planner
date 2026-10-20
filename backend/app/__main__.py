"""Run with: python -m app"""
import uvicorn
from dotenv import load_dotenv

from .config import ConfigError, load_settings
from .main import create_app


def main() -> None:
    load_dotenv()
    try:
        settings = load_settings()
    except ConfigError as err:
        raise SystemExit(f"Invalid configuration: {err}") from None
    app = create_app(settings)
    uvicorn.run(app, host=settings.host, port=settings.port, server_header=False, access_log=False)


if __name__ == "__main__":
    main()
