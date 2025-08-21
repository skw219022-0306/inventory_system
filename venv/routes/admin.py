from flask import Blueprint, render_template
from models import db, Product, Order, InventoryTransaction, Category
from auth_utils import admin_required

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/')
@admin_required
def admin_dashboard():
    total_products = Product.query.count()
    total_orders = Order.query.count()
    low_stock_products = Product.query.filter(Product.stock_quantity < 10).count()
    
    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(5).all()
    low_stock_items = Product.query.filter(Product.stock_quantity < 10).all()
    
    total_revenue = db.session.query(db.func.sum(Order.total_amount)).filter(Order.status == 'completed').scalar() or 0
    
    return render_template('admin/dashboard.html', 
                         total_products=total_products,
                         total_orders=total_orders,
                         low_stock_products=low_stock_products,
                         recent_orders=recent_orders,
                         low_stock_items=low_stock_items,
                         total_revenue=total_revenue)

@admin_bp.route('/products')
@admin_required
def admin_products():
    products = Product.query.all()
    categories = Category.query.all()
    return render_template('admin/products.html', products=products, categories=categories)

@admin_bp.route('/inventory')
@admin_required
def admin_inventory():
    products = Product.query.all()
    transactions = InventoryTransaction.query.order_by(InventoryTransaction.created_at.desc()).limit(20).all()
    return render_template('admin/inventory.html', products=products, transactions=transactions)

@admin_bp.route('/orders')
@admin_required
def admin_orders():
    orders = Order.query.order_by(Order.created_at.desc()).all()
    return render_template('admin/orders.html', orders=orders)