from app.main import create_app
import config

app = create_app(config.DevelopmentConfig)