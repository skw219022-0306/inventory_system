from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from models import db, Product, Order, OrderItem
from auth_utils import admin_required
from datetime import datetime, timedelta
from sqlalchemy import func
import statistics

ai_bp = Blueprint('ai_system', __name__)

@ai_bp.route('/')
@admin_required
def ai_dashboard():
    return render_template('admin/ai_dashboard.html')

@ai_bp.route('/demand_forecast')
@admin_required
def demand_forecast():
    products = Product.query.all()
    forecasts = []
    
    for product in products:
        # 過去30日の売上データ
        thirty_days_ago = datetime.now() - timedelta(days=30)
        sales_data = db.session.query(
            func.date(Order.created_at).label('date'),
            func.sum(OrderItem.quantity).label('quantity')
        ).join(OrderItem).filter(
            OrderItem.product_id == product.id,
            Order.created_at >= thirty_days_ago,
            Order.status == 'completed'
        ).group_by(func.date(Order.created_at)).all()
        
        if len(sales_data) >= 7:  # 最低7日のデータが必要
            quantities = [float(data.quantity) for data in sales_data]
            
            # 単純移動平均による予測
            avg_daily_sales = statistics.mean(quantities)
            trend = (quantities[-3:] and statistics.mean(quantities[-3:]) or 0) - (quantities[:3] and statistics.mean(quantities[:3]) or 0)
            
            # 7日後の予測
            forecast_7days = max(0, avg_daily_sales + trend) * 7
            forecast_30days = max(0, avg_daily_sales + trend) * 30
            
            forecasts.append({
                'product': product,
                'current_sales': avg_daily_sales,
                'trend': trend,
                'forecast_7days': round(forecast_7days),
                'forecast_30days': round(forecast_30days),
                'confidence': min(100, len(sales_data) * 10)  # データ量に基づく信頼度
            })
    
    return render_template('admin/demand_forecast.html', forecasts=forecasts)

@ai_bp.route('/dynamic_pricing')
@admin_required
def dynamic_pricing():
    products = Product.query.all()
    pricing_suggestions = []
    
    for product in products:
        # 在庫回転率計算
        thirty_days_ago = datetime.now() - timedelta(days=30)
        sold_quantity = db.session.query(func.sum(OrderItem.quantity)).join(Order).filter(
            OrderItem.product_id == product.id,
            Order.created_at >= thirty_days_ago,
            Order.status == 'completed'
        ).scalar() or 0
        
        turnover_rate = sold_quantity / max(1, product.stock_quantity)
        
        # 価格調整提案
        current_price = product.price
        if turnover_rate > 2:  # 高回転
            suggested_price = current_price * 1.1  # 10%値上げ
            reason = "高需要のため値上げ推奨"
        elif turnover_rate < 0.5 and product.stock_quantity > 20:  # 低回転・過剰在庫
            suggested_price = current_price * 0.9  # 10%値下げ
            reason = "在庫過多のため値下げ推奨"
        else:
            suggested_price = current_price
            reason = "現在価格を維持"
        
        pricing_suggestions.append({
            'product': product,
            'current_price': current_price,
            'suggested_price': round(suggested_price),
            'turnover_rate': round(turnover_rate, 2),
            'reason': reason
        })
    
    return render_template('admin/dynamic_pricing.html', pricing_suggestions=pricing_suggestions)

@ai_bp.route('/optimal_order')
@admin_required
def optimal_order():
    products = Product.query.all()
    order_suggestions = []
    
    for product in products:
        # 過去の売上パターン分析
        thirty_days_ago = datetime.now() - timedelta(days=30)
        avg_daily_sales = db.session.query(func.avg(OrderItem.quantity)).join(Order).filter(
            OrderItem.product_id == product.id,
            Order.created_at >= thirty_days_ago,
            Order.status == 'completed'
        ).scalar() or 0
        
        # 安全在庫（7日分）
        safety_stock = avg_daily_sales * 7
        
        # 最適発注量（30日分 + 安全在庫 - 現在庫）
        optimal_order_qty = max(0, (avg_daily_sales * 30) + safety_stock - product.stock_quantity)
        
        # 発注優先度
        days_until_stockout = product.stock_quantity / max(0.1, avg_daily_sales)
        
        if days_until_stockout < 7:
            priority = "緊急"
        elif days_until_stockout < 14:
            priority = "高"
        elif days_until_stockout < 30:
            priority = "中"
        else:
            priority = "低"
        
        order_suggestions.append({
            'product': product,
            'avg_daily_sales': round(avg_daily_sales, 1),
            'days_until_stockout': round(days_until_stockout, 1),
            'optimal_order_qty': round(optimal_order_qty),
            'priority': priority
        })
    
    # 優先度順にソート
    priority_order = {"緊急": 0, "高": 1, "中": 2, "低": 3}
    order_suggestions.sort(key=lambda x: priority_order[x['priority']])
    
    return render_template('admin/optimal_order.html', order_suggestions=order_suggestions)

@ai_bp.route('/anomaly_detection')
@admin_required
def anomaly_detection():
    anomalies = []
    
    # 売上異常検知
    seven_days_ago = datetime.now() - timedelta(days=7)
    fourteen_days_ago = datetime.now() - timedelta(days=14)
    
    # 過去7日と前の7日の売上比較
    recent_sales = db.session.query(func.sum(Order.total_amount)).filter(
        Order.created_at >= seven_days_ago,
        Order.status == 'completed'
    ).scalar() or 0
    
    previous_sales = db.session.query(func.sum(Order.total_amount)).filter(
        Order.created_at >= fourteen_days_ago,
        Order.created_at < seven_days_ago,
        Order.status == 'completed'
    ).scalar() or 0
    
    if previous_sales > 0:
        sales_change = ((recent_sales - previous_sales) / previous_sales) * 100
        if abs(sales_change) > 30:  # 30%以上の変動
            anomalies.append({
                'type': '売上異常',
                'description': f'売上が前週比{sales_change:+.1f}%変動',
                'severity': '高' if abs(sales_change) > 50 else '中',
                'date': datetime.now().strftime('%Y-%m-%d')
            })
    
    # 商品別異常検知
    for product in Product.query.all():
        # 在庫切れ警告
        if product.stock_quantity == 0:
            anomalies.append({
                'type': '在庫切れ',
                'description': f'{product.name}の在庫が0になりました',
                'severity': '高',
                'date': datetime.now().strftime('%Y-%m-%d')
            })
        
        # 異常な売上パターン
        recent_orders = db.session.query(func.sum(OrderItem.quantity)).join(Order).filter(
            OrderItem.product_id == product.id,
            Order.created_at >= seven_days_ago,
            Order.status == 'completed'
        ).scalar() or 0
        
        if recent_orders > product.stock_quantity * 0.8:  # 在庫の80%以上が売れた
            anomalies.append({
                'type': '急激な需要増加',
                'description': f'{product.name}の需要が急増しています',
                'severity': '中',
                'date': datetime.now().strftime('%Y-%m-%d')
            })
    
    return render_template('admin/anomaly_detection.html', anomalies=anomalies)

@ai_bp.route('/apply_pricing/<int:product_id>', methods=['POST'])
@admin_required
def apply_pricing(product_id):
    try:
        product = Product.query.get_or_404(product_id)
        new_price = float(request.form.get('new_price'))
        
        product.price = new_price
        db.session.commit()
        
        flash(f'{product.name}の価格を¥{new_price:,.0f}に更新しました', 'success')
    except Exception as e:
        flash('価格更新に失敗しました', 'error')
    
    return redirect(url_for('ai_system.dynamic_pricing'))