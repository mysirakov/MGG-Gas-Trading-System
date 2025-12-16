import streamlit as st
import pandas as pd
from datetime import date
from database import (
    load_purchases, save_purchases, load_sales, load_settings,
    purchases_to_df, sales_to_df, generate_id,
    load_invoices, save_invoices, invoices_to_df
)

st.set_page_config(page_title="Seller Balance", page_icon="🏦", layout="wide")

st.title("🏦 Seller Balance")
st.markdown("Track supplier balance, payments, and invoices")

settings = load_settings()
purchases = load_purchases()
sales = load_sales()
invoices = load_invoices()

purchases_df = purchases_to_df(purchases)
sales_df = sales_to_df(sales)

valid_sales = sales_df[
    (sales_df['quantity_mwh'] > 0) & 
    (sales_df['purchase_price_eur_mwh'] > 0)
] if not sales_df.empty and 'quantity_mwh' in sales_df.columns and 'purchase_price_eur_mwh' in sales_df.columns else pd.DataFrame()

total_purchase_cost = (valid_sales['quantity_mwh'] * valid_sales['purchase_price_eur_mwh']).sum() if not valid_sales.empty else 0

total_received_by_supplier = purchases_df['amount_received_eur'].sum() if not purchases_df.empty and 'amount_received_eur' in purchases_df.columns else 0

supplier_balance = total_received_by_supplier - total_purchase_cost

tab1, tab2, tab3, tab4 = st.tabs(["📊 Balance Overview", "📝 Add Payment", "📤 Bulk Upload", "📄 Invoice Tracking"])

with tab1:
    st.header("📊 Overall Supplier Balance")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Received by Supplier", f"€{total_received_by_supplier:,.2f}", 
                  help="Total amount received by the supplier (GPE) from your payments")
    
    with col2:
        st.metric("Total Purchase Cost", f"€{total_purchase_cost:,.2f}",
                  help="Total value of gas purchased = Sum of (Quantity MWh × Purchase Price EUR/MWh) from Sales")
    
    with col3:
        delta_text = "Available" if supplier_balance >= 0 else "Overdraw"
        st.metric("Supplier Balance", f"€{supplier_balance:,.2f}", 
                  delta=delta_text,
                  help="Balance available with supplier = Amount Received - Purchase Cost")
    
    st.markdown("---")
    
    st.header("📋 Balance Breakdown by Supplier")
    
    if not purchases_df.empty:
        suppliers = purchases_df['supplier'].unique().tolist()
        
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
        st.info("No payment data available. Add payments to see supplier balances.")
    
    st.markdown("---")
    
    st.header("💳 Payment History")
    
    if not purchases_df.empty:
        display_cols = ['payment_date', 'supplier', 'payment_method', 'amount_sent_eur', 'amount_received_eur', 'invoice_number']
        available_cols = [c for c in display_cols if c in purchases_df.columns]
        
        st.dataframe(purchases_df[available_cols], use_container_width=True, hide_index=True)
        
        st.markdown("---")
        st.subheader("🗑️ Delete Payment")
        if len(purchases) > 0:
            delete_options = [f"{p['payment_date']} - {p['supplier']} - €{p['amount_sent_eur']}" for p in purchases]
            selected_delete = st.selectbox("Select payment to delete", options=delete_options, key="del_payment")
            if st.button("Delete Selected Payment", type="secondary"):
                idx = delete_options.index(selected_delete)
                purchases.pop(idx)
                save_purchases(purchases)
                st.success("Payment deleted!")
                st.rerun()
    else:
        st.info("No payments recorded yet.")

