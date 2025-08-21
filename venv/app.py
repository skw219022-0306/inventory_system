from flask import Flask, redirect, url_for
from models import db
from config import Config
from utils import create_tables
from routes.orders import orders_bp
from routes.products import products_bp
from routes.inventory import inventory_bp
from routes.admin import admin_bp
from routes.auth import auth_bp
from routes.users import users_bp
from routes.reports import reports_bp
from routes.customers import customers_bp
from routes.ai_system import ai_bp

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)

@app.route('/')
def index():
    return redirect(url_for('auth.login'))

# Blueprintの登録
app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(users_bp, url_prefix='/users')
app.register_blueprint(orders_bp, url_prefix='/orders')
app.register_blueprint(products_bp, url_prefix='/products')
app.register_blueprint(inventory_bp, url_prefix='/inventory')
app.register_blueprint(admin_bp, url_prefix='/admin')
app.register_blueprint(reports_bp, url_prefix='/reports')
app.register_blueprint(customers_bp, url_prefix='/customers')
app.register_blueprint(ai_bp, url_prefix='/ai')

if __name__ == '__main__':
    create_tables(app)
    app.run(debug=True)