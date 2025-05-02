from flask import Flask
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from .extensions import db

def create_app():
    app = Flask(__name__)
    # CORS(app)
    # CORS(app, supports_credentials=True, origins=["*"])
    CORS(app,supports_credentials=True,origins=["*"],resources={
        r"/*": {
            "methods": ["GET", "POST", "PUT", "DELETE"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    })
    app.config.from_object('app.config.Config')
    
    db.init_app(app)
    
    with app.app_context():
        db.create_all()
    
    return app
