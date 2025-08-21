from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session, current_app
from models import db, Product, Order, OrderItem, InventoryTransaction, Customer, PointTransaction, Category, Review
from sqlalchemy import func
from auth_utils import login_required
import json

orders_bp = Blueprint('orders', __name__)

@orders_bp.route('/')
@login_required
def order_index():
    search = request.args.get('search', '')
    category_id = request.args.get('category_id')
    sort_by = request.args.get('sort_by', 'name')
    
    query = Product.query.filter(Product.stock_quantity > 0)
    
    if search:
        query = query.filter(Product.name.contains(search))
    
    if category_id:
        query = query.filter(Product.category_id == category_id)
    
    if sort_by == 'price_asc':
        query = query.order_by(Product.price.asc())
    elif sort_by == 'price_desc':
        query = query.order_by(Product.price.desc())
    elif sort_by == 'rating':
        query = query.outerjoin(Review).group_by(Product.id).order_by(db.func.avg(Review.rating).desc().nullslast())
    else:
        query = query.order_by(Product.name)
    
    products = query.all()
    categories = Category.query.all()
    
    return render_template('order/index.html', 
                         products=products, 
                         categories=categories,
                         search=search,
                         category_id=int(category_id) if category_id else None,
                         sort_by=sort_by)

@orders_bp.route('/add_to_cart', methods=['POST'])
@login_required
def add_to_cart():
    product_id = request.form.get('product_id')
    quantity = int(request.form.get('quantity', 1))
    
    product = Product.query.get_or_404(product_id)
    
    if product.stock_quantity < quantity:
        flash('在庫が不足しています', 'error')
        return redirect(url_for('orders.order_index'))
    
    cart = request.cookies.get('cart', '{}')
    cart_data = json.loads(cart) if cart else {}
    
    if str(product_id) in cart_data:
        new_quantity = cart_data[str(product_id)] + quantity
        if product.stock_quantity < new_quantity:
            flash(f'在庫が不足しています。現在の在庫数：{product.stock_quantity}個', 'error')
            return redirect(url_for('orders.order_index'))
        cart_data[str(product_id)] = new_quantity
    else:
        cart_data[str(product_id)] = quantity
    
    response = redirect(url_for('orders.order_index'))
    response.set_cookie('cart', json.dumps(cart_data))
    flash(f'{product.name} をカートに追加しました', 'success')
    return response

@orders_bp.route('/cart')
@login_required
def view_cart():
    cart = request.cookies.get('cart', '{}')
    cart_data = json.loads(cart) if cart else {}
    
    cart_items = []
    total = 0
    
    for product_id, quantity in cart_data.items():
        product = Product.query.get(int(product_id))
        if product:
            subtotal = product.price * quantity
            cart_items.append({
                'product': product,
                'quantity': quantity,
                'subtotal': subtotal
            })
            total += subtotal
    
    return render_template('order/cart.html', cart_items=cart_items, total=total)

