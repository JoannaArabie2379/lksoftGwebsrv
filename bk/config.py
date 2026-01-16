import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'lksoftgwebsrv-secret-key-2024'
    
    # Database
    DB_HOST = os.environ.get('DB_HOST', '10.16.10.150')
    DB_PORT = os.environ.get('DB_PORT', '5432')
    DB_NAME = os.environ.get('DB_NAME', 'lksoftgwebsrv')
    DB_USER = os.environ.get('DB_USER', 'lksoftgwebsrv')
    DB_PASSWORD = os.environ.get('DB_PASSWORD', 'lksoftGwebsrv')
    
    DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    
    # Upload settings
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    
    # GIS settings
    SRID_WGS84 = 4326
    SRID_MSK86_ZONE4 = 2502  # МСК-86 зона 4 (приблизительный EPSG код)
    
    # Default admin credentials
    DEFAULT_ADMIN_LOGIN = 'root'
    DEFAULT_ADMIN_PASSWORD = 'Kolobaha00!'
