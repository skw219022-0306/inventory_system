from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from models import db, Customer, Order, PointTransaction
from auth_utils import admin_required, login_required

customers_bp = Blueprint('customers', __name__)

@customers_bp.route('/')
@admin_required
def customer_list():
    customers = Customer.query.all()
    return render_template('admin/customers.html', customers=customers)

@customers_bp.route('/add', methods=['POST'])
@admin_required
def add_customer():
    try:
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        address = request.form.get('address')
        
        if Customer.query.filter_by(email=email).first():
            flash('そのメールアドレスは既に登録されています', 'error')
            return redirect(url_for('customers.customer_list'))
        
        customer = Customer(name=name, email=email, phone=phone, address=address)
        db.session.add(customer)
        db.session.commit()
        
        flash('顧客が追加されました', 'success')
    except Exception as e:
        flash('顧客の追加に失敗しました', 'error')
    
    return redirect(url_for('customers.customer_list'))

@customers_bp.route('/edit/<int:customer_id>', methods=['POST'])
@admin_required
def edit_customer(customer_id):
    try:
        customer = Customer.query.get_or_404(customer_id)
        
        customer.name = request.form.get('name')
        customer.phone = request.form.get('phone')
        customer.address = request.form.get('address')
        
        db.session.commit()
        flash('顧客情報が更新されました', 'success')
    except Exception as e:
        flash('顧客情報の更新に失敗しました', 'error')
    
    return redirect(url_for('customers.customer_list'))

@customers_bp.route('/detail/<int:customer_id>')
@admin_required
def customer_detail(customer_id):
    customer = Customer.query.get_or_404(customer_id)
    orders = Order.query.filter_by(customer_id=customer_id).order_by(Order.created_at.desc()).all()
    point_history = PointTransaction.query.filter_by(customer_id=customer_id).order_by(PointTransaction.created_at.desc()).all()
    
    return render_template('admin/customer_detail.html', 
                         customer=customer, 
                         orders=orders, 
                         point_history=point_history)

@customers_bp.route('/points/add', methods=['POST'])
@admin_required
def add_points():
    try:
        customer_id = request.form.get('customer_id')
        points = int(request.form.get('points'))
        notes = request.form.get('notes', '')
        
        customer = Customer.query.get_or_404(customer_id)
        customer.points += points
        
        point_transaction = PointTransaction(
            customer_id=customer_id,
            points=points,
            transaction_type='earned',
            notes=notes
        )
        
        db.session.add(point_transaction)
        db.session.commit()
        
        flash(f'{points}ポイントを追加しました', 'success')
    except Exception as e:
        flash('ポイントの追加に失敗しました', 'error')
    
    return redirect(url_for('customers.customer_detail', customer_id=customer_id))

@customers_bp.route('/profile')
@login_required
def customer_profile():
    email = session.get('customer_email')
    if not email:
        flash('顧客情報が見つかりません', 'error')
        return redirect(url_for('orders.order_index'))
    
    customer = Customer.query.filter_by(email=email).first()
    if not customer:
        flash('顧客情報が見つかりません', 'error')
        return redirect(url_for('orders.order_index'))
    
    orders = Order.query.filter_by(customer_id=customer.id).order_by(Order.created_at.desc()).all()
    point_history = PointTransaction.query.filter_by(customer_id=customer.id).order_by(PointTransaction.created_at.desc()).limit(10).all()
    
    return render_template('customer/profile.html', 
                         customer=customer, 
                         orders=orders, 
                         point_history=point_history)