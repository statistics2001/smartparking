from app import create_app
from app.extensions import db
from app.routes import init_routes

app = create_app()
init_routes(app)

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
