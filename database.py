import json
import os
from datetime import datetime
import pandas as pd

DATA_DIR = "data"

def ensure_data_dir():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

def get_file_path(filename):
    return os.path.join(DATA_DIR, filename)

def load_json(filename, default=None):
    ensure_data_dir()
    filepath = get_file_path(filename)
    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            return json.load(f)
    return default if default is not None else []

def save_json(filename, data):
    ensure_data_dir()
    filepath = get_file_path(filename)
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2, default=str)

def load_purchases():
    return load_json("purchases.json", [])

def save_purchases(data):
    save_json("purchases.json", data)

def load_sales():
    return load_json("sales.json", [])

def save_sales(data):
    save_json("sales.json", data)

def load_payments_received():
    return load_json("payments_received.json", [])

def save_payments_received(data):
    save_json("payments_received.json", data)

def load_invoices():
    return load_json("invoices.json", [])

def save_invoices(data):
    save_json("invoices.json", data)

def load_settings():
    default_settings = {
        "suppliers": ["Default Supplier"],
        "payment_methods": ["Unicredit", "Financial Agent"],
        "buyers": ["Keler"],
        "gas_trading_names": ["Default Trading Name"]
    }
    return load_json("settings.json", default_settings)

def save_settings(data):
    save_json("settings.json", data)

def purchases_to_df(purchases):
    if not purchases:
        return pd.DataFrame(columns=[
            'id', 'payment_date', 'supplier', 'payment_method', 'amount_sent_eur',
            'invoice_number', 'receipt_date', 'amount_received_eur',
            'price_eur_mwh', 'quantity_mwh', 'gas_trading_name'
        ])
    return pd.DataFrame(purchases)

def sales_to_df(sales):
    if not sales:
        return pd.DataFrame(columns=[
            'id', 'contract_date', 'sales_price_eur_mwh', 'quantity_mwh',
            'cost_capacity_eur_mwh', 'cost_transport_eur_mwh', 'purchase_price_eur_mwh',
            'margin_eur_mwh', 'total_revenue', 'total_margin', 'buyer', 'amount_paid', 'payment_status'
        ])
    return pd.DataFrame(sales)

def payments_to_df(payments):
    if not payments:
        return pd.DataFrame(columns=[
            'id', 'payment_date', 'amount_eur', 'buyer', 'related_sales_dates', 'notes'
        ])
    return pd.DataFrame(payments)

def invoices_to_df(invoices):
    if not invoices:
        return pd.DataFrame(columns=[
            'id', 'invoice_number', 'total_amount', 'paid_amount', 'remaining_amount', 'status'
        ])
    return pd.DataFrame(invoices)

def generate_id():
    return datetime.now().strftime("%Y%m%d%H%M%S%f")

def calculate_supplier_balance(purchases):
    df = purchases_to_df(purchases)
    if df.empty:
        return 0.0
    total_received = df['amount_received_eur'].sum() if 'amount_received_eur' in df.columns else 0
    total_used = 0.0
    for _, row in df.iterrows():
        if 'price_eur_mwh' in row and 'quantity_mwh' in row:
            if pd.notna(row['price_eur_mwh']) and pd.notna(row['quantity_mwh']):
                total_used += row['price_eur_mwh'] * row['quantity_mwh']
    return total_received - total_used

def calculate_outstanding_receivables(sales, payments):
    sales_df = sales_to_df(sales)
    payments_df = payments_to_df(payments)
    
    if sales_df.empty:
        return 0.0
    
    total_revenue = sales_df['total_revenue'].sum() if 'total_revenue' in sales_df.columns else 0
    total_received = payments_df['amount_eur'].sum() if not payments_df.empty and 'amount_eur' in payments_df.columns else 0
    
    return total_revenue - total_received
