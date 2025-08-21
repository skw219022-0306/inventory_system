from flask import Blueprint, request, redirect, url_for, flash
from models import db, Product, InventoryTransaction
from auth_utils import admin_required

inventory_bp = Blueprint('inventory', __name__)

@inventory_bp.route('/update', methods=['POST'])
@admin_required
def update_inventory():
    try:
        product_id = request.form.get('product_id')
        transaction_type = request.form.get('transaction_type')
        quantity = int(request.form.get('quantity'))
        notes = request.form.get('notes', '')
        
        product = Product.query.get_or_404(product_id)
        
        old_stock = product.stock_quantity
        
        if transaction_type == 'in':
            product.stock_quantity += quantity
        else:
            if product.stock_quantity < quantity:
                flash('出庫数量が現在の在庫を超えています', 'error')
                return redirect(url_for('admin.admin_inventory'))
            product.stock_quantity -= quantity
        
        transaction = InventoryTransaction(
            product_id=product_id,
            transaction_type=transaction_type,
            quantity=quantity,
            notes=notes
        )
        
        db.session.add(transaction)
        db.session.commit()
        
        flash(f'{product.name}の在庫を更新しました（{old_stock}個 → {product.stock_quantity}個）', 'success')
    except Exception as e:
        flash('在庫の更新に失敗しました', 'error')
    
    return redirect(url_for('admin.admin_inventory'))