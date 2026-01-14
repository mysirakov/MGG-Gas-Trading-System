import os
import json
import pg8000
from datetime import datetime
from decimal import Decimal
from dotenv import load_dotenv
import streamlit as st
from urllib.parse import urlparse

load_dotenv()

DATABASE_URL = os.environ.get('DATABASE_URL')

def get_db_connection():
    """Create a new database connection with pg8000."""
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

def sanitize_data(data):
    """Convert Decimal and other non-JSON serializable types to float/string."""
    if isinstance(data, list):
        return [sanitize_data(i) for i in data]
    if isinstance(data, dict):
        return {k: sanitize_data(v) for k, v in data.items()}
    if isinstance(data, Decimal):
        return float(data)
    if isinstance(data, datetime):
        return data.isoformat()
    return data

def initialize_database_system():
    if 'db_initialized' not in st.session_state:
        try:
            init_database()
            migrate_json_to_postgres()
            st.session_state.db_initialized = True
        except Exception as e:
            st.error(f"Failed to initialize database: {e}")
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
    if isinstance(date_str, (datetime, datetime.date)):
        return date_str
    if isinstance(date_str, str):
        for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y']:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue
    return None

def get_or_create_supplier(cur, name):
    if not name: return None
    cur.execute('SELECT id FROM suppliers WHERE name = %s', (name,))
    result = cur.fetchone()
    if result: return result[0] if isinstance(result, tuple) else result['id']
    cur.execute('INSERT INTO suppliers (name) VALUES (%s) RETURNING id', (name,))
    result = cur.fetchone()
    return result[0] if isinstance(result, tuple) else result['id']

def get_or_create_buyer(cur, name):
    if not name: return None
    cur.execute('SELECT id FROM buyers WHERE name = %s', (name,))
    result = cur.fetchone()
    if result: return result[0] if isinstance(result, tuple) else result['id']
    cur.execute('INSERT INTO buyers (name) VALUES (%s) RETURNING id', (name,))
    result = cur.fetchone()
    return result[0] if isinstance(result, tuple) else result['id']

def get_or_create_payment_method(cur, name):
    if not name: return None
    cur.execute('SELECT id FROM payment_methods WHERE name = %s', (name,))
    result = cur.fetchone()
    if result: return result[0] if isinstance(result, tuple) else result['id']
    cur.execute('INSERT INTO payment_methods (name) VALUES (%s) RETURNING id', (name,))
    result = cur.fetchone()
    return result[0] if isinstance(result, tuple) else result['id']

def get_or_create_invoice(cur, invoice_number, supplier_id, total_amount):
    if not invoice_number: return None
    cur.execute('SELECT id FROM invoices WHERE invoice_number = %s', (invoice_number,))
    result = cur.fetchone()
    if result: return result[0] if isinstance(result, tuple) else result['id']
    cur.execute('INSERT INTO invoices (invoice_number, supplier_id, total_amount) VALUES (%s, %s, %s) RETURNING id', (invoice_number, supplier_id, total_amount or 0))
    result = cur.fetchone()
    return result[0] if isinstance(result, tuple) else result['id']

def migrate_json_to_postgres():
    conn = get_db_connection()
    cur = DictCursor(conn)
    cur.execute('SELECT COUNT(*) FROM sales')
    if cur.fetchone()['count'] > 0:
        cur.close(); conn.close()
        return
    
    try:
        with open('data/settings.json', 'r') as f: settings = json.load(f)
    except: settings = {}
    
    for s in settings.get('suppliers', []): get_or_create_supplier(cur, s)
    for b in settings.get('buyers', []): get_or_create_buyer(cur, b)
    for m in settings.get('payment_methods', []): get_or_create_payment_method(cur, m)
    
    old_to_new_sale_ids = {}
    try:
        with open('data/sales.json', 'r') as f: sales = json.load(f)
    except: sales = []
    
    for sale in sales:
        b_id = get_or_create_buyer(cur, sale.get('buyer'))
        s_id = get_or_create_supplier(cur, sale.get('supplier', 'GPE'))
        cur.execute('''
            INSERT INTO sales (contract_date, buyer_id, supplier_id, quantity_mwh, sales_price_eur_mwh,
            purchase_price_eur_mwh, cost_capacity_eur_mwh, cost_transport_eur_mwh, cost_customs_eur_mwh, old_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
        ''', (parse_date(sale.get('contract_date')), b_id, s_id, sale.get('quantity_mwh', 0), sale.get('sales_price_eur_mwh', 0),
              sale.get('purchase_price_eur_mwh', 0), sale.get('cost_capacity_eur_mwh', 0), sale.get('cost_transport_eur_mwh', 0),
              sale.get('cost_customs_eur_mwh', 0), sale.get('id')))
        res = cur.fetchone()
        if res: old_to_new_sale_ids[sale.get('id')] = res['id']
    
    try:
        with open('data/purchases.json', 'r') as f: purchases = json.load(f)
    except: purchases = []
    for p in purchases:
        s_id = get_or_create_supplier(cur, p.get('supplier'))
        pm_id = get_or_create_payment_method(cur, p.get('payment_method'))
        inv_id = get_or_create_invoice(cur, p.get('invoice_number'), s_id, p.get('amount_sent_eur'))
        cur.execute('''
            INSERT INTO supplier_payments (payment_date, supplier_id, payment_method_id, amount_sent_eur,
            invoice_id, receipt_date, amount_received_eur, old_id) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ''', (parse_date(p.get('payment_date')), s_id, pm_id, p.get('amount_sent_eur', 0), inv_id, 
              parse_date(p.get('receipt_date')), p.get('amount_received_eur', 0), p.get('id')))
    
    try:
        with open('data/payments_received.json', 'r') as f: payments = json.load(f)
    except: payments = []
    for pay in payments:
        b_id = get_or_create_buyer(cur, pay.get('buyer'))
        cur.execute('INSERT INTO payments_received (payment_date, buyer_id, amount_eur, notes, old_id) VALUES (%s, %s, %s, %s, %s) RETURNING id',
                    (parse_date(pay.get('payment_date')), b_id, pay.get('amount_eur', 0), pay.get('notes', ''), pay.get('id')))
        res = cur.fetchone()
        if res:
            p_id = res['id']
            for alloc in pay.get('allocations', []):
                s_id = old_to_new_sale_ids.get(alloc.get('sale_id'))
                if s_id:
                    cur.execute('INSERT INTO payment_allocations (payment_id, sale_id, amount) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING',
                                (p_id, s_id, alloc.get('amount', 0)))
    
    conn.commit(); cur.close(); conn.close()

def clear_db_cache():
    st.cache_data.clear()

@st.cache_data(show_spinner=False)
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
    res = cur.fetchall()
    cur.close(); conn.close()
    return sanitize_data(res)

@st.cache_data(show_spinner=False)
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
    res = cur.fetchall()
    cur.close(); conn.close()
    return sanitize_data(res)

@st.cache_data(show_spinner=False)
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
    res = cur.fetchall()
    cur.close(); conn.close()
    return sanitize_data(res)

@st.cache_data(show_spinner=False)
def get_dashboard_metrics():
    conn = get_db_connection()
    cur = DictCursor(conn)
    
    cur.execute('SELECT COALESCE(SUM(total_revenue), 0) as r, COALESCE(SUM(total_margin), 0) as m, COALESCE(SUM(quantity_mwh), 0) as q, COALESCE(SUM(purchase_cost), 0) as p FROM sales')
    s_m = cur.fetchone()
    
    cur.execute('SELECT sup.name, COALESCE(SUM(s.purchase_cost), 0) as c FROM sales s LEFT JOIN suppliers sup ON s.supplier_id = sup.id GROUP BY sup.name')
    s_c = {r['name'] if r['name'] else 'Unknown': float(r['c']) for r in cur.fetchall()}
    
    cur.execute('SELECT COALESCE(SUM(amount_eur), 0) as t FROM payments_received')
    p_r = cur.fetchone()['t']
    
    cur.execute('SELECT COALESCE(SUM(amount_sent_eur), 0) as s, COALESCE(SUM(amount_received_eur), 0) as r FROM supplier_payments')
    sup_m = cur.fetchone()
    
    cur.execute('SELECT COALESCE(SUM(amount), 0) as a FROM payment_allocations')
    t_a = cur.fetchone()['a']
    
    g_c = s_c.get('GPE', 0); k_c = s_c.get('Keler', 0)
    out = float(s_m['r']) - float(t_a) - k_c
    bal = float(sup_m['r']) - g_c
    
    cur.close(); conn.close()
    return sanitize_data({
        'total_revenue': s_m['r'], 'total_margin': s_m['m'], 'total_quantity': s_m['q'], 'total_purchase_cost': s_m['p'],
        'gpe_purchase_cost': g_c, 'keler_purchase_cost': k_c, 'supplier_costs': s_c, 'payments_received': p_r,
        'total_sent_to_suppliers': sup_m['s'], 'total_received_by_suppliers': sup_m['r'], 'supplier_balance': bal,
        'outstanding_receivables': out, 'total_allocated': t_a
    })

