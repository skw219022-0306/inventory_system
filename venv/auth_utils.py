from functools import wraps
from flask import session, redirect, url_for, flash

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('ログインが必要です', 'error')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('ログインが必要です', 'error')
            return redirect(url_for('auth.login'))
        if session.get('role') != 'admin':
            flash('管理者権限が必要です', 'error')
            return redirect(url_for('orders.order_index'))
        return f(*args, **kwargs)
    return decorated_function