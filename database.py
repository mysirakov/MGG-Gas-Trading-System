import os
import json
import pg8000
from datetime import datetime
from dotenv import load_dotenv
import streamlit as st
from urllib.parse import urlparse

load_dotenv()

DATABASE_URL = os.environ.get('DATABASE_URL')

def get_db_connection():
    url = urlparse(DATABASE_URL)
    return pg8000.connect(
        user=url.username,
        password=url.password,
        host=url.hostname,
        port=url.port or 5432,
        database=url.path[1:]
    )

class DictCursor:
    def __init__(self, conn):
        self.cur = conn.cursor()
    
    def execute(self, sql, params=None):
        self.cur.execute(sql, params or ())
    
    def fetchone(self):
        row = self.cur.fetchone()
        if not row:
            return None
        return dict(zip([d[0] for d in self.cur.description], row))
    
    def fetchall(self):
        rows = self.cur.fetchall()
        if not rows:
            return []
        cols = [d[0] for d in self.cur.description]
        return [dict(zip(cols, row)) for row in rows]
    
    def close(self):
        self.cur.close()

    def __getattr__(self, name):
        return getattr(self.cur, name)

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
    if not date_str or str(date_str).lower() == 'nan':
        return None
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
        return result[0] if isinstance(result, tuple) else result['id']
    cur.execute('INSERT INTO suppliers (name) VALUES (%s) RETURNING id', (name,))
    result = cur.fetchone()
    return result[0] if isinstance(result, tuple) else result['id']

def get_or_create_buyer(cur, name):
    if not name:
        return None
    cur.execute('SELECT id FROM buyers WHERE name = %s', (name,))
    result = cur.fetchone()
    if result:
        return result[0] if isinstance(result, tuple) else result['id']
    cur.execute('INSERT INTO buyers (name) VALUES (%s) RETURNING id', (name,))
    result = cur.fetchone()
    return result[0] if isinstance(result, tuple) else result['id']

def get_or_create_payment_method(cur, name):
    if not name:
        return None
    cur.execute('SELECT id FROM payment_methods WHERE name = %s', (name,))
    result = cur.fetchone()
    if result:
        return result[0] if isinstance(result, tuple) else result['id']
    cur.execute('INSERT INTO payment_methods (name) VALUES (%s) RETURNING id', (name,))
    result = cur.fetchone()
    return result[0] if isinstance(result, tuple) else result['id']

def get_or_create_invoice(cur, invoice_number, supplier_id, total_amount):
    if not invoice_number:
        return None
    cur.execute('SELECT id FROM invoices WHERE invoice_number = %s', (invoice_number,))
    result = cur.fetchone()
    if result:
        return result[0] if isinstance(result, tuple) else result['id']
    cur.execute('''
        INSERT INTO invoices (invoice_number, supplier_id, total_amount) 
        VALUES (%s, %s, %s) RETURNING id
    ''', (invoice_number, supplier_id, total_amount or 0))
    result = cur.fetchone()
    return result[0] if isinstance(result, tuple) else result['id']

def migrate_json_to_postgres():
    conn = get_db_connection()
    cur = DictCursor(conn)
    
    cur.execute('SELECT COUNT(*) FROM sales')
    result = cur.fetchone()
    if result and result['count'] > 0:
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
        result = cur.fetchone()
        if result:
            new_id = result['id']
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
        if notes == 'nan':
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
        result = cur.fetchone()
        if result:
            new_payment_id = result['id']
            for alloc in payment.get('allocations', []):
                old_sale_id = alloc.get('sale_id')
                new_sale_id = old_to_new_sale_ids.get(old_sale_id)
                if new_sale_id:
                    cur.execute('''
                        INSERT INTO payment_allocations (payment_id, sale_id, amount)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (payment_id, sale_id) DO UPDATE SET amount = payment_allocations.amount + EXCLUDED.amount
                    ''', (new_payment_id, new_sale_id, alloc.get('amount', 0)))
    
    conn.commit()
    cur.close()
    conn.close()
    return "Migration complete"