@orders_bp.route('/checkout', methods=['POST'])
@login_required
def checkout():
    customer_name = request.form.get('customer_name')
    customer_email = request.form.get('customer_email')
    points_to_use = int(request.form.get('points_to_use', 0))
    
    if not customer_name or not customer_email:
        flash('お名前とメールアドレスを入力してください', 'error')
        return redirect(url_for('orders.view_cart'))
    
    cart = request.cookies.get('cart', '{}')
    cart_data = json.loads(cart) if cart else {}
    
    if not cart_data:
        flash('カートが空です', 'error')
        return redirect(url_for('orders.order_index'))
    
    try:
        # 顧客情報の取得または作成
        customer = Customer.query.filter_by(email=customer_email).first()
        if not customer:
            customer = Customer(name=customer_name, email=customer_email)
            db.session.add(customer)
            db.session.flush()
        
        # ポイント使用チェック
        if points_to_use > customer.points:
            flash('使用可能ポイントを超えています', 'error')
            return redirect(url_for('orders.view_cart'))
        
        for product_id, quantity in cart_data.items():
            product = Product.query.get(int(product_id))
            if not product:
                flash(f'商品が見つかりません', 'error')
                return redirect(url_for('orders.view_cart'))
            if product.stock_quantity < quantity:
                flash(f'{product.name}の在庫が不足しています（現在庫：{product.stock_quantity}個）', 'error')
                return redirect(url_for('orders.view_cart'))
        
        subtotal_amount = 0
        points_earned = 0
        
        for product_id, quantity in cart_data.items():
            product = Product.query.get(int(product_id))
            subtotal_amount += product.price * quantity
            points_earned += int(product.price * quantity * product.point_rate)
        
        # 消費税計算
        tax_rate = current_app.config['TAX_RATE']
        discount_amount = points_to_use
        discounted_subtotal = max(0, subtotal_amount - discount_amount)
        tax_amount = discounted_subtotal * tax_rate
        final_amount = discounted_subtotal + tax_amount
        
        order = Order(
            customer_id=customer.id,
            customer_name=customer_name, 
            customer_email=customer_email, 
            subtotal_amount=subtotal_amount,
            tax_amount=tax_amount,
            total_amount=final_amount,
            discount_amount=discount_amount,
            points_used=points_to_use,
            points_earned=points_earned,
            status='pending'
        )
        db.session.add(order)
        db.session.flush()
        
        for product_id, quantity in cart_data.items():
            product = Product.query.get(int(product_id))
            
            order_item = OrderItem(
                order_id=order.id,
                product_id=product.id,
                quantity=quantity,
                unit_price=product.price
            )
            db.session.add(order_item)
            
            product.stock_quantity -= quantity
            
            transaction = InventoryTransaction(
                product_id=product.id,
                transaction_type='out',
                quantity=quantity,
                notes=f'注文 #{order.id} ({customer_name}) による出庫'
            )
            db.session.add(transaction)
        
        # ポイント処理
        if points_to_use > 0:
            customer.points -= points_to_use
            point_transaction = PointTransaction(
                customer_id=customer.id,
                order_id=order.id,
                points=-points_to_use,
                transaction_type='used',
                notes=f'注文 #{order.id} でポイント使用'
            )
            db.session.add(point_transaction)
        
        if points_earned > 0:
            customer.points += points_earned
            point_transaction = PointTransaction(
                customer_id=customer.id,
                order_id=order.id,
                points=points_earned,
                transaction_type='earned',
                notes=f'注文 #{order.id} でポイント獲得'
            )
            db.session.add(point_transaction)
        
        order.status = 'completed'
        session['customer_email'] = customer_email
        
        db.session.commit()
        
        response = redirect(url_for('orders.order_success', order_id=order.id))
        response.set_cookie('cart', '', expires=0)
        
        flash(f'注文が完了しました。注文番号: {order.id}', 'success')
        return response
        
    except Exception as e:
        db.session.rollback()
        flash('注文処理中にエラーが発生しました。もう一度お試しください。', 'error')
        return redirect(url_for('orders.view_cart'))

@orders_bp.route('/order_success')
@orders_bp.route('/order_success/<int:order_id>')
@login_required
def order_success(order_id=None):
    order = None
    if order_id:
        order = Order.query.get(order_id)
    return render_template('order/success.html', order=order)

@orders_bp.route('/review/<int:product_id>', methods=['POST'])
@login_required
def add_review(product_id):
    try:
        customer_email = session.get('customer_email')
        if not customer_email:
            flash('レビューを投稿するには顧客情報が必要です', 'error')
            return redirect(url_for('orders.order_index'))
        
        customer = Customer.query.filter_by(email=customer_email).first()
        if not customer:
            flash('顧客情報が見つかりません', 'error')
            return redirect(url_for('orders.order_index'))
        
        rating = int(request.form.get('rating'))
        comment = request.form.get('comment', '')
        
        # 既存レビューのチェック
        existing_review = Review.query.filter_by(product_id=product_id, customer_id=customer.id).first()
        if existing_review:
            flash('この商品には既にレビューを投稿しています', 'error')
            return redirect(url_for('orders.order_index'))
        
        review = Review(
            product_id=product_id,
            customer_id=customer.id,
            rating=rating,
            comment=comment
        )
        db.session.add(review)
        db.session.commit()
        
        flash('レビューを投稿しました', 'success')
    except Exception as e:
        flash('レビューの投稿に失敗しました', 'error')
    
    return redirect(url_for('orders.order_index'))