import streamlit as st
import csv
import io
from datetime import datetime, date
from database import (
    get_supplier_payments, add_supplier_payment, update_supplier_payment, delete_supplier_payment,
    get_settings, supplier_payments_to_df, get_sales, get_invoices, get_dashboard_metrics, sales_to_df
)
from components import load_material_icons, page_header, metric_card, section_header, empty_state, setup_page
from auth import require_auth

st.set_page_config(
    page_title="Mix Gas Group | Seller Balance",
    page_icon="https://slelguoygbfzlpylpxfs.supabase.co/storage/v1/render/image/public/project-uploads/704afe63-0b4a-4050-803e-5116d1754a58/Untitled-Project-1768468114127.png?width=8000&height=8000&resize=contain",
    layout="wide"
)

require_auth()
setup_page()

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

purchases_data = supplier_payments_to_df(purchases)
sales_data = sales_to_df(sales)

gpe_purchase_cost = metrics['gpe_purchase_cost']
total_received_by_supplier = metrics['total_received_by_suppliers']
supplier_balance = metrics['supplier_balance']

col1, col2, col3 = st.columns(3)

with col1:
    metric_card("account_balance_wallet", "Received by Supplier", f"€{total_received_by_supplier:,.0f}", "blue")
with col2:
    metric_card("shopping_cart", "GPE Purchase Cost", f"€{gpe_purchase_cost:,.0f}", "orange")
with col3:
    color = "green" if supplier_balance >= 0 else "red"
    metric_card("savings", "Supplier Balance", f"€{supplier_balance:,.0f}", color)

st.markdown("<div style='height: 1.5rem;'></div>", unsafe_allow_html=True)

tab1, tab2, tab3, tab4 = st.tabs(["Balance Overview", "Add Payment", "Bulk Upload", "Invoice Tracking"])

with tab1:
    section_header("account_balance", "Balance Breakdown by Supplier")
    
    if purchases_data:
        # Get unique suppliers
        suppliers = list(set(p['supplier'] for p in purchases_data if p.get('supplier')))
        
        balance_data = []
        supplier_costs = metrics.get('supplier_costs', {})
        
        for supplier in suppliers:
            sup_purchases = [p for p in purchases_data if p.get('supplier') == supplier]
            amount_received = sum(float(p.get('amount_received_eur', 0) or 0) for p in sup_purchases)
            purchase_cost = supplier_costs.get(supplier, 0)
            
            balance_data.append({
                'Supplier': supplier,
                'Amount Received': f"€{amount_received:,.2f}",
                'Purchase Cost': f"€{purchase_cost:,.2f}",
                'Available Balance': f"€{amount_received - purchase_cost:,.2f}"
            })
        
        st.dataframe(
            balance_data,
            width="stretch"
        )

    else:
        empty_state("account_balance", "No payment data available. Add payments to see supplier balances.")
    
    st.markdown("<div style='height: 2rem;'></div>", unsafe_allow_html=True)
    
    section_header("history", "Payment History")
    
    if purchases_data:
        display_cols = ['payment_date', 'supplier', 'payment_method', 'amount_sent_eur', 'amount_received_eur', 'invoice_number']
        
        history_display = []
        for p in purchases_data:
            row = {}
            for col in display_cols:
                val = p.get(col)
                if col == 'payment_date' and val:
                    if isinstance(val, (date, datetime)):
                        row[col] = val.strftime('%b %d, %Y')
                    else:
                        row[col] = str(val)
                elif col in ['amount_sent_eur', 'amount_received_eur']:
                    row[col] = f"€{float(val or 0):,.2f}"
                else:
                    row[col] = val
            history_display.append(row)
            
        st.dataframe(history_display, width="stretch", height=300)
        
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
        
        sample_rows = [
            ['payment_date', 'supplier', 'payment_method', 'amount_sent_eur', 'invoice_number', 'receipt_date', 'amount_received_eur'],
            ['01/11/2024', 'GPE', 'Unicredit', 50000, 'INV-001', '03/11/2024', 49985]
        ]
        st.table(sample_rows)
        
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerows(sample_rows)
        csv_data = output.getvalue()
        st.download_button("Download Template CSV", csv_data, "payments_template.csv", "text/csv")
    
    uploaded_file = st.file_uploader("Upload Payments File (CSV only)", type=['csv'], key="bulk_payments")
    
    if uploaded_file:
        try:
            content = uploaded_file.read().decode('utf-8')
            csv_reader = csv.DictReader(io.StringIO(content))
            rows = list(csv_reader)
            
            st.markdown("##### Preview of Uploaded Data")
            st.dataframe(rows, width="stretch")
            
            if st.button("Import All Rows", type="primary", key="import_payments"):
                count = 0
                for row in rows:
                    payment_date_str = row.get('payment_date', '').strip()
                    receipt_date_str = row.get('receipt_date', '').strip()
                    
                    # Parse dates
                    def parse_custom_date(date_str):
                        if not date_str:
                            return date.today()
                        for fmt in ['%d/%m/%Y', '%Y-%m-%d', '%m/%d/%Y']:
                            try:
                                return datetime.strptime(date_str, fmt).date()
                            except ValueError:
                                continue
                        return date.today()

                    p_date = parse_custom_date(payment_date_str)
                    r_date = parse_custom_date(receipt_date_str)
                    
                    add_supplier_payment(
                        p_date,
                        str(row.get('supplier', settings.get('suppliers', ['GPE'])[0])),
                        str(row.get('payment_method', settings.get('payment_methods', ['Unicredit'])[0])),
                        float(row.get('amount_sent_eur', 0) or 0),
                        str(row.get('invoice_number', '')),
                        r_date,
                        float(row.get('amount_received_eur', 0) or 0)
                    )
                    count += 1
                
                st.success(f"Successfully imported {count} payments!")
                st.rerun()
        except Exception as e:
            st.error(f"Error reading file: {str(e)}")

with tab4:
    section_header("receipt", "Invoice Tracking")
    
    if invoices:
        col1, col2, col3 = st.columns(3)
        total_invoiced = sum(float(inv.get('total_amount', 0) or 0) for inv in invoices)
        total_paid = sum(float(inv.get('paid_amount', 0) or 0) for inv in invoices)
        total_remaining = total_invoiced - total_paid
        
        with col1:
            metric_card("description", "Total Invoiced", f"€{total_invoiced:,.0f}", "blue")
        with col2:
            metric_card("check_circle", "Total Paid", f"€{total_paid:,.0f}", "green")
        with col3:
            metric_card("pending", "Outstanding", f"€{max(0, total_remaining):,.0f}", "orange")
        
        st.markdown("<div style='height: 1.5rem;'></div>", unsafe_allow_html=True)
        
        display_cols = ['invoice_number', 'supplier', 'total_amount', 'paid_amount', 'status']
        inv_display = []
        for inv in invoices:
            row = {col: inv.get(col) for col in display_cols}
            # Format numbers for display
            row['total_amount'] = f"€{float(row['total_amount'] or 0):,.2f}"
            row['paid_amount'] = f"€{float(row['paid_amount'] or 0):,.2f}"
            inv_display.append(row)
            
        st.dataframe(inv_display, width="stretch")
    else:
        empty_state("receipt_long", "No invoices recorded yet. Invoices are created when you add payments with invoice numbers.")

