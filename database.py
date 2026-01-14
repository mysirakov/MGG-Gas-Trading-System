import os
import json
import pg8000.dbapi
from datetime import datetime
from urllib.parse import urlparse
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ.get('DATABASE_URL')

def get_db_connection():
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL environment variable is not set")
    
    result = urlparse(DATABASE_URL)
    username = result.username
    password = result.password
    database = result.path[1:]
    hostname = result.hostname
    port = result.port or 5432
    
    return pg8000.dbapi.connect(
        user=username,
        password=password,
        host=hostname,
        port=port,
        database=database
    )

def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

def initialize_database_system():
    init_database()
    migrate_json_to_postgres()
    return True

def init_database():
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute('''
        CREATE TABLE IF NOT EXISTS suppliers (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cur.execute('''
        CREATE TABLE IF NOT EXISTS buyers (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cur.execute('''
        CREATE TABLE IF NOT EXISTS payment_methods (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cur.execute('''
        CREATE TABLE IF NOT EXISTS sales (
            id SERIAL PRIMARY KEY,
            contract_date DATE NOT NULL,
            buyer_id INTEGER REFERENCES buyers(id),
            supplier_id INTEGER REFERENCES suppliers(id),
            quantity_mwh DECIMAL(12,4) NOT NULL,
            sales_price_eur_mwh DECIMAL(12,4) NOT NULL,
            purchase_price_eur_mwh DECIMAL(12,4) NOT NULL,
            cost_capacity_eur_mwh DECIMAL(12,4) DEFAULT 0,
            cost_transport_eur_mwh DECIMAL(12,4) DEFAULT 0,
            cost_customs_eur_mwh DECIMAL(12,4) DEFAULT 0,
            margin_eur_mwh DECIMAL(12,4) GENERATED ALWAYS AS (
                sales_price_eur_mwh - purchase_price_eur_mwh - cost_capacity_eur_mwh - cost_transport_eur_mwh - cost_customs_eur_mwh
            ) STORED,
            total_revenue DECIMAL(14,2) GENERATED ALWAYS AS (
                quantity_mwh * sales_price_eur_mwh
            ) STORED,
            total_margin DECIMAL(14,2) GENERATED ALWAYS AS (
                quantity_mwh * (sales_price_eur_mwh - purchase_price_eur_mwh - cost_capacity_eur_mwh - cost_transport_eur_mwh - cost_customs_eur_mwh)
            ) STORED,
            purchase_cost DECIMAL(14,2) GENERATED ALWAYS AS (
                quantity_mwh * purchase_price_eur_mwh
            ) STORED,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            old_id VARCHAR(50)
        )
    ''')
    
    try:
        cur.execute("ALTER TABLE sales ADD COLUMN IF NOT EXISTS supplier_id INTEGER REFERENCES suppliers(id)")
        cur.execute("ALTER TABLE sales ADD COLUMN IF NOT EXISTS cost_customs_eur_mwh DECIMAL(12,4) DEFAULT 0")
    except:
        conn.rollback()
    
    cur.execute('''
        CREATE TABLE IF NOT EXISTS invoices (
            id SERIAL PRIMARY KEY,
            invoice_number VARCHAR(255) NOT NULL,
            supplier_id INTEGER REFERENCES suppliers(id),
            total_amount DECIMAL(14,2) NOT NULL,
            status VARCHAR(50) DEFAULT 'Pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            old_id VARCHAR(50)
        )
    ''')
    
    cur.execute('''
        CREATE TABLE IF NOT EXISTS supplier_payments (
            id SERIAL PRIMARY KEY,
            payment_date DATE NOT NULL,
            supplier_id INTEGER REFERENCES suppliers(id),
            payment_method_id INTEGER REFERENCES payment_methods(id),
            amount_sent_eur DECIMAL(14,2) NOT NULL,
            invoice_id INTEGER REFERENCES invoices(id),
            receipt_date DATE,
            amount_received_eur DECIMAL(14,2),
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            old_id VARCHAR(50)
        )
    ''')
    
    cur.execute('''
        CREATE TABLE IF NOT EXISTS payments_received (
            id SERIAL PRIMARY KEY,
            payment_date DATE NOT NULL,
            buyer_id INTEGER REFERENCES buyers(id),
            amount_eur DECIMAL(14,2) NOT NULL,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            old_id VARCHAR(50)
        )
    ''')
    
    cur.execute('''
        CREATE TABLE IF NOT EXISTS payment_allocations (
            id SERIAL PRIMARY KEY,
            payment_id INTEGER REFERENCES payments_received(id) ON DELETE CASCADE,
            sale_id INTEGER REFERENCES sales(id) ON DELETE CASCADE,
            amount DECIMAL(14,2) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(payment_id, sale_id)
        )
    ''')
    
    conn.commit()
    cur.close()
    conn.close()

def parse_date(date_str):
    if not date_str:
        return None
    if isinstance(date_str, datetime):
        return date_str.date()
    if isinstance(date_str, str):
        for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y']:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue
    return None

def get_or_create_supplier(cur, name):
    if not name:
        return None
    cur.execute('SELECT id FROM suppliers WHERE name = %s', (name,))
    result = cur.fetchone()
    if result:
        return result[0]
    cur.execute('INSERT INTO suppliers (name) VALUES (%s) RETURNING id', (name,))
    result = cur.fetchone()
    return result[0]

def get_or_create_buyer(cur, name):
    if not name:
        return None
    cur.execute('SELECT id FROM buyers WHERE name = %s', (name,))
    result = cur.fetchone()
    if result:
        return result[0]
    cur.execute('INSERT INTO buyers (name) VALUES (%s) RETURNING id', (name,))
    result = cur.fetchone()
    return result[0]

def get_or_create_payment_method(cur, name):
    if not name:
        return None
    cur.execute('SELECT id FROM payment_methods WHERE name = %s', (name,))
    result = cur.fetchone()
    if result:
        return result[0]
    cur.execute('INSERT INTO payment_methods (name) VALUES (%s) RETURNING id', (name,))
    result = cur.fetchone()
    return result[0]

def get_or_create_invoice(cur, invoice_number, supplier_id, total_amount):
    if not invoice_number:
        return None
    cur.execute('SELECT id FROM invoices WHERE invoice_number = %s', (invoice_number,))
    result = cur.fetchone()
    if result:
        return result[0]
    cur.execute('''
        INSERT INTO invoices (invoice_number, supplier_id, total_amount) 
        VALUES (%s, %s, %s) RETURNING id
    ''', (invoice_number, supplier_id, total_amount or 0))
    result = cur.fetchone()
    return result[0]

def migrate_json_to_postgres():
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute('SELECT COUNT(*) FROM sales')
    count = cur.fetchone()[0]
    if count > 0:
        cur.close()
        conn.close()
        return "Data already migrated"
    
    try:
        with open('data/settings.json', 'r') as f:
            settings = json.load(f)
    except:
        settings = {'suppliers': [], 'buyers': [], 'payment_methods': []}
    
    for supplier in settings.get('suppliers', []):
        get_or_create_supplier(cur, supplier)
    for buyer in settings.get('buyers', []):
        get_or_create_buyer(cur, buyer)
    for method in settings.get('payment_methods', []):
        get_or_create_payment_method(cur, method)
    
    old_to_new_sale_ids = {}
    try:
        with open('data/sales.json', 'r') as f:
            sales = json.load(f)
    except:
        sales = []
    
    for sale in sales:
        buyer_id = get_or_create_buyer(cur, sale.get('buyer'))
        supplier_id = get_or_create_supplier(cur, sale.get('supplier', 'GPE'))
        contract_date = parse_date(sale.get('contract_date'))
        
        cur.execute('''
            INSERT INTO sales (
                contract_date, buyer_id, supplier_id, quantity_mwh, sales_price_eur_mwh,
                purchase_price_eur_mwh, cost_capacity_eur_mwh, cost_transport_eur_mwh, 
                cost_customs_eur_mwh, old_id
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
        ''', (
            contract_date,
            buyer_id,
            supplier_id,
            sale.get('quantity_mwh', 0),
            sale.get('sales_price_eur_mwh', 0),
            sale.get('purchase_price_eur_mwh', 0),
            sale.get('cost_capacity_eur_mwh', 0),
            sale.get('cost_transport_eur_mwh', 0),
            sale.get('cost_customs_eur_mwh', 0),
            sale.get('id')
        ))
        new_id = cur.fetchone()[0]
        old_to_new_sale_ids[sale.get('id')] = new_id
    
    try:
        with open('data/purchases.json', 'r') as f:
            purchases = json.load(f)
    except:
        purchases = []
    
    for purchase in purchases:
        supplier_id = get_or_create_supplier(cur, purchase.get('supplier'))
        payment_method_id = get_or_create_payment_method(cur, purchase.get('payment_method'))
        invoice_id = get_or_create_invoice(cur, purchase.get('invoice_number'), supplier_id, purchase.get('amount_sent_eur'))
        
        cur.execute('''
            INSERT INTO supplier_payments (
                payment_date, supplier_id, payment_method_id, amount_sent_eur,
                invoice_id, receipt_date, amount_received_eur, old_id
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ''', (
            parse_date(purchase.get('payment_date')),
            supplier_id,
            payment_method_id,
            purchase.get('amount_sent_eur', 0),
            invoice_id,
            parse_date(purchase.get('receipt_date')),
            purchase.get('amount_received_eur', 0),
            purchase.get('id')
        ))
    
    try:
        with open('data/payments_received.json', 'r') as f:
            payments = json.load(f)
    except:
        payments = []
    
    for payment in payments:
        buyer_id = get_or_create_buyer(cur, payment.get('buyer'))
        notes = payment.get('notes', '')
        if notes == 'nan' or notes is None:
            notes = ''
        
        cur.execute('''
            INSERT INTO payments_received (payment_date, buyer_id, amount_eur, notes, old_id)
            VALUES (%s, %s, %s, %s, %s) RETURNING id
        ''', (
            parse_date(payment.get('payment_date')),
            buyer_id,
            payment.get('amount_eur', 0),
            notes,
            payment.get('id')
        ))
        new_payment_id = cur.fetchone()[0]
        
        for alloc in payment.get('allocations', []):
            old_sale_id = alloc.get('sale_id')
            new_sale_id = old_to_new_sale_ids.get(old_sale_id)
            if new_sale_id:
                cur.execute('''
                    INSERT INTO payment_allocations (payment_id, sale_id, amount)
                    VALUES (%s, %s, %s)
                ''', (new_payment_id, new_sale_id, alloc.get('amount', 0)))
    
    conn.commit()
    cur.close()
    conn.close()
    return "Migration complete"

def get_sales():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        SELECT s.*, b.name as buyer, sup.name as supplier,
            COALESCE((SELECT SUM(amount) FROM payment_allocations WHERE sale_id = s.id), 0) as amount_paid
        FROM sales s
        LEFT JOIN buyers b ON s.buyer_id = b.id
        LEFT JOIN suppliers sup ON s.supplier_id = sup.id
        ORDER BY s.contract_date DESC
    ''')
    rows = cur.fetchall()
    sales = [dict_factory(cur, row) for row in rows]
    cur.close()
    conn.close()
    return sales

def add_sale(contract_date, buyer_name, quantity_mwh, sales_price, purchase_price, capacity_cost, transport_cost, supplier_name=None, customs_cost=0):
    conn = get_db_connection()
    cur = conn.cursor()
    buyer_id = get_or_create_buyer(cur, buyer_name)
    supplier_id = get_or_create_supplier(cur, supplier_name) if supplier_name else None
    cur.execute('''
        INSERT INTO sales (
            contract_date, buyer_id, quantity_mwh, sales_price_eur_mwh,
            purchase_price_eur_mwh, cost_capacity_eur_mwh, cost_transport_eur_mwh, supplier_id, cost_customs_eur_mwh
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
    ''', (contract_date, buyer_id, quantity_mwh, sales_price, purchase_price, capacity_cost, transport_cost, supplier_id, customs_cost))
    sale_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return sale_id

def update_sale(sale_id, contract_date, buyer_name, quantity_mwh, sales_price, purchase_price, capacity_cost, transport_cost, supplier_name=None, customs_cost=0):
    conn = get_db_connection()
    cur = conn.cursor()
    buyer_id = get_or_create_buyer(cur, buyer_name)
    supplier_id = get_or_create_supplier(cur, supplier_name) if supplier_name else None
    cur.execute('''
        UPDATE sales SET
            contract_date = %s, buyer_id = %s, quantity_mwh = %s, sales_price_eur_mwh = %s,
            purchase_price_eur_mwh = %s, cost_capacity_eur_mwh = %s, cost_transport_eur_mwh = %s, supplier_id = %s, cost_customs_eur_mwh = %s
        WHERE id = %s
    ''', (contract_date, buyer_id, quantity_mwh, sales_price, purchase_price, capacity_cost, transport_cost, supplier_id, customs_cost, sale_id))
    conn.commit()
    cur.close()
    conn.close()

def delete_sale(sale_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('DELETE FROM sales WHERE id = %s', (sale_id,))
    conn.commit()
    cur.close()
    conn.close()

def get_payments_received():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        SELECT p.*, b.name as buyer,
            COALESCE((SELECT SUM(amount) FROM payment_allocations WHERE payment_id = p.id), 0) as allocated_amount
        FROM payments_received p
        LEFT JOIN buyers b ON p.buyer_id = b.id
        ORDER BY p.payment_date DESC
    ''')
    rows = cur.fetchall()
    payments = [dict_factory(cur, row) for row in rows]
    cur.close()
    conn.close()
    return payments

def get_payment_allocations(payment_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        SELECT pa.*, s.contract_date, s.total_revenue
        FROM payment_allocations pa
        JOIN sales s ON pa.sale_id = s.id
        WHERE pa.payment_id = %s
    ''', (payment_id,))
    rows = cur.fetchall()
    allocations = [dict_factory(cur, row) for row in rows]
    cur.close()
    conn.close()
    return allocations

def get_unpaid_sales(buyer_name=None):
    conn = get_db_connection()
    cur = conn.cursor()
    query = '''
        SELECT s.*, b.name as buyer,
            s.total_revenue - COALESCE((SELECT SUM(amount) FROM payment_allocations WHERE sale_id = s.id), 0) as outstanding
        FROM sales s
        LEFT JOIN buyers b ON s.buyer_id = b.id
        WHERE s.total_revenue > COALESCE((SELECT SUM(amount) FROM payment_allocations WHERE sale_id = s.id), 0)
    '''
    params = []
    if buyer_name:
        query += ' AND b.name = %s'
        params.append(buyer_name)
    query += ' ORDER BY s.contract_date ASC'
    cur.execute(query, params)
    rows = cur.fetchall()
    sales = [dict_factory(cur, row) for row in rows]
    cur.close()
    conn.close()
    return sales

def add_payment_received(payment_date, buyer_name, amount_eur, notes=''):
    conn = get_db_connection()
    cur = conn.cursor()
    buyer_id = get_or_create_buyer(cur, buyer_name)
    
    cur.execute('''
        INSERT INTO payments_received (payment_date, buyer_id, amount_eur, notes)
        VALUES (%s, %s, %s, %s) RETURNING id
    ''', (payment_date, buyer_id, amount_eur, notes))
    payment_id = cur.fetchone()[0]
    
    cur.execute('''
        SELECT s.id, s.total_revenue,
            s.total_revenue - COALESCE((SELECT SUM(amount) FROM payment_allocations WHERE sale_id = s.id), 0) as outstanding
        FROM sales s
        LEFT JOIN buyers b ON s.buyer_id = b.id
        WHERE b.name = %s
        AND s.total_revenue > COALESCE((SELECT SUM(amount) FROM payment_allocations WHERE sale_id = s.id), 0)
        ORDER BY s.contract_date ASC
    ''', (buyer_name,))
    unpaid_sales = [dict_factory(cur, r) for r in cur.fetchall()]
    
    remaining = float(amount_eur)
    for sale in unpaid_sales:
        if remaining <= 0:
            break
        outstanding = float(sale['outstanding'])
        alloc_amount = min(remaining, outstanding)
        if alloc_amount > 0:
            cur.execute('''
                INSERT INTO payment_allocations (payment_id, sale_id, amount)
                VALUES (%s, %s, %s)
            ''', (payment_id, sale['id'], alloc_amount))
            remaining -= alloc_amount
    
    conn.commit()
    cur.close()
    conn.close()
    return payment_id

def delete_payment(payment_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('DELETE FROM payments_received WHERE id = %s', (payment_id,))
    conn.commit()
    cur.close()
    conn.close()

def get_supplier_payments():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        SELECT sp.*, s.name as supplier, pm.name as payment_method, i.invoice_number
        FROM supplier_payments sp
        LEFT JOIN suppliers s ON sp.supplier_id = s.id
        LEFT JOIN payment_methods pm ON sp.payment_method_id = pm.id
        LEFT JOIN invoices i ON sp.invoice_id = i.id
        ORDER BY sp.payment_date DESC
    ''')
    rows = cur.fetchall()
    payments = [dict_factory(cur, row) for row in rows]
    cur.close()
    conn.close()
    return payments

def add_supplier_payment(payment_date, supplier_name, payment_method_name, amount_sent, invoice_number, receipt_date=None, amount_received=None):
    conn = get_db_connection()
    cur = conn.cursor()
    supplier_id = get_or_create_supplier(cur, supplier_name)
    payment_method_id = get_or_create_payment_method(cur, payment_method_name)
    invoice_id = get_or_create_invoice(cur, invoice_number, supplier_id, amount_sent) if invoice_number else None
    
    cur.execute('''
        INSERT INTO supplier_payments (
            payment_date, supplier_id, payment_method_id, amount_sent_eur,
            invoice_id, receipt_date, amount_received_eur
        ) VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id
    ''', (payment_date, supplier_id, payment_method_id, amount_sent, invoice_id, receipt_date, amount_received))
    payment_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return payment_id

def delete_supplier_payment(payment_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('DELETE FROM supplier_payments WHERE id = %s', (payment_id,))
    conn.commit()
    cur.close()
    conn.close()

def get_invoices():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        SELECT i.*, s.name as supplier,
            COALESCE((SELECT SUM(amount_sent_eur) FROM supplier_payments WHERE invoice_id = i.id), 0) as paid_amount
        FROM invoices i
        LEFT JOIN suppliers s ON i.supplier_id = s.id
        ORDER BY i.created_at DESC
    ''')
    rows = cur.fetchall()
    invoices = [dict_factory(cur, row) for row in rows]
    cur.close()
    conn.close()
    return invoices

def get_settings():
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute('SELECT name FROM suppliers ORDER BY name')
    suppliers = [r[0] for r in cur.fetchall()]
    
    cur.execute('SELECT name FROM buyers ORDER BY name')
    buyers = [r[0] for r in cur.fetchall()]
    
    cur.execute('SELECT name FROM payment_methods ORDER BY name')
    payment_methods = [r[0] for r in cur.fetchall()]
    
    cur.close()
    conn.close()
    
    return {
        'suppliers': suppliers,
        'buyers': buyers,
        'payment_methods': payment_methods
    }

def add_supplier(name):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute('INSERT INTO suppliers (name) VALUES (%s)', (name,))
        conn.commit()
    except:
        conn.rollback()
    cur.close()
    conn.close()

def add_buyer(name):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute('INSERT INTO buyers (name) VALUES (%s)', (name,))
        conn.commit()
    except:
        conn.rollback()
    cur.close()
    conn.close()

def add_payment_method(name):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute('INSERT INTO payment_methods (name) VALUES (%s)', (name,))
        conn.commit()
    except:
        conn.rollback()
    cur.close()
    conn.close()

def delete_supplier(name):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('DELETE FROM suppliers WHERE name = %s', (name,))
    conn.commit()
    cur.close()
    conn.close()

def delete_buyer(name):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('DELETE FROM buyers WHERE name = %s', (name,))
    conn.commit()
    cur.close()
    conn.close()

def delete_payment_method(name):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('DELETE FROM payment_methods WHERE name = %s', (name,))
    conn.commit()
    cur.close()
    conn.close()

def get_dashboard_metrics():
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute('''
        SELECT 
            COALESCE(SUM(total_revenue), 0) as total_revenue, 
            COALESCE(SUM(total_margin), 0) as total_margin, 
            COALESCE(SUM(quantity_mwh), 0) as total_quantity, 
            COALESCE(SUM(purchase_cost), 0) as total_purchase_cost 
        FROM sales
    ''')
    sales_metrics = dict_factory(cur, cur.fetchone())
    
    cur.execute('''
        SELECT 
            sup.name,
            COALESCE(SUM(s.purchase_cost), 0) as purchase_cost
        FROM sales s
        LEFT JOIN suppliers sup ON s.supplier_id = sup.id
        GROUP BY sup.name
    ''')
    supplier_costs = {r[0] if r[0] else 'Unknown': float(r[1]) for r in cur.fetchall()}
    
    gpe_purchase_cost = supplier_costs.get('GPE', 0)
    keler_purchase_cost = supplier_costs.get('Keler', 0)
    
    cur.execute('SELECT COALESCE(SUM(amount_eur), 0) as total_received FROM payments_received')
    payments_received = float(cur.fetchone()[0])
    
    cur.execute('SELECT COALESCE(SUM(amount_sent_eur), 0) as total_sent, COALESCE(SUM(amount_received_eur), 0) as total_supplier_received FROM supplier_payments')
    supplier_metrics = dict_factory(cur, cur.fetchone())
    
    cur.execute('SELECT COALESCE(SUM(amount), 0) as total_allocated FROM payment_allocations')
    total_allocated = float(cur.fetchone()[0])
    
    outstanding = float(sales_metrics['total_revenue']) - float(total_allocated) - keler_purchase_cost
    supplier_balance = float(supplier_metrics['total_supplier_received']) - gpe_purchase_cost
    
    cur.close()
    conn.close()
    
    return {
        'total_revenue': float(sales_metrics['total_revenue']),
        'total_margin': float(sales_metrics['total_margin']),
        'total_quantity': float(sales_metrics['total_quantity']),
        'total_purchase_cost': float(sales_metrics['total_purchase_cost']),
        'gpe_purchase_cost': gpe_purchase_cost,
        'keler_purchase_cost': keler_purchase_cost,
        'supplier_costs': supplier_costs,
        'payments_received': float(payments_received),
        'total_sent_to_suppliers': float(supplier_metrics['total_sent']),
        'total_received_by_suppliers': float(supplier_metrics['total_supplier_received']),
        'supplier_balance': supplier_balance,
        'outstanding_receivables': outstanding,
        'total_allocated': float(total_allocated)
    }
