import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'AutoQuote-Secret-Key-2024-Muito-Longa-32-Chars')
    SESSION_TYPE = 'filesystem'
    LOG_FOLDER = 'logs'
    LOG_FILE = 'autoquote.log'
    
    # Supabase Configuration
    SUPABASE_URL = os.getenv('SUPABASE_URL', "https://rzglsaargcpwewrgzwtx.supabase.co")
    SUPABASE_KEY = os.getenv('SUPABASE_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJ6Z2xzYWFyZ2Nwd2V3cmd6d3R4Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2NzY4NTA2NCwiZXhwIjoyMDgzMjYxMDY0fQ.A-1z2X-YdqEA083Kbso4kSnkbJPngHRR6dTiGvnM9p0')
    
    # Email Configuration
    MAIL_SERVER = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.getenv('MAIL_PORT', 587))
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER')