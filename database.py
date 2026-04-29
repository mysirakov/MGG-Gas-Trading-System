import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, date
from decimal import Decimal
from math import isnan
from dotenv import load_dotenv
import streamlit as st
from urllib.parse import urlparse

load_dotenv()

DATABASE_URL = os.environ.get('DATABASE_URL')

def get_db_connection():
    """Create a new database connection with psycopg2."""
    url = urlparse(DATABASE_URL)
    return psycopg2.connect(
        user=url.username,
        password=url.password,
        host=url.hostname,
        port=url.port or 5432,
        database=url.path[1:]
    )

def sanitize_data(data):
    """Convert Decimal, date, and other non-JSON/Arrow types to float/string/int."""
    if data is None:
        return None
    if isinstance(data, list):
        return [sanitize_data(i) for i in data]
    if isinstance(data, dict):
        return {k: sanitize_data(v) for k, v in data.items()}
    if isinstance(data, Decimal):
        return float(data)
    if isinstance(data, (datetime, date)):
        return data.isoformat()
    if isinstance(data, float) and isnan(data):
        return 0.0
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
    if isinstance(date_str, (datetime, date)):
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
    if result: return result[0]
    cur.execute('INSERT INTO suppliers (name) VALUES (%s) RETURNING id', (name,))
    return cur.fetchone()[0]

def get_or_create_buyer(cur, name):
    if not name: return None
    cur.execute('SELECT id FROM buyers WHERE name = %s', (name,))
    result = cur.fetchone()
    if result: return result['id'] if isinstance(result, dict) else result[0]
    cur.execute('INSERT INTO buyers (name) VALUES (%s) RETURNING id', (name,))
    r = cur.fetchone()
    return r['id'] if isinstance(r, dict) else r[0]

def get_or_create_payment_method(cur, name):
    if not name: return None
    cur.execute('SELECT id FROM payment_methods WHERE name = %s', (name,))
    result = cur.fetchone()
    if result: return result[0]
    cur.execute('INSERT INTO payment_methods (name) VALUES (%s) RETURNING id', (name,))
    return cur.fetchone()[0]

def get_or_create_invoice(cur, invoice_number, supplier_id, total_amount):
    if not invoice_number: return None
    cur.execute('SELECT id FROM invoices WHERE invoice_number = %s', (invoice_number,))
    result = cur.fetchone()
    if result: return result['id'] if isinstance(result, dict) else result[0]
    cur.execute('INSERT INTO invoices (invoice_number, supplier_id, total_amount) VALUES (%s, %s, %s) RETURNING id', (invoice_number, supplier_id, total_amount or 0))
    r = cur.fetchone()
    return r['id'] if isinstance(r, dict) else r[0]

def migrate_json_to_postgres():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT COUNT(*) FROM sales')
    if cur.fetchone()[0] > 0:
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
        if res: old_to_new_sale_ids[sale.get('id')] = res[0]
    
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
            p_id = res[0]
            for alloc in pay.get('allocations', []):
                s_id = old_to_new_sale_ids.get(alloc.get('sale_id'))
                if s_id:
                    cur.execute('INSERT INTO payment_allocations (payment_id, sale_id, amount) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING',
                                (p_id, s_id, alloc.get('amount', 0)))
    
    conn.commit(); cur.close(); conn.close()

def clear_db_cache():
    st.cache_data.clear()

@st.cache_data(show_spinner=False, ttl=60)
def get_sales():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute('''
        SELECT s.*, b.name as buyer, sup.name as supplier,
            COALESCE((SELECT SUM(amount) FROM payment_allocations WHERE sale_id = s.id), 0) as amount_paid
        FROM sales s
        LEFT JOIN buyers b ON s.buyer_id = b.id
        LEFT JOIN suppliers sup ON s.supplier_id = sup.id
        ORDER BY s.contract_date DESC
    ''')
    res = [dict(r) for r in cur.fetchall()]
    cur.close(); conn.close()
    return sanitize_data(res)

@st.cache_data(show_spinner=False, ttl=60)
def get_payments_received():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute('''
        SELECT p.*, b.name as buyer,
            COALESCE((SELECT SUM(amount) FROM payment_allocations WHERE payment_id = p.id), 0) as allocated_amount
        FROM payments_received p
        LEFT JOIN buyers b ON p.buyer_id = b.id
        ORDER BY p.payment_date DESC
    ''')
    res = [dict(r) for r in cur.fetchall()]
    cur.close(); conn.close()
    return sanitize_data(res)

