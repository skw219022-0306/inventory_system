from flask import Blueprint, request, redirect, url_for, flash, current_app
from models import db, Product, Category, Review
from auth_utils import admin_required
from werkzeug.utils import secure_filename
import os

products_bp = Blueprint('products', __name__)

@products_bp.route('/categories/add', methods=['POST'])
@admin_required
def add_category():
    try:
        name = request.form.get('name')
        description = request.form.get('description')
        
        category = Category(name=name, description=description)
        db.session.add(category)
        db.session.commit()
        
        flash('カテゴリが追加されました', 'success')
    except Exception as e:
        flash('カテゴリの追加に失敗しました', 'error')
    
    return redirect(url_for('admin.admin_products'))

@products_bp.route('/add', methods=['POST'])
@admin_required
def add_product():
    try:
        name = request.form.get('name')
        description = request.form.get('description')
        price = float(request.form.get('price'))
        stock_quantity = int(request.form.get('stock_quantity', 0))
        category_id = request.form.get('category_id') or None
        
        # 画像アップロード処理
        image_filename = None
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename:
                filename = secure_filename(file.filename)
                if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                    upload_folder = os.path.join(current_app.root_path, 'static', 'uploads')
                    os.makedirs(upload_folder, exist_ok=True)
                    image_filename = f"{name}_{filename}"
                    file.save(os.path.join(upload_folder, image_filename))
        
        product = Product(
            name=name, 
            description=description, 
            price=price, 
            stock_quantity=stock_quantity,
            category_id=category_id,
            image_filename=image_filename
        )
        db.session.add(product)
        db.session.commit()
        
        flash('商品が追加されました', 'success')
    except Exception as e:
        flash('商品の追加に失敗しました', 'error')
    
    return redirect(url_for('admin.admin_products'))

@products_bp.route('/edit/<int:product_id>', methods=['POST'])
@admin_required
def edit_product(product_id):
    try:
        product = Product.query.get_or_404(product_id)
        
        product.name = request.form.get('name')
        product.description = request.form.get('description')
        product.price = float(request.form.get('price'))
        product.category_id = request.form.get('category_id') or None
        
        db.session.commit()
        flash('商品が更新されました', 'success')
    except Exception as e:
        flash('商品の更新に失敗しました', 'error')
    
    return redirect(url_for('admin.admin_products'))