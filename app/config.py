import os

class Config:
    # Force PyMySQL usage with explicit dialect
    SQLALCHEMY_DATABASE_URI = os.getenv('MYSQL_URL', 'mysql://root:QKErTqUxrsHQfgLwQrfIuzBFBYFRkpPW@mysql.railway.internal:3306/railway')
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
    }
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key')
    CORS_HEADERS = 'Content-Type'
    SESSION_COOKIE_SECURE = True  # For HTTPS
    SESSION_COOKIE_SAMESITE = 'None'  # For cross-site cookies