@st.cache_data(show_spinner=False)
def get_settings():
    conn = get_db_connection()
    cur = DictCursor(conn)
    cur.execute('SELECT name FROM suppliers ORDER BY name'); sups = [r['name'] for r in cur.fetchall()]
    cur.execute('SELECT name FROM buyers ORDER BY name'); buys = [r['name'] for r in cur.fetchall()]
    cur.execute('SELECT name FROM payment_methods ORDER BY name'); pms = [r['name'] for r in cur.fetchall()]
    cur.close(); conn.close()
    return {'suppliers': sups, 'buyers': buys, 'payment_methods': pms}

def add_sale(contract_date, buyer_name, quantity_mwh, sales_price, purchase_price, capacity_cost, transport_cost, supplier_name=None, customs_cost=0):
    conn = get_db_connection()
    cur = DictCursor(conn)
    b_id = get_or_create_buyer(cur, buyer_name)
    s_id = get_or_create_supplier(cur, supplier_name) if supplier_name else None
    cur.execute('''
        INSERT INTO sales (contract_date, buyer_id, quantity_mwh, sales_price_eur_mwh, purchase_price_eur_mwh,
        cost_capacity_eur_mwh, cost_transport_eur_mwh, supplier_id, cost_customs_eur_mwh)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
    ''', (contract_date, b_id, quantity_mwh, sales_price, purchase_price, capacity_cost, transport_cost, s_id, customs_cost))
    res = cur.fetchone(); s_id = res['id'] if res else None
    conn.commit(); cur.close(); conn.close(); clear_db_cache()
    return s_id

def update_sale(sale_id, contract_date, buyer_name, quantity_mwh, sales_price, purchase_price, capacity_cost, transport_cost, supplier_name=None, customs_cost=0):
    conn = get_db_connection()
    cur = DictCursor(conn)
    b_id = get_or_create_buyer(cur, buyer_name)
    s_id = get_or_create_supplier(cur, supplier_name) if supplier_name else None
    cur.execute('''
        UPDATE sales SET contract_date = %s, buyer_id = %s, quantity_mwh = %s, sales_price_eur_mwh = %s,
        purchase_price_eur_mwh = %s, cost_capacity_eur_mwh = %s, cost_transport_eur_mwh = %s, supplier_id = %s, cost_customs_eur_mwh = %s
        WHERE id = %s
    ''', (contract_date, b_id, quantity_mwh, sales_price, purchase_price, capacity_cost, transport_cost, s_id, customs_cost, sale_id))
    conn.commit(); cur.close(); conn.close(); clear_db_cache()

