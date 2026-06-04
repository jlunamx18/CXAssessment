"""
Database connection configuration.
Values can be overridden via environment variables.
"""

import os

DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "173.214.175.66"),
    "database": os.environ.get("DB_NAME", "eGestionMLV"),
    "user": os.environ.get("DB_USER", "mlv"),
    "password": os.environ.get("DB_PASSWORD", "39313565.jj"),
    "port": int(os.environ.get("DB_PORT", "1433")),
    "charset": "UTF-8",
    "tds_version": os.environ.get("TDS_VERSION", "7.0"),
}

# Application settings
APP_TITLE = "Transport Analytics"
APP_ICON = "🚛"
CACHE_TTL = int(os.environ.get("CACHE_TTL", "3600"))