@st.cache_data
def get_sales():
    conn = get_db_connection()
    cur = DictCursor(conn)
    cur.execute('''
        SELECT s.*, b.name as buyer, sup.name as supplier,
            COALESCE((SELECT SUM(amount) FROM payment_allocations WHERE sale_id = s.id), 0) as amount_paid
        FROM sales s
        LEFT JOIN buyers b ON s.buyer_id = b.id
        LEFT JOIN suppliers sup ON s.supplier_id = sup.id
        ORDER BY s.contract_date DESC
    ''')
    sales = cur.fetchall()
    cur.close()
    conn.close()
    return [dict(s) for s in sales]

def clear_db_cache():
    st.cache_data.clear()

def add_sale(contract_date, buyer_name, quantity_mwh, sales_price, purchase_price, capacity_cost, transport_cost, supplier_name=None, customs_cost=0):
    conn = get_db_connection()
    cur = DictCursor(conn)
    buyer_id = get_or_create_buyer(cur, buyer_name)
    supplier_id = get_or_create_supplier(cur, supplier_name) if supplier_name else None
    cur.execute('''
        INSERT INTO sales (
            contract_date, buyer_id, quantity_mwh, sales_price_eur_mwh,
            purchase_price_eur_mwh, cost_capacity_eur_mwh, cost_transport_eur_mwh, supplier_id, cost_customs_eur_mwh
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
    ''', (contract_date, buyer_id, quantity_mwh, sales_price, purchase_price, capacity_cost, transport_cost, supplier_id, customs_cost))
    result = cur.fetchone()
    sale_id = result['id'] if result else None
    conn.commit()
    cur.close()
    conn.close()
    clear_db_cache()
    return sale_id

def update_sale(sale_id, contract_date, buyer_name, quantity_mwh, sales_price, purchase_price, capacity_cost, transport_cost, supplier_name=None, customs_cost=0):
    conn = get_db_connection()
    cur = DictCursor(conn)
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
    clear_db_cache()

