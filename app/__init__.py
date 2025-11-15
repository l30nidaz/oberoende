from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
import os
from dotenv import load_dotenv
from flask_migrate import Migrate

migrate=Migrate()

load_dotenv()

csrf = CSRFProtect()
db = SQLAlchemy()
def create_app():
    app = Flask(__name__)
    
    #Configuración
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("MYSQL_URI")
    app.config['SECRET_KEY'] = os.getenv("SECRET_KEY") or os.urandom(32)
    app.config['SECRET_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['DEBUG'] = False

    #Inicializar extensiones
    db.init_app(app)
    csrf.init_app(app)
    migrate.init_app(app,db)
    
    #Registrar blueprints o rutas aquí
    from app.appointments import bp as appointments_bp
    from app.functions import bp as functions_bp
    from app._____whatsapp import bp as whatsapp_bp
    from app.my_collections import bp as my_collections_bp
    from app.users import bp as users_bp
    from app.calendly_webhook import bp as calendly_bp

    app.register_blueprint(calendly_bp)
    app.register_blueprint(appointments_bp)
    app.register_blueprint(functions_bp)
    app.register_blueprint(whatsapp_bp)
    app.register_blueprint(my_collections_bp)
    app.register_blueprint(users_bp)
    
    
    return app