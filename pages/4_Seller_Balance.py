import streamlit as st
import pandas as pd
from datetime import date
from database import (
    get_supplier_payments, add_supplier_payment, delete_supplier_payment,
    get_sales, get_settings, get_invoices, get_dashboard_metrics,
    supplier_payments_to_df, sales_to_df
)
from components import load_material_icons, page_header, metric_card, section_header

st.set_page_config(page_title="Seller Balance", page_icon="🏦", layout="wide")

try:
    with open('style.css') as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
except:
    pass

load_material_icons()

page_header("Seller Balance", "Track supplier balance, payments, and invoices")

settings = get_settings()
purchases = get_supplier_payments()
sales = get_sales()
invoices = get_invoices()
metrics = get_dashboard_metrics()

purchases_df = supplier_payments_to_df(purchases)
sales_df = sales_to_df(sales)

total_purchase_cost = metrics['total_purchase_cost']
total_received_by_supplier = metrics['total_received_by_suppliers']
supplier_balance = metrics['supplier_balance']

col1, col2, col3 = st.columns(3)

with col1:
    metric_card("account_balance_wallet", "Received by Supplier", f"€{total_received_by_supplier:,.0f}", "blue")
with col2:
    metric_card("shopping_cart", "Total Purchase Cost", f"€{total_purchase_cost:,.0f}", "orange")
with col3:
    color = "green" if supplier_balance >= 0 else "red"
    metric_card("savings", "Supplier Balance", f"€{supplier_balance:,.0f}", color)

st.markdown("<div style='height: 1.5rem;'></div>", unsafe_allow_html=True)

tab1, tab2, tab3, tab4 = st.tabs(["Balance Overview", "Add Payment", "Bulk Upload", "Invoice Tracking"])

