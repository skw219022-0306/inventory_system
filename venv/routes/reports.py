from flask import Blueprint, render_template, request
from models import db, Product, Order, OrderItem, InventoryTransaction
from auth_utils import admin_required
from datetime import datetime, timedelta
from sqlalchemy import func, desc

reports_bp = Blueprint('reports', __name__)

@reports_bp.route('/')
@admin_required
def reports_dashboard():
    return render_template('admin/reports.html')

@reports_bp.route('/sales')
@admin_required
def sales_report():
    period = request.args.get('period', 'daily')
    
    if period == 'daily':
        # 日別売上
        sales_data = db.session.query(
            func.date(Order.created_at).label('date'),
            func.sum(Order.total_amount).label('total'),
            func.count(Order.id).label('orders')
        ).filter(Order.status == 'completed').group_by(func.date(Order.created_at)).order_by(desc('date')).limit(30).all()
    else:
        # 月別売上
        sales_data = db.session.query(
            func.strftime('%Y-%m', Order.created_at).label('month'),
            func.sum(Order.total_amount).label('total'),
            func.count(Order.id).label('orders')
        ).filter(Order.status == 'completed').group_by(func.strftime('%Y-%m', Order.created_at)).order_by(desc('month')).limit(12).all()
    
    # 商品別売上
    product_sales = db.session.query(
        Product.name,
        func.sum(OrderItem.quantity).label('quantity'),
        func.sum(OrderItem.quantity * OrderItem.unit_price).label('revenue')
    ).join(OrderItem).join(Order).filter(Order.status == 'completed').group_by(Product.name).order_by(desc('revenue')).limit(10).all()
    
    return render_template('admin/sales_report.html', 
                         sales_data=sales_data, 
                         product_sales=product_sales, 
                         period=period)

@reports_bp.route('/inventory')
@admin_required
def inventory_report():
    # 在庫切れ・少ない商品
    low_stock = Product.query.filter(Product.stock_quantity < 10).all()
    out_of_stock = Product.query.filter(Product.stock_quantity == 0).all()
    
    # 在庫回転率（売上数量/平均在庫）
    thirty_days_ago = datetime.now() - timedelta(days=30)
    inventory_turnover = db.session.query(
        Product.name,
        Product.stock_quantity,
        func.coalesce(func.sum(OrderItem.quantity), 0).label('sold_quantity')
    ).outerjoin(OrderItem).outerjoin(Order).filter(
        db.or_(Order.created_at >= thirty_days_ago, Order.created_at.is_(None))
    ).group_by(Product.id).all()
    
    return render_template('admin/inventory_report.html',
                         low_stock=low_stock,
                         out_of_stock=out_of_stock,
                         inventory_turnover=inventory_turnover)

@reports_bp.route('/customers')
@admin_required
def customer_report():
    # 顧客別購入履歴
    customer_stats = db.session.query(
        Order.customer_email,
        Order.customer_name,
        func.count(Order.id).label('order_count'),
        func.sum(Order.total_amount).label('total_spent'),
        func.max(Order.created_at).label('last_order')
    ).filter(Order.status == 'completed').group_by(Order.customer_email).order_by(desc('total_spent')).limit(20).all()
    
    # リピート顧客
    repeat_customers = db.session.query(
        Order.customer_email,
        func.count(Order.id).label('order_count')
    ).filter(Order.status == 'completed').group_by(Order.customer_email).having(func.count(Order.id) > 1).all()
    
    total_customers = db.session.query(func.count(func.distinct(Order.customer_email))).filter(Order.status == 'completed').scalar()
    repeat_rate = (len(repeat_customers) / total_customers * 100) if total_customers > 0 else 0
    
    return render_template('admin/customer_report.html',
                         customer_stats=customer_stats,
                         repeat_rate=repeat_rate,
                         total_customers=total_customers)