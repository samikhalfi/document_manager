from flask import Flask
from .routes import main  # Import your blueprint here

def create_app():
    app = Flask(__name__, static_folder='static',template_folder='templates') # Flask will automatically look for a /static folder

    # Register the blueprint that contains your routes
    app.register_blueprint(main)

    # Set the secret key for session management
    app.config['SECRET_KEY'] = '1234'  
    
    return app