@st.cache_data(show_spinner=False, ttl=60)
def get_supplier_payments():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute('''
        SELECT sp.*, s.name as supplier, pm.name as payment_method, i.invoice_number
        FROM supplier_payments sp
        LEFT JOIN suppliers s ON sp.supplier_id = s.id
        LEFT JOIN payment_methods pm ON sp.payment_method_id = pm.id
        LEFT JOIN invoices i ON sp.invoice_id = i.id
        ORDER BY sp.payment_date DESC
    ''')
    res = [dict(r) for r in cur.fetchall()]
    cur.close(); conn.close()
    return sanitize_data(res)

@st.cache_data(show_spinner=False, ttl=60)
def get_dashboard_metrics():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # Single consolidated query for performance with unique aliases
    cur.execute('''
        WITH sales_agg AS (
            SELECT 
                COALESCE(SUM(total_revenue), 0) as rev, 
                COALESCE(SUM(total_margin), 0) as mar, 
                COALESCE(SUM(quantity_mwh), 0) as qty, 
                COALESCE(SUM(purchase_cost), 0) as pcost 
            FROM sales
        ),
        alloc_agg AS (
            SELECT COALESCE(SUM(amount), 0) as alloc FROM payment_allocations
        ),
        payments_agg AS (
            SELECT COALESCE(SUM(amount_eur), 0) as pay_rec FROM payments_received
        ),
        sup_payments_agg AS (
            SELECT 
                COALESCE(SUM(amount_sent_eur), 0) as sent, 
                COALESCE(SUM(amount_received_eur), 0) as rec 
            FROM supplier_payments
        ),
        sup_costs_agg AS (
            SELECT 
                COALESCE(SUM(CASE WHEN sup.name = 'GPE' THEN s.purchase_cost ELSE 0 END), 0) as gpe_c,
                COALESCE(SUM(CASE WHEN sup.name = 'Keler' THEN s.purchase_cost ELSE 0 END), 0) as keler_c
            FROM sales s 
            LEFT JOIN suppliers sup ON s.supplier_id = sup.id
        )
        SELECT * FROM sales_agg, alloc_agg, payments_agg, sup_payments_agg, sup_costs_agg
    ''')
    row = cur.fetchone()
    
    cur.execute('SELECT sup.name, COALESCE(SUM(s.purchase_cost), 0) as c FROM sales s LEFT JOIN suppliers sup ON s.supplier_id = sup.id GROUP BY sup.name')
    s_c = {r['name'] if r['name'] else 'Unknown': float(r['c']) for r in cur.fetchall()}
    
    cur.close(); conn.close()
    
    g_c = float(row['gpe_c'])
    k_c = float(row['keler_c'])
    out = float(row['rev']) - float(row['alloc']) - k_c
    bal = float(row['rec']) - g_c
    
    return sanitize_data({
        'total_revenue': row['rev'], 'total_margin': row['mar'], 'total_quantity': row['qty'], 'total_purchase_cost': row['pcost'],
        'gpe_purchase_cost': g_c, 'keler_purchase_cost': k_c, 'supplier_costs': s_c, 'payments_received': row['pay_rec'],
        'total_sent_to_suppliers': row['sent'], 'total_received_by_suppliers': row['rec'], 'supplier_balance': bal,
        'outstanding_receivables': out, 'total_allocated': row['alloc']
    })

@st.cache_data(show_spinner=False, ttl=60)
def get_settings():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute('SELECT name FROM suppliers ORDER BY name'); sups = [r['name'] for r in cur.fetchall()]
    cur.execute('SELECT name FROM buyers ORDER BY name'); buys = [r['name'] for r in cur.fetchall()]
    cur.execute('SELECT name FROM payment_methods ORDER BY name'); pms = [r['name'] for r in cur.fetchall()]
    cur.close(); conn.close()
    return {'suppliers': sups, 'buyers': buys, 'payment_methods': pms}

def update_settings(setting_type, action, value):
    conn = get_db_connection()
    cur = conn.cursor()
    table_map = {'suppliers': 'suppliers', 'buyers': 'buyers', 'payment_methods': 'payment_methods'}
    table = table_map.get(setting_type)
    if not table:
        cur.close(); conn.close()
        return False
    try:
        if action == 'add':
            cur.execute(f'INSERT INTO {table} (name) VALUES (%s) ON CONFLICT (name) DO NOTHING', (value,))
        elif action == 'delete':
            cur.execute(f'DELETE FROM {table} WHERE name = %s', (value,))
        conn.commit()
        get_settings.clear()
        cur.close(); conn.close()
        return True
    except Exception as e:
        conn.rollback()
        cur.close(); conn.close()
        return False