def delete_sale(sale_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('DELETE FROM sales WHERE id = %s', (sale_id,))
    conn.commit()
    cur.close()
    conn.close()
    clear_db_cache()

@st.cache_data
def get_payments_received():
    conn = get_db_connection()
    cur = DictCursor(conn)
    cur.execute('''
        SELECT p.*, b.name as buyer,
            COALESCE((SELECT SUM(amount) FROM payment_allocations WHERE payment_id = p.id), 0) as allocated_amount
        FROM payments_received p
        LEFT JOIN buyers b ON p.buyer_id = b.id
        ORDER BY p.payment_date DESC
    ''')
    payments = cur.fetchall()
    cur.close()
    conn.close()
    return [dict(p) for p in payments]

@st.cache_data
def get_payment_allocations(payment_id):
    conn = get_db_connection()
    cur = DictCursor(conn)
    cur.execute('''
        SELECT pa.*, s.contract_date, s.total_revenue
        FROM payment_allocations pa
        JOIN sales s ON pa.sale_id = s.id
        WHERE pa.payment_id = %s
    ''', (payment_id,))
    allocations = cur.fetchall()
    cur.close()
    conn.close()
    return [dict(a) for a in allocations]

@st.cache_data
def get_unpaid_sales(buyer_name=None):
    conn = get_db_connection()
    cur = DictCursor(conn)
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
    sales = cur.fetchall()
    cur.close()
    conn.close()
    return [dict(s) for s in sales]

def add_payment_received(payment_date, buyer_name, amount_eur, notes=''):
    conn = get_db_connection()
    cur = DictCursor(conn)
    buyer_id = get_or_create_buyer(cur, buyer_name)
    
    cur.execute('''
        INSERT INTO payments_received (payment_date, buyer_id, amount_eur, notes)
        VALUES (%s, %s, %s, %s) RETURNING id
    ''', (payment_date, buyer_id, amount_eur, notes))
    result = cur.fetchone()
    if not result:
        conn.close()
        return None
    payment_id = result['id']
    
    cur.execute('''
        SELECT s.id, s.total_revenue,
            s.total_revenue - COALESCE((SELECT SUM(amount) FROM payment_allocations WHERE sale_id = s.id), 0) as outstanding
        FROM sales s
        LEFT JOIN buyers b ON s.buyer_id = b.id
        WHERE b.name = %s
        AND s.total_revenue > COALESCE((SELECT SUM(amount) FROM payment_allocations WHERE sale_id = s.id), 0)
        ORDER BY s.contract_date ASC
    ''', (buyer_name,))
    unpaid_sales = cur.fetchall()
    
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
    clear_db_cache()
    return payment_id

def delete_payment(payment_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('DELETE FROM payments_received WHERE id = %s', (payment_id,))
    conn.commit()
    cur.close()
    conn.close()
    clear_db_cache()

@st.cache_data
def get_supplier_payments():
    conn = get_db_connection()
    cur = DictCursor(conn)
    cur.execute('''
        SELECT sp.*, s.name as supplier, pm.name as payment_method, i.invoice_number
        FROM supplier_payments sp
        LEFT JOIN suppliers s ON sp.supplier_id = s.id
        LEFT JOIN payment_methods pm ON sp.payment_method_id = pm.id
        LEFT JOIN invoices i ON sp.invoice_id = i.id
        ORDER BY sp.payment_date DESC
    ''')
    payments = cur.fetchall()
    cur.close()
    conn.close()
    return [dict(p) for p in payments]

def add_supplier_payment(payment_date, supplier_name, payment_method_name, amount_sent, invoice_number, receipt_date=None, amount_received=None):
    conn = get_db_connection()
    cur = DictCursor(conn)
    supplier_id = get_or_create_supplier(cur, supplier_name)
    payment_method_id = get_or_create_payment_method(cur, payment_method_name)
    invoice_id = get_or_create_invoice(cur, invoice_number, supplier_id, amount_sent) if invoice_number else None
    
    cur.execute('''
        INSERT INTO supplier_payments (
            payment_date, supplier_id, payment_method_id, amount_sent_eur,
            invoice_id, receipt_date, amount_received_eur
        ) VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id
    ''', (payment_date, supplier_id, payment_method_id, amount_sent, invoice_id, receipt_date, amount_received))
    result = cur.fetchone()
    payment_id = result['id'] if result else None
    conn.commit()
    cur.close()
    conn.close()
    clear_db_cache()
    return payment_id

def delete_supplier_payment(payment_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('DELETE FROM supplier_payments WHERE id = %s', (payment_id,))
    conn.commit()
    cur.close()
    conn.close()
    clear_db_cache()

@st.cache_data
def get_invoices():
    conn = get_db_connection()
    cur = DictCursor(conn)
    cur.execute('''
        SELECT i.*, s.name as supplier,
            COALESCE((SELECT SUM(amount_sent_eur) FROM supplier_payments WHERE invoice_id = i.id), 0) as paid_amount
        FROM invoices i
        LEFT JOIN suppliers s ON i.supplier_id = s.id
        ORDER BY i.created_at DESC
    ''')
    invoices = cur.fetchall()
    cur.close()
    conn.close()
    return [dict(i) for i in invoices]

@st.cache_data
def get_settings():
    conn = get_db_connection()
    cur = DictCursor(conn)
    
    cur.execute('SELECT name FROM suppliers ORDER BY name')
    suppliers = [r['name'] for r in cur.fetchall()]
    
    cur.execute('SELECT name FROM buyers ORDER BY name')
    buyers = [r['name'] for r in cur.fetchall()]
    
    cur.execute('SELECT name FROM payment_methods ORDER BY name')
    payment_methods = [r['name'] for r in cur.fetchall()]
    
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
        clear_db_cache()
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
        clear_db_cache()
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
        clear_db_cache()
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
    clear_db_cache()

def delete_buyer(name):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('DELETE FROM buyers WHERE name = %s', (name,))
    conn.commit()
    cur.close()
    conn.close()
    clear_db_cache()

def delete_payment_method(name):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('DELETE FROM payment_methods WHERE name = %s', (name,))
    conn.commit()
    cur.close()
    conn.close()
    clear_db_cache()

def sales_to_df(sales=None):
    if sales is None:
        sales = get_sales()
    if not sales:
        return []
    
    numeric_cols = ['quantity_mwh', 'sales_price_eur_mwh', 'purchase_price_eur_mwh', 
                   'cost_capacity_eur_mwh', 'cost_transport_eur_mwh', 'cost_customs_eur_mwh', 'margin_eur_mwh',
                   'total_revenue', 'total_margin', 'purchase_cost', 'amount_paid']
    
    for row in sales:
        for col in numeric_cols:
            if col in row:
                try:
                    val = row[col]
                    if val is None or str(val).lower() == 'nan':
                        row[col] = 0.0
                    else:
                        row[col] = float(val)
                except (ValueError, TypeError):
                    row[col] = 0.0
    return sales

def payments_to_df(payments=None):
    if payments is None:
        payments = get_payments_received()
    if not payments:
        return []
    
    for row in payments:
        if 'amount_eur' in row:
            try:
                row['amount_eur'] = float(row['amount_eur']) if row['amount_eur'] is not None else 0.0
            except:
                row['amount_eur'] = 0.0
        if 'allocated_amount' in row:
            try:
                row['allocated_amount'] = float(row['allocated_amount']) if row['allocated_amount'] is not None else 0.0
            except:
                row['allocated_amount'] = 0.0
    return payments

def supplier_payments_to_df(payments=None):
    if payments is None:
        payments = get_supplier_payments()
    if not payments:
        return []
    
    numeric_cols = ['amount_sent_eur', 'amount_received_eur']
    for row in payments:
        for col in numeric_cols:
            if col in row:
                try:
                    val = row[col]
                    if val is None or str(val).lower() == 'nan':
                        row[col] = 0.0
                    else:
                        row[col] = float(val)
                except (ValueError, TypeError):
                    row[col] = 0.0
    return payments

@st.cache_data
def get_dashboard_metrics():
    conn = get_db_connection()
    cur = DictCursor(conn)
    
    cur.execute('''
        SELECT 
            COALESCE(SUM(total_revenue), 0) as total_revenue, 
            COALESCE(SUM(total_margin), 0) as total_margin, 
            COALESCE(SUM(quantity_mwh), 0) as total_quantity, 
            COALESCE(SUM(purchase_cost), 0) as total_purchase_cost 
        FROM sales
    ''')
    sales_metrics = cur.fetchone()
    
    cur.execute('''
        SELECT 
            sup.name,
            COALESCE(SUM(s.purchase_cost), 0) as purchase_cost
        FROM sales s
        LEFT JOIN suppliers sup ON s.supplier_id = sup.id
        GROUP BY sup.name
    ''')
    supplier_costs = {r['name'] if r['name'] else 'Unknown': float(r['purchase_cost']) for r in cur.fetchall()}
    
    gpe_purchase_cost = supplier_costs.get('GPE', 0)
    keler_purchase_cost = supplier_costs.get('Keler', 0)
    
    cur.execute('SELECT COALESCE(SUM(amount_eur), 0) as total_received FROM payments_received')
    result = cur.fetchone()
    payments_received = result['total_received'] if result else 0
    
    cur.execute('SELECT COALESCE(SUM(amount_sent_eur), 0) as total_sent, COALESCE(SUM(amount_received_eur), 0) as total_supplier_received FROM supplier_payments')
    supplier_metrics = cur.fetchone()
    
    cur.execute('SELECT COALESCE(SUM(amount), 0) as total_allocated FROM payment_allocations')
    result = cur.fetchone()
    total_allocated = result['total_allocated'] if result else 0
    
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

def load_purchases():
    return get_supplier_payments()

def load_sales():
    return get_sales()

def load_payments_received():
    return get_payments_received()

def load_settings():
    return get_settings()

def purchases_to_df(purchases=None):
    return supplier_payments_to_df(purchases)