with tab2:
    st.subheader("Add Supplier Payment")
    
    col1, col2 = st.columns(2)
    
    with col1:
        payment_date = st.date_input("Payment Date", value=date.today(), key="single_payment_date")
        supplier = st.selectbox("Supplier", options=settings.get("suppliers", ["GPE"]), key="single_supplier")
        payment_method = st.selectbox("Payment Method", options=settings.get("payment_methods", ["Unicredit", "Financial Agent"]), key="single_payment_method")
        amount_sent = st.number_input("Amount Sent (EUR)", min_value=0.0, step=100.0, key="single_amount_sent")
        
        existing_invoices = [inv['invoice_number'] for inv in invoices if inv.get('remaining_amount', 0) > 0]
        invoice_option = st.radio("Invoice", ["New Invoice", "Existing Invoice"], horizontal=True)
        
        if invoice_option == "New Invoice":
            invoice_number = st.text_input("Invoice Number", key="single_invoice")
            invoice_total = st.number_input("Total Invoice Amount (EUR)", min_value=0.0, step=100.0, key="invoice_total", 
                                           help="Full amount of the invoice (for tracking partial payments)")
        else:
            if existing_invoices:
                invoice_number = st.selectbox("Select Invoice", options=existing_invoices, key="existing_invoice")
                selected_inv = next((inv for inv in invoices if inv['invoice_number'] == invoice_number), None)
                if selected_inv:
                    st.info(f"Remaining on invoice: €{selected_inv['remaining_amount']:,.2f}")
                invoice_total = None
            else:
                st.warning("No existing invoices with remaining balance")
                invoice_number = st.text_input("Invoice Number", key="single_invoice_fallback")
                invoice_total = st.number_input("Total Invoice Amount (EUR)", min_value=0.0, step=100.0, key="invoice_total_fallback")
    
    with col2:
        receipt_date = st.date_input("Receipt Date (by supplier)", value=date.today(), key="single_receipt_date")
        amount_received = st.number_input("Amount Received by Supplier (EUR)", min_value=0.0, step=100.0, key="single_amount_received")
    
    if st.button("Add Payment", type="primary", key="add_single"):
        new_purchase = {
            "id": generate_id(),
            "payment_date": str(payment_date),
            "supplier": supplier,
            "payment_method": payment_method,
            "amount_sent_eur": amount_sent,
            "invoice_number": invoice_number,
            "receipt_date": str(receipt_date),
            "amount_received_eur": amount_received,
            "price_eur_mwh": 0,
            "quantity_mwh": 0,
            "total_cost": 0
        }
        purchases.append(new_purchase)
        save_purchases(purchases)
        
        existing_invoice = next((inv for inv in invoices if inv['invoice_number'] == invoice_number), None)
        if existing_invoice:
            existing_invoice['paid_amount'] += amount_sent
            existing_invoice['remaining_amount'] = max(0, existing_invoice['total_amount'] - existing_invoice['paid_amount'])
            existing_invoice['status'] = 'Paid' if existing_invoice['remaining_amount'] <= 0 else 'Partial'
        else:
            total_amt = invoice_total if invoice_total else amount_sent
            new_invoice = {
                "id": generate_id(),
                "invoice_number": invoice_number,
                "supplier": supplier,
                "total_amount": total_amt,
                "paid_amount": amount_sent,
                "remaining_amount": max(0, total_amt - amount_sent),
                "status": "Paid" if amount_sent >= total_amt else "Partial"
            }
            invoices.append(new_invoice)
        save_invoices(invoices)
        
        st.success("Payment added successfully!")
        st.rerun()

