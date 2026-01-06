import os
import logging
from flask import Flask
from flask_session import Session
from app.config import Config

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Inicializar extensões
    Session(app)
    
    # Configurar logs
    _configure_logs(app)
    
    # Registrar blueprints
    _register_blueprints(app)
    
    app.logger.info("✅ AutoQuote aplicação iniciada.")
    return app

def _configure_logs(app):
    """Configura sistema de logs"""
    if not os.path.exists(app.config['LOG_FOLDER']):
        os.makedirs(app.config['LOG_FOLDER'])
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(os.path.join(app.config['LOG_FOLDER'], app.config['LOG_FILE']))
        ]
    )

def _register_blueprints(app):
    """Registra todas as rotas"""
    from app.routes.auth_routes import auth_bp
    from app.routes.main_routes import main_bp
    from app.routes.vale_routes import vale_bp
    from app.routes.profile_routes import profile_bp
    from app.routes.admin_routes import admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(vale_bp, url_prefix="/vale")
    app.register_blueprint(profile_bp, url_prefix="/profile")
    app.register_blueprint(admin_bp, url_prefix="/admin")
