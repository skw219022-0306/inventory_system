from models import db, Product, User, Customer, PointTransaction, Category, Review

def create_tables(app):
    with app.app_context():
        db.create_all()
        
        # デフォルト管理者ユーザーの作成
        if User.query.count() == 0:
            admin_user = User(username='admin', role='admin')
            admin_user.set_password('admin123')
            db.session.add(admin_user)
            db.session.commit()
            print("デフォルト管理者ユーザーを作成しました (admin/admin123)")
        
        if Category.query.count() == 0:
            sample_categories = [
                Category(name='コンピューター', description='PC関連商品'),
                Category(name='周辺機器', description='マウス、キーボードなど'),
                Category(name='アクセサリ', description='その他アクセサリ'),
            ]
            for category in sample_categories:
                db.session.add(category)
            db.session.commit()
        
        if Product.query.count() == 0:
            pc_category = Category.query.filter_by(name='コンピューター').first()
            peripheral_category = Category.query.filter_by(name='周辺機器').first()
            
            sample_products = [
                Product(name='ノートPC', description='高性能ノートパソコン', price=80000, stock_quantity=10, point_rate=0.01, category_id=pc_category.id if pc_category else None),
                Product(name='マウス', description='ワイヤレスマウス', price=2000, stock_quantity=50, point_rate=0.01, category_id=peripheral_category.id if peripheral_category else None),
                Product(name='キーボード', description='メカニカルキーボード', price=8000, stock_quantity=25, point_rate=0.01, category_id=peripheral_category.id if peripheral_category else None),
            ]
            for product in sample_products:
                db.session.add(product)
            db.session.commit()
            print("サンプルデータを追加しました")