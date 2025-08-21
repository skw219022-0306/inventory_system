from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from models import db, User

users_bp = Blueprint('users', __name__)

@users_bp.route('/')
def user_list():
    if session.get('role') != 'admin':
        flash('管理者権限が必要です', 'error')
        return redirect(url_for('orders.order_index'))
    
    users = User.query.all()
    return render_template('admin/users.html', users=users)

@users_bp.route('/add', methods=['POST'])
def add_user():
    if session.get('role') != 'admin':
        flash('管理者権限が必要です', 'error')
        return redirect(url_for('orders.order_index'))
    
    try:
        username = request.form.get('username')
        password = request.form.get('password')
        role = request.form.get('role')
        
        if User.query.filter_by(username=username).first():
            flash('そのユーザー名は既に使用されています', 'error')
            return redirect(url_for('users.user_list'))
        
        user = User(username=username, role=role)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        flash('ユーザーが追加されました', 'success')
    except Exception as e:
        flash('ユーザーの追加に失敗しました', 'error')
    
    return redirect(url_for('users.user_list'))

@users_bp.route('/edit/<int:user_id>', methods=['POST'])
def edit_user(user_id):
    if session.get('role') != 'admin':
        flash('管理者権限が必要です', 'error')
        return redirect(url_for('orders.order_index'))
    
    try:
        user = User.query.get_or_404(user_id)
        user.role = request.form.get('role')
        
        password = request.form.get('password')
        if password:
            user.set_password(password)
        
        db.session.commit()
        flash('ユーザーが更新されました', 'success')
    except Exception as e:
        flash('ユーザーの更新に失敗しました', 'error')
    
    return redirect(url_for('users.user_list'))

@users_bp.route('/delete/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    if session.get('role') != 'admin':
        flash('管理者権限が必要です', 'error')
        return redirect(url_for('orders.order_index'))
    
    try:
        user = User.query.get_or_404(user_id)
        if user.id == session.get('user_id'):
            flash('自分自身は削除できません', 'error')
            return redirect(url_for('users.user_list'))
        
        db.session.delete(user)
        db.session.commit()
        flash('ユーザーが削除されました', 'success')
    except Exception as e:
        flash('ユーザーの削除に失敗しました', 'error')
    
    return redirect(url_for('users.user_list'))