with tab3:
    st.subheader("Bulk Upload Payments")
    st.markdown("Upload a CSV or Excel file with payment data")
    
    with st.expander("📋 Required Columns Format"):
        st.markdown("""
        Your file should contain the following columns:
        - `payment_date` - Date of payment (DD/MM/YYYY)
        - `supplier` - Supplier name
        - `payment_method` - Payment method used
        - `amount_sent_eur` - Amount sent in EUR
        - `invoice_number` - Invoice reference
        - `invoice_total_eur` - Total invoice amount (for partial payment tracking)
        - `receipt_date` - Date received by supplier (DD/MM/YYYY)
        - `amount_received_eur` - Amount received by supplier in EUR
        """)
        
        sample_data = pd.DataFrame({
            'payment_date': ['01/11/2024'],
            'supplier': ['GPE'],
            'payment_method': ['Unicredit'],
            'amount_sent_eur': [50000],
            'invoice_number': ['INV-001'],
            'invoice_total_eur': [50000],
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
            
            st.subheader("Preview of Uploaded Data")
            st.dataframe(df, use_container_width=True)
            
            if st.button("Import All Rows", type="primary", key="import_payments"):
                count = 0
                for _, row in df.iterrows():
                    invoice_num = str(row.get('invoice_number', ''))
                    amount_sent = float(row.get('amount_sent_eur', 0))
                    invoice_total = float(row.get('invoice_total_eur', amount_sent))
                    
                    new_purchase = {
                        "id": generate_id(),
                        "payment_date": str(row.get('payment_date', '')),
                        "supplier": str(row.get('supplier', settings.get('suppliers', ['GPE'])[0])),
                        "payment_method": str(row.get('payment_method', settings.get('payment_methods', ['Unicredit'])[0])),
                        "amount_sent_eur": amount_sent,
                        "invoice_number": invoice_num,
                        "receipt_date": str(row.get('receipt_date', '')),
                        "amount_received_eur": float(row.get('amount_received_eur', 0)),
                        "price_eur_mwh": 0,
                        "quantity_mwh": 0,
                        "total_cost": 0
                    }
                    purchases.append(new_purchase)
                    
                    existing_invoice = next((inv for inv in invoices if inv['invoice_number'] == invoice_num), None)
                    if existing_invoice:
                        existing_invoice['paid_amount'] += amount_sent
                        existing_invoice['remaining_amount'] = max(0, existing_invoice['total_amount'] - existing_invoice['paid_amount'])
                        existing_invoice['status'] = 'Paid' if existing_invoice['remaining_amount'] <= 0 else 'Partial'
                    else:
                        new_invoice = {
                            "id": generate_id(),
                            "invoice_number": invoice_num,
                            "supplier": str(row.get('supplier', settings.get('suppliers', ['GPE'])[0])),
                            "total_amount": invoice_total,
                            "paid_amount": amount_sent,
                            "remaining_amount": max(0, invoice_total - amount_sent),
                            "status": "Paid" if amount_sent >= invoice_total else "Partial"
                        }
                        invoices.append(new_invoice)
                    
                    count += 1
                
                save_purchases(purchases)
                save_invoices(invoices)
                st.success(f"Successfully imported {count} payments!")
                st.rerun()
        except Exception as e:
            st.error(f"Error reading file: {str(e)}")

with tab4:
    st.subheader("📄 Invoice Tracking")
    st.markdown("Monitor invoice payment status and remaining balances")
    
    inv_df = invoices_to_df(invoices)
    
    if not inv_df.empty:
        col1, col2, col3 = st.columns(3)
        with col1:
            total_invoiced = inv_df['total_amount'].sum()
            st.metric("Total Invoiced", f"€{total_invoiced:,.2f}")
        with col2:
            total_paid = inv_df['paid_amount'].sum()
            st.metric("Total Paid", f"€{total_paid:,.2f}")
        with col3:
            total_remaining = inv_df['remaining_amount'].sum()
            st.metric("Total Outstanding", f"€{total_remaining:,.2f}")
        
        st.markdown("---")
        
        status_options = inv_df['status'].unique().tolist()
        filter_status = st.multiselect("Filter by Status", options=status_options)
        
        filtered_inv_df = inv_df.copy()
        if filter_status:
            filtered_inv_df = filtered_inv_df[filtered_inv_df['status'].isin(filter_status)]
        
        st.dataframe(filtered_inv_df, use_container_width=True, hide_index=True)
        
        st.markdown("---")
        st.subheader("Manage Invoices")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Add New Invoice**")
            new_inv_number = st.text_input("Invoice Number", key="new_inv_number")
            new_inv_supplier = st.selectbox("Supplier", options=settings.get("suppliers", ["GPE"]), key="new_inv_supplier")
            new_inv_total = st.number_input("Total Amount (EUR)", min_value=0.0, step=100.0, key="new_inv_total")
            
            if st.button("Create Invoice", type="primary"):
                if new_inv_number:
                    new_invoice = {
                        "id": generate_id(),
                        "invoice_number": new_inv_number,
                        "supplier": new_inv_supplier,
                        "total_amount": new_inv_total,
                        "paid_amount": 0,
                        "remaining_amount": new_inv_total,
                        "status": "Pending"
                    }
                    invoices.append(new_invoice)
                    save_invoices(invoices)
                    st.success("Invoice created!")
                    st.rerun()
        
        with col2:
            st.markdown("**Update Invoice Total**")
            if invoices:
                inv_options = [f"{inv['invoice_number']} (€{inv['total_amount']:,.2f})" for inv in invoices]
                selected_inv = st.selectbox("Select Invoice", options=inv_options, key="update_inv")
                new_total = st.number_input("New Total Amount (EUR)", min_value=0.0, step=100.0, key="update_inv_total")
                
                if st.button("Update Total", type="secondary"):
                    idx = inv_options.index(selected_inv)
                    invoices[idx]['total_amount'] = new_total
                    invoices[idx]['remaining_amount'] = max(0, new_total - invoices[idx]['paid_amount'])
                    invoices[idx]['status'] = 'Paid' if invoices[idx]['remaining_amount'] <= 0 else 'Partial'
                    save_invoices(invoices)
                    st.success("Invoice updated!")
                    st.rerun()
        
        st.markdown("---")
        st.markdown("**Delete Invoice**")
        if invoices:
            del_inv_options = [f"{inv['invoice_number']} - {inv.get('supplier', 'N/A')} (€{inv['total_amount']:,.2f})" for inv in invoices]
            selected_del_inv = st.selectbox("Select Invoice to Delete", options=del_inv_options, key="del_inv")
            
            if st.button("🗑️ Delete Invoice", type="secondary"):
                idx = del_inv_options.index(selected_del_inv)
                deleted_inv = invoices.pop(idx)
                save_invoices(invoices)
                st.success(f"Invoice '{deleted_inv['invoice_number']}' deleted!")
                st.rerun()
        else:
            st.info("No invoices to delete.")
    else:
        st.info("No invoices recorded yet. Invoices are created when you add payments.")