with tab1:
    section_header("account_balance", "Balance Breakdown by Supplier")
    
    if not purchases_df.empty and 'supplier' in purchases_df.columns:
        suppliers = purchases_df['supplier'].dropna().unique().tolist()
        
        balance_data = []
        for supplier in suppliers:
            sup_purchases = purchases_df[purchases_df['supplier'] == supplier]
            amount_received = sup_purchases['amount_received_eur'].sum()
            
            balance_data.append({
                'Supplier': supplier,
                'Amount Received (EUR)': amount_received,
                'Purchase Cost (EUR)': total_purchase_cost,
                'Available Balance (EUR)': amount_received - total_purchase_cost
            })
        
        balance_df = pd.DataFrame(balance_data)
        
        st.dataframe(
            balance_df.style.format({
                'Amount Received (EUR)': '€{:,.2f}',
                'Purchase Cost (EUR)': '€{:,.2f}',
                'Available Balance (EUR)': '€{:,.2f}'
            }),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.markdown("""
            <div style="
                background: rgba(255, 255, 255, 0.7);
                border: 1px solid rgba(255, 255, 255, 0.5);
                border-radius: 16px;
                padding: 3rem 2rem;
                text-align: center;
                color: #64748b;
                backdrop-filter: blur(12px);
            ">
                <span class="material-icons-round" style="font-size: 48px; opacity: 0.4; color: #3b82f6;">account_balance</span>
                <p style="margin: 1rem 0 0 0;">No payment data available. Add payments to see supplier balances.</p>
            </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<div style='height: 2rem;'></div>", unsafe_allow_html=True)
    
    section_header("history", "Payment History")
    
    if not purchases_df.empty:
        display_cols = ['payment_date', 'supplier', 'payment_method', 'amount_sent_eur', 'amount_received_eur', 'invoice_number']
        available_cols = [c for c in display_cols if c in purchases_df.columns]
        
        display_df = purchases_df[available_cols].copy()
        if 'payment_date' in display_df.columns:
            display_df['payment_date'] = pd.to_datetime(display_df['payment_date']).dt.strftime('%b %d, %Y')
        
        st.dataframe(display_df, use_container_width=True, hide_index=True, height=300)
        
        st.markdown("<div style='height: 2rem;'></div>", unsafe_allow_html=True)
        
        section_header("delete", "Delete Payment")
        if len(purchases) > 0:
            delete_options = {f"{p['payment_date']} - {p.get('supplier', 'N/A')} - €{float(p['amount_sent_eur']):.2f}": p['id'] for p in purchases}
            col1, col2 = st.columns([3, 1])
            with col1:
                selected_delete = st.selectbox("Select payment to delete", options=list(delete_options.keys()), key="del_payment", label_visibility="collapsed")
            with col2:
                if st.button("Delete", type="secondary"):
                    payment_id = delete_options[selected_delete]
                    delete_supplier_payment(payment_id)
                    st.success("Payment deleted!")
                    st.rerun()
    else:
        st.info("No payments recorded yet.")

with tab2:
    section_header("add_card", "Add Supplier Payment")
    
    col1, col2 = st.columns(2)
    
    with col1:
        payment_date = st.date_input("Payment Date", value=date.today(), key="single_payment_date")
        supplier = st.selectbox("Supplier", options=settings.get("suppliers", ["GPE"]), key="single_supplier")
        payment_method = st.selectbox("Payment Method", options=settings.get("payment_methods", ["Unicredit", "Financial Agent"]), key="single_payment_method")
        amount_sent = st.number_input("Amount Sent (EUR)", min_value=0.0, step=100.0, key="single_amount_sent")
        invoice_number = st.text_input("Invoice Number", key="single_invoice")
    
    with col2:
        receipt_date = st.date_input("Receipt Date (by supplier)", value=date.today(), key="single_receipt_date")
        amount_received = st.number_input("Amount Received by Supplier (EUR)", min_value=0.0, step=100.0, key="single_amount_received")
    
    st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)
    
    if st.button("Add Payment", type="primary", key="add_single"):
        add_supplier_payment(
            payment_date, supplier, payment_method, amount_sent,
            invoice_number, receipt_date, amount_received
        )
        st.success("Payment added successfully!")
        st.rerun()

with tab3:
    section_header("upload_file", "Bulk Upload Payments")
    
    with st.expander("Required Columns Format"):
        st.markdown("""
        Your file should contain the following columns:
        - `payment_date` - Date of payment (DD/MM/YYYY)
        - `supplier` - Supplier name
        - `payment_method` - Payment method used
        - `amount_sent_eur` - Amount sent in EUR
        - `invoice_number` - Invoice reference
        - `receipt_date` - Date received by supplier (DD/MM/YYYY)
        - `amount_received_eur` - Amount received by supplier in EUR
        """)
        
        sample_data = pd.DataFrame({
            'payment_date': ['01/11/2024'],
            'supplier': ['GPE'],
            'payment_method': ['Unicredit'],
            'amount_sent_eur': [50000],
            'invoice_number': ['INV-001'],
            'receipt_date': ['03/11/2024'],
            'amount_received_eur': [49985]
        })
        st.dataframe(sample_data)
        
        csv = sample_data.to_csv(index=False)
        st.download_button("Download Template CSV", csv, "payments_template.csv", "text/csv")
    
    uploaded_file = st.file_uploader("Upload Payments File", type=['csv', 'xlsx'], key="bulk_payments")
    
    if uploaded_file:
        try:
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)
            
            st.markdown("##### Preview of Uploaded Data")
            st.dataframe(df, use_container_width=True)
            
            if st.button("Import All Rows", type="primary", key="import_payments"):
                count = 0
                for _, row in df.iterrows():
                    payment_date_str = str(row.get('payment_date', ''))
                    receipt_date_str = str(row.get('receipt_date', ''))
                    try:
                        payment_date = pd.to_datetime(payment_date_str, dayfirst=True).date()
                    except:
                        payment_date = date.today()
                    try:
                        receipt_date = pd.to_datetime(receipt_date_str, dayfirst=True).date()
                    except:
                        receipt_date = date.today()
                    
                    add_supplier_payment(
                        payment_date,
                        str(row.get('supplier', settings.get('suppliers', ['GPE'])[0])),
                        str(row.get('payment_method', settings.get('payment_methods', ['Unicredit'])[0])),
                        float(row.get('amount_sent_eur', 0)),
                        str(row.get('invoice_number', '')),
                        receipt_date,
                        float(row.get('amount_received_eur', 0))
                    )
                    count += 1
                
                st.success(f"Successfully imported {count} payments!")
                st.rerun()
        except Exception as e:
            st.error(f"Error reading file: {str(e)}")

with tab4:
    section_header("receipt", "Invoice Tracking")
    
    if invoices:
        inv_df = pd.DataFrame(invoices)
        
        if not inv_df.empty:
            col1, col2, col3 = st.columns(3)
            total_invoiced = inv_df['total_amount'].sum()
            total_paid = inv_df['paid_amount'].sum()
            total_remaining = total_invoiced - total_paid
            
            with col1:
                metric_card("description", "Total Invoiced", f"€{total_invoiced:,.0f}", "blue")
            with col2:
                metric_card("check_circle", "Total Paid", f"€{total_paid:,.0f}", "green")
            with col3:
                metric_card("pending", "Outstanding", f"€{max(0, total_remaining):,.0f}", "orange")
            
            st.markdown("<div style='height: 1.5rem;'></div>", unsafe_allow_html=True)
            
            display_cols = ['invoice_number', 'supplier', 'total_amount', 'paid_amount', 'status']
            available_cols = [c for c in display_cols if c in inv_df.columns]
            st.dataframe(inv_df[available_cols], use_container_width=True, hide_index=True)
    else:
        st.markdown("""
            <div style="
                background: rgba(255, 255, 255, 0.7);
                border: 1px solid rgba(255, 255, 255, 0.5);
                border-radius: 16px;
                padding: 3rem 2rem;
                text-align: center;
                color: #64748b;
                backdrop-filter: blur(12px);
            ">
                <span class="material-icons-round" style="font-size: 48px; opacity: 0.4; color: #3b82f6;">receipt_long</span>
                <p style="margin: 1rem 0 0 0;">No invoices recorded yet. Invoices are created when you add payments with invoice numbers.</p>
            </div>
        """, unsafe_allow_html=True)
