
import os
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

DATABASE_URL = os.environ.get('DATABASE_URL')

def get_connection():
    return psycopg2.connect(DATABASE_URL)

def clean_date(date_str):
    if pd.isna(date_str) or not date_str:
        return None
    if isinstance(date_str, str):
        date_str = date_str.replace('"', '').replace("'", "")
        try:
            return pd.to_datetime(date_str).to_pydatetime()
        except:
            return None
    return date_str

def import_data():
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        # 1. Buyers
        print("Importing buyers...")
        buyers_df = pd.read_csv('temp_csv/buyers.csv')
        data = [(row['id'], row['name'], clean_date(row['created_at'])) for _, row in buyers_df.iterrows()]
        execute_values(cur, "INSERT INTO buyers (id, name, created_at) VALUES %s", data)
        
        # 2. Payment Methods
        print("Importing payment methods...")
        pm_df = pd.read_csv('temp_csv/payment_methods.csv')
        data = [(row['id'], row['name'], clean_date(row['created_at'])) for _, row in pm_df.iterrows()]
        execute_values(cur, "INSERT INTO payment_methods (id, name, created_at) VALUES %s", data)
            
        # 3. Suppliers
        print("Creating suppliers...")
        cur.execute("INSERT INTO suppliers (id, name) VALUES (1, 'GPE'), (2, 'Keler') ON CONFLICT DO NOTHING")
        
        # 4. Sales
        print("Importing sales...")
        sales_df = pd.read_csv('temp_csv/sales.csv')
        data = []
        for _, row in sales_df.iterrows():
            sid = row.get('supplier_id')
            if pd.isna(sid) or sid == '' or sid == ' ' or sid == 'nan':
                sid = 1
            data.append((
                row['id'], clean_date(row['contract_date']), row['buyer_id'], sid, 
                row['quantity_mwh'], row['sales_price_eur_mwh'], row['purchase_price_eur_mwh'],
                row['cost_capacity_eur_mwh'], row['cost_transport_eur_mwh'], row['cost_customs_eur_mwh'],
                row['old_id'], clean_date(row['created_at'])
            ))
        execute_values(cur, """
            INSERT INTO sales (
                id, contract_date, buyer_id, supplier_id, quantity_mwh, 
                sales_price_eur_mwh, purchase_price_eur_mwh, cost_capacity_eur_mwh, 
                cost_transport_eur_mwh, cost_customs_eur_mwh, old_id, created_at
            ) VALUES %s
        """, data)
            
        # 5. Invoices
        print("Importing invoices...")
        invoices_df = pd.read_csv('temp_csv/invoices.csv')
        data = [(row['id'], row['invoice_number'], row['supplier_id'], row['total_amount'], 
                 row['status'], clean_date(row['created_at']), row['old_id']) for _, row in invoices_df.iterrows()]
        execute_values(cur, "INSERT INTO invoices (id, invoice_number, supplier_id, total_amount, status, created_at, old_id) VALUES %s", data)
            
        # 6. Payments Received
        print("Importing payments received...")
        pr_df = pd.read_csv('temp_csv/payments_received.csv')
        data = [(row['id'], clean_date(row['payment_date']), row['buyer_id'], row['amount_eur'],
                 row['notes'] if not pd.isna(row['notes']) else '', clean_date(row['created_at']), row['old_id']) for _, row in pr_df.iterrows()]
        execute_values(cur, "INSERT INTO payments_received (id, payment_date, buyer_id, amount_eur, notes, created_at, old_id) VALUES %s", data)
            
        # 7. Payment Allocations
        print("Importing payment allocations...")
        pa_df = pd.read_csv('temp_csv/payment_allocations.csv')
        data = [(row['id'], row['payment_id'], row['sale_id'], row['amount'], clean_date(row['created_at'])) for _, row in pa_df.iterrows()]
        execute_values(cur, "INSERT INTO payment_allocations (id, payment_id, sale_id, amount, created_at) VALUES %s", data)
            
        # 8. Supplier Payments
        print("Importing supplier payments...")
        sp_df = pd.read_csv('temp_csv/supplier_payments.csv')
        data = []
        for _, row in sp_df.iterrows():
            data.append((
                row['id'], clean_date(row['payment_date']), row['supplier_id'], row['payment_method_id'],
                row['amount_sent_eur'], row['invoice_id'], clean_date(row['receipt_date']), 
                row['amount_received_eur'], row['notes'] if not pd.isna(row['notes']) else '',
                clean_date(row['created_at']), row['old_id']
            ))
        execute_values(cur, """
            INSERT INTO supplier_payments (
                id, payment_date, supplier_id, payment_method_id, amount_sent_eur,
                invoice_id, receipt_date, amount_received_eur, notes, created_at, old_id
            ) VALUES %s
        """, data)
            
        # Update sequences
        print("Updating sequences...")
        tables = ['buyers', 'payment_methods', 'suppliers', 'sales', 'invoices', 'payments_received', 'payment_allocations', 'supplier_payments']
        for table in tables:
            cur.execute(f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), (SELECT MAX(id) FROM {table}))")
            
        conn.commit()
        print("Import completed successfully!")
        
    except Exception as e:
        conn.rollback()
        print(f"Error during import: {e}")
        raise e
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    import_data()
