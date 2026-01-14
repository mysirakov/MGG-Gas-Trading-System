
import os
import csv
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

DATABASE_URL = os.environ.get('DATABASE_URL')

def get_connection():
    return psycopg2.connect(DATABASE_URL)

def clean_date(date_str):
    if not date_str or str(date_str).lower() == 'nan':
        return None
    if isinstance(date_str, str):
        date_str = date_str.replace('"', '').replace("'", "").strip()
        if not date_str:
            return None
        # Try multiple formats
        for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y']:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
    return date_str

def read_csv(file_path):
    with open(file_path, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        return list(reader)

def import_data():
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        # 1. Buyers
        print("Importing buyers...")
        buyers = read_csv('temp_csv/buyers.csv')
        data = [(row['id'], row['name'], clean_date(row['created_at'])) for row in buyers]
        execute_values(cur, "INSERT INTO buyers (id, name, created_at) VALUES %s", data)
        
        # 2. Payment Methods
        print("Importing payment methods...")
        payment_methods = read_csv('temp_csv/payment_methods.csv')
        data = [(row['id'], row['name'], clean_date(row['created_at'])) for row in payment_methods]
        execute_values(cur, "INSERT INTO payment_methods (id, name, created_at) VALUES %s", data)
            
        # 3. Suppliers
        print("Creating suppliers...")
        cur.execute("INSERT INTO suppliers (id, name) VALUES (1, 'GPE'), (2, 'Keler') ON CONFLICT DO NOTHING")
        
        # 4. Sales
        print("Importing sales...")
        sales = read_csv('temp_csv/sales.csv')
        data = []
        for row in sales:
            sid = row.get('supplier_id')
            if not sid or str(sid).lower() == 'nan' or str(sid).strip() == '':
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
        invoices = read_csv('temp_csv/invoices.csv')
        data = [(row['id'], row['invoice_number'], row['supplier_id'], row['total_amount'], 
                 row['status'], clean_date(row['created_at']), row['old_id']) for row in invoices]
        execute_values(cur, "INSERT INTO invoices (id, invoice_number, supplier_id, total_amount, status, created_at, old_id) VALUES %s", data)
            
        # 6. Payments Received
        print("Importing payments received...")
        payments_received = read_csv('temp_csv/payments_received.csv')
        data = [(row['id'], clean_date(row['payment_date']), row['buyer_id'], row['amount_eur'],
                 row['notes'] if row['notes'] and str(row['notes']).lower() != 'nan' else '', 
                 clean_date(row['created_at']), row['old_id']) for row in payments_received]
        execute_values(cur, "INSERT INTO payments_received (id, payment_date, buyer_id, amount_eur, notes, created_at, old_id) VALUES %s", data)
            
        # 7. Payment Allocations
        print("Importing payment allocations...")
        payment_allocations = read_csv('temp_csv/payment_allocations.csv')
        data = [(row['id'], row['payment_id'], row['sale_id'], row['amount'], clean_date(row['created_at'])) for row in payment_allocations]
        execute_values(cur, "INSERT INTO payment_allocations (id, payment_id, sale_id, amount, created_at) VALUES %s", data)
            
        # 8. Supplier Payments
        print("Importing supplier payments...")
        supplier_payments = read_csv('temp_csv/supplier_payments.csv')
        data = []
        for row in supplier_payments:
            data.append((
                row['id'], clean_date(row['payment_date']), row['supplier_id'], row['payment_method_id'],
                row['amount_sent_eur'], row['invoice_id'], clean_date(row['receipt_date']), 
                row['amount_received_eur'], row['notes'] if row['notes'] and str(row['notes']).lower() != 'nan' else '',
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