def delete_sale(sale_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('DELETE FROM sales WHERE id = %s', (sale_id,))
    conn.commit(); cur.close(); conn.close(); clear_db_cache()

def add_payment_received(payment_date, buyer_name, amount_eur, notes=''):
    conn = get_db_connection()
    cur = DictCursor(conn)
    b_id = get_or_create_buyer(cur, buyer_name)
    cur.execute('INSERT INTO payments_received (payment_date, buyer_id, amount_eur, notes) VALUES (%s, %s, %s, %s) RETURNING id',
                (payment_date, b_id, amount_eur, notes))
    res = cur.fetchone()
    if not res: conn.close(); return None
    p_id = res['id']
    cur.execute('''
        SELECT s.id, s.total_revenue - COALESCE((SELECT SUM(amount) FROM payment_allocations WHERE sale_id = s.id), 0) as out
        FROM sales s JOIN buyers b ON s.buyer_id = b.id
        WHERE b.name = %s AND s.total_revenue > COALESCE((SELECT SUM(amount) FROM payment_allocations WHERE sale_id = s.id), 0)
        ORDER BY s.contract_date ASC
    ''', (buyer_name,))
    unpaid = cur.fetchall()
    rem = float(amount_eur)
    for s in unpaid:
        if rem <= 0: break
        alloc = min(rem, float(s['out']))
        if alloc > 0:
            cur.execute('INSERT INTO payment_allocations (payment_id, sale_id, amount) VALUES (%s, %s, %s)', (p_id, s['id'], alloc))
            rem -= alloc
    conn.commit(); cur.close(); conn.close(); clear_db_cache()
    return p_id

def delete_payment(payment_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('DELETE FROM payments_received WHERE id = %s', (payment_id,))
    conn.commit(); cur.close(); conn.close(); clear_db_cache()

def add_supplier_payment(payment_date, supplier_name, payment_method_name, amount_sent, invoice_number, receipt_date=None, amount_received=None):
    conn = get_db_connection()
    cur = DictCursor(conn)
    s_id = get_or_create_supplier(cur, supplier_name)
    pm_id = get_or_create_payment_method(cur, payment_method_name)
    inv_id = get_or_create_invoice(cur, invoice_number, s_id, amount_sent) if invoice_number else None
    cur.execute('''
        INSERT INTO supplier_payments (payment_date, supplier_id, payment_method_id, amount_sent_eur, invoice_id, receipt_date, amount_received_eur)
        VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id
    ''', (payment_date, s_id, pm_id, amount_sent, inv_id, receipt_date, amount_received))
    res = cur.fetchone(); p_id = res['id'] if res else None
    conn.commit(); cur.close(); conn.close(); clear_db_cache()
    return p_id

def delete_supplier_payment(payment_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('DELETE FROM supplier_payments WHERE id = %s', (payment_id,))
    conn.commit(); cur.close(); conn.close(); clear_db_cache()

def add_supplier(name):
    conn = get_db_connection(); cur = conn.cursor()
    try: cur.execute('INSERT INTO suppliers (name) VALUES (%s)', (name,)); conn.commit(); clear_db_cache()
    except: conn.rollback()
    cur.close(); conn.close()

def add_buyer(name):
    conn = get_db_connection(); cur = conn.cursor()
    try: cur.execute('INSERT INTO buyers (name) VALUES (%s)', (name,)); conn.commit(); clear_db_cache()
    except: conn.rollback()
    cur.close(); conn.close()

def add_payment_method(name):
    conn = get_db_connection(); cur = conn.cursor()
    try: cur.execute('INSERT INTO payment_methods (name) VALUES (%s)', (name,)); conn.commit(); clear_db_cache()
    except: conn.rollback()
    cur.close(); conn.close()

def delete_supplier(name):
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('DELETE FROM suppliers WHERE name = %s', (name,)); conn.commit(); cur.close(); conn.close(); clear_db_cache()

def delete_buyer(name):
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('DELETE FROM buyers WHERE name = %s', (name,)); conn.commit(); cur.close(); conn.close(); clear_db_cache()

def delete_payment_method(name):
    conn = get_db_connection(); cur = conn.cursor()
    cur.execute('DELETE FROM payment_methods WHERE name = %s', (name,)); conn.commit(); cur.close(); conn.close(); clear_db_cache()

# Compat layer
def sales_to_df(sales=None): return sales if sales is not None else get_sales()
def payments_to_df(payments=None): return payments if payments is not None else get_payments_received()
def supplier_payments_to_df(payments=None): return payments if payments is not None else get_supplier_payments()
def load_purchases(): return get_supplier_payments()
def load_sales(): return get_sales()
def load_payments_received(): return get_payments_received()
def load_settings(): return get_settings()
def purchases_to_df(p=None): return supplier_payments_to_df(p)