@st.cache_data(show_spinner=False, ttl=60)
def get_unpaid_sales(buyer_name=None):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    query = '''
        SELECT s.*, b.name as buyer,
            COALESCE((SELECT SUM(amount) FROM payment_allocations WHERE sale_id = s.id), 0) as amount_paid,
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
    res = [dict(r) for r in cur.fetchall()]
    cur.close(); conn.close()
    return sanitize_data(res)

@st.cache_data(show_spinner=False, ttl=60)
def get_invoices():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute('''
        SELECT i.*, s.name as supplier,
            COALESCE((SELECT SUM(amount_sent_eur) FROM supplier_payments WHERE invoice_id = i.id), 0) as paid_amount
        FROM invoices i
        LEFT JOIN suppliers s ON i.supplier_id = s.id
        ORDER BY i.created_at DESC
    ''')
    res = [dict(r) for r in cur.fetchall()]
    cur.close(); conn.close()
    return sanitize_data(res)

def _reconcile_buyer_allocations(cur, buyer_name):
    if not buyer_name: return
    cur.execute('SELECT id FROM buyers WHERE name = %s', (buyer_name,))
    row = cur.fetchone()
    if not row: return
    b_id = row['id'] if isinstance(row, dict) else row[0]

    cur.execute('DELETE FROM payment_allocations WHERE payment_id IN (SELECT id FROM payments_received WHERE buyer_id = %s)', (b_id,))

    cur.execute('SELECT id, amount_eur FROM payments_received WHERE buyer_id = %s ORDER BY payment_date ASC, id ASC', (b_id,))
    payments = [(r['id'] if isinstance(r, dict) else r[0], float(r['amount_eur'] if isinstance(r, dict) else r[1])) for r in cur.fetchall()]

    cur.execute('SELECT id, total_revenue FROM sales WHERE buyer_id = %s ORDER BY contract_date ASC, id ASC', (b_id,))
    sales = [(r['id'] if isinstance(r, dict) else r[0], float(r['total_revenue'] if isinstance(r, dict) else r[1] or 0)) for r in cur.fetchall()]

    sale_idx = 0
    sale_remaining = sales[0][1] if sales else 0.0
    for pid, p_amount in payments:
        rem = p_amount
        while rem > 0 and sale_idx < len(sales):
            if sale_remaining <= 0:
                sale_idx += 1
                if sale_idx < len(sales):
                    sale_remaining = sales[sale_idx][1]
                continue
            sid = sales[sale_idx][0]
            alloc = min(rem, sale_remaining)
            cur.execute('INSERT INTO payment_allocations (payment_id, sale_id, amount) VALUES (%s, %s, %s)', (pid, sid, alloc))
            rem -= alloc
            sale_remaining -= alloc

def add_sale(contract_date, buyer_name, quantity_mwh, sales_price, purchase_price, capacity_cost, transport_cost, supplier_name=None, customs_cost=0):
    conn = get_db_connection()
    cur = conn.cursor()
    b_id = get_or_create_buyer(cur, buyer_name)
    s_id = get_or_create_supplier(cur, supplier_name) if supplier_name else None
    cur.execute('''
        INSERT INTO sales (contract_date, buyer_id, quantity_mwh, sales_price_eur_mwh, purchase_price_eur_mwh,
        cost_capacity_eur_mwh, cost_transport_eur_mwh, supplier_id, cost_customs_eur_mwh)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
    ''', (contract_date, b_id, quantity_mwh, sales_price, purchase_price, capacity_cost, transport_cost, s_id, customs_cost))
    res = cur.fetchone()
    new_sale_id = res[0] if res else None
    _reconcile_buyer_allocations(cur, buyer_name)
    conn.commit(); cur.close(); conn.close(); clear_db_cache()
    return new_sale_id

def update_sale(sale_id, contract_date, buyer_name, quantity_mwh, sales_price, purchase_price, capacity_cost, transport_cost, supplier_name=None, customs_cost=0):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT b.name FROM sales s LEFT JOIN buyers b ON s.buyer_id = b.id WHERE s.id = %s', (sale_id,))
    row = cur.fetchone()
    old_buyer = row[0] if row else None

    b_id = get_or_create_buyer(cur, buyer_name)
    s_id = get_or_create_supplier(cur, supplier_name) if supplier_name else None
    cur.execute('''
        UPDATE sales SET contract_date = %s, buyer_id = %s, quantity_mwh = %s, sales_price_eur_mwh = %s,
        purchase_price_eur_mwh = %s, cost_capacity_eur_mwh = %s, cost_transport_eur_mwh = %s, supplier_id = %s, cost_customs_eur_mwh = %s
        WHERE id = %s
    ''', (contract_date, b_id, quantity_mwh, sales_price, purchase_price, capacity_cost, transport_cost, s_id, customs_cost, sale_id))

    if old_buyer and old_buyer != buyer_name:
        _reconcile_buyer_allocations(cur, old_buyer)
    _reconcile_buyer_allocations(cur, buyer_name)
    conn.commit(); cur.close(); conn.close(); clear_db_cache()

def delete_sale(sale_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT b.name FROM sales s LEFT JOIN buyers b ON s.buyer_id = b.id WHERE s.id = %s', (sale_id,))
    row = cur.fetchone()
    buyer_name = row[0] if row else None
    cur.execute('DELETE FROM sales WHERE id = %s', (sale_id,))
    if buyer_name:
        _reconcile_buyer_allocations(cur, buyer_name)
    conn.commit(); cur.close(); conn.close(); clear_db_cache()

def add_payment_received(payment_date, buyer_name, amount_eur, notes=''):
    conn = get_db_connection()
    cur = conn.cursor()
    b_id = get_or_create_buyer(cur, buyer_name)
    cur.execute('INSERT INTO payments_received (payment_date, buyer_id, amount_eur, notes) VALUES (%s, %s, %s, %s) RETURNING id',
                (payment_date, b_id, amount_eur, notes))
    res = cur.fetchone()
    if not res: cur.close(); conn.close(); return None
    p_id = res[0]
    _reconcile_buyer_allocations(cur, buyer_name)
    conn.commit(); cur.close(); conn.close(); clear_db_cache()
    return p_id

def update_payment_received(payment_id, payment_date, buyer_name, amount_eur, notes=''):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT b.name FROM payments_received p LEFT JOIN buyers b ON p.buyer_id = b.id WHERE p.id = %s', (payment_id,))
    row = cur.fetchone()
    old_buyer = row[0] if row else None

    b_id = get_or_create_buyer(cur, buyer_name)
    cur.execute('UPDATE payments_received SET payment_date = %s, buyer_id = %s, amount_eur = %s, notes = %s WHERE id = %s',
                (payment_date, b_id, amount_eur, notes, payment_id))

    if old_buyer and old_buyer != buyer_name:
        _reconcile_buyer_allocations(cur, old_buyer)
    _reconcile_buyer_allocations(cur, buyer_name)
    conn.commit(); cur.close(); conn.close(); clear_db_cache()

def delete_payment_received(payment_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT b.name FROM payments_received p LEFT JOIN buyers b ON p.buyer_id = b.id WHERE p.id = %s', (payment_id,))
    row = cur.fetchone()
    buyer_name = row[0] if row else None
    cur.execute('DELETE FROM payments_received WHERE id = %s', (payment_id,))
    if buyer_name:
        _reconcile_buyer_allocations(cur, buyer_name)
    conn.commit(); cur.close(); conn.close(); clear_db_cache()

def delete_payment(payment_id):
    delete_payment_received(payment_id)

def add_supplier_payment(payment_date, supplier_name, payment_method_name, amount_sent, invoice_number, receipt_date=None, amount_received=None):
    conn = get_db_connection()
    cur = conn.cursor()
    s_id = get_or_create_supplier(cur, supplier_name)
    pm_id = get_or_create_payment_method(cur, payment_method_name)
    inv_id = get_or_create_invoice(cur, invoice_number, s_id, amount_sent) if invoice_number else None
    cur.execute('''
        INSERT INTO supplier_payments (payment_date, supplier_id, payment_method_id, amount_sent_eur, invoice_id, receipt_date, amount_received_eur)
        VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id
    ''', (payment_date, s_id, pm_id, amount_sent, inv_id, receipt_date, amount_received))
    res = cur.fetchone(); p_id = res[0] if res else None
    conn.commit(); cur.close(); conn.close(); clear_db_cache()
    return p_id

def update_supplier_payment(payment_id, payment_date, supplier_name, payment_method_name, amount_sent, invoice_number, receipt_date=None, amount_received=None):
    conn = get_db_connection()
    cur = conn.cursor()
    s_id = get_or_create_supplier(cur, supplier_name)
    pm_id = get_or_create_payment_method(cur, payment_method_name)
    inv_id = get_or_create_invoice(cur, invoice_number, s_id, amount_sent) if invoice_number else None
    cur.execute('''
        UPDATE supplier_payments SET payment_date = %s, supplier_id = %s, payment_method_id = %s, amount_sent_eur = %s,
        invoice_id = %s, receipt_date = %s, amount_received_eur = %s WHERE id = %s
    ''', (payment_date, s_id, pm_id, amount_sent, inv_id, receipt_date, amount_received, payment_id))
    conn.commit(); cur.close(); conn.close(); clear_db_cache()

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

def get_filtered_statistics(date_from=None, date_to=None, buyers=None, suppliers=None):
    """Get statistics for filtered sales data with period comparison"""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    base_query = '''
        SELECT 
            COALESCE(SUM(s.total_margin), 0) as total_margin,
            COALESCE(SUM(s.total_revenue), 0) as total_revenue,
            COALESCE(SUM(s.quantity_mwh), 0) as total_quantity,
            COALESCE(SUM(s.purchase_cost), 0) as total_purchase_cost,
            COUNT(*) as trade_count,
            CASE WHEN SUM(s.quantity_mwh) > 0 
                THEN SUM(s.purchase_price_eur_mwh * s.quantity_mwh) / SUM(s.quantity_mwh) 
                ELSE 0 END as avg_buy_price,
            CASE WHEN SUM(s.quantity_mwh) > 0 
                THEN SUM(s.sales_price_eur_mwh * s.quantity_mwh) / SUM(s.quantity_mwh) 
                ELSE 0 END as avg_sell_price,
            CASE WHEN SUM(s.quantity_mwh) > 0 
                THEN SUM(s.total_margin) / SUM(s.quantity_mwh) 
                ELSE 0 END as margin_per_mwh,
            MAX(s.total_margin) as best_trade_margin,
            MAX(s.total_revenue) as largest_trade_revenue
        FROM sales s
        LEFT JOIN buyers b ON s.buyer_id = b.id
        LEFT JOIN suppliers sup ON s.supplier_id = sup.id
        WHERE 1=1
    '''
    
    params = []
    if date_from:
        base_query += ' AND s.contract_date >= %s'
        params.append(date_from)
    if date_to:
        base_query += ' AND s.contract_date <= %s'
        params.append(date_to)
    if buyers and len(buyers) > 0:
        base_query += ' AND b.name = ANY(%s)'
        params.append(buyers)
    if suppliers and len(suppliers) > 0:
        base_query += ' AND sup.name = ANY(%s)'
        params.append(suppliers)
    
    cur.execute(base_query, params)
    current = dict(cur.fetchone())
    
    current['avg_spread'] = float(current['avg_sell_price'] or 0) - float(current['avg_buy_price'] or 0)
    current['margin_pct'] = (float(current['total_margin'] or 0) / float(current['total_revenue']) * 100) if float(current['total_revenue'] or 0) > 0 else 0
    
    cur.close()
    conn.close()
    return sanitize_data(current)

def get_period_comparison_statistics(date_from, date_to, prev_date_from, prev_date_to, buyers=None, suppliers=None):
    """Get current and previous period statistics for comparison"""
    current = get_filtered_statistics(date_from, date_to, buyers, suppliers)
    previous = get_filtered_statistics(prev_date_from, prev_date_to, buyers, suppliers)
    
    def calc_delta(curr_val, prev_val):
        if prev_val and prev_val != 0:
            return ((curr_val - prev_val) / abs(prev_val)) * 100
        return 0 if curr_val == 0 else 100
    
    deltas = {
        'total_margin_delta': calc_delta(current['total_margin'], previous['total_margin']),
        'total_revenue_delta': calc_delta(current['total_revenue'], previous['total_revenue']),
        'total_quantity_delta': calc_delta(current['total_quantity'], previous['total_quantity']),
        'total_purchase_cost_delta': calc_delta(current['total_purchase_cost'], previous['total_purchase_cost']),
        'avg_buy_price_delta': calc_delta(current['avg_buy_price'], previous['avg_buy_price']),
        'avg_sell_price_delta': calc_delta(current['avg_sell_price'], previous['avg_sell_price']),
        'avg_spread_delta': calc_delta(current['avg_spread'], previous['avg_spread']),
        'margin_per_mwh_delta': calc_delta(current['margin_per_mwh'], previous['margin_per_mwh']),
        'margin_pct_delta': calc_delta(current['margin_pct'], previous['margin_pct']),
        'trade_count_delta': calc_delta(current['trade_count'], previous['trade_count']),
    }
    
    return {
        'current': current,
        'previous': previous,
        'deltas': deltas
    }
