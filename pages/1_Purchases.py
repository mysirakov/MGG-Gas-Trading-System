import streamlit as st
import pandas as pd
from datetime import datetime, date
from database import (
    load_purchases, save_purchases, load_settings, 
    purchases_to_df, generate_id, load_invoices, save_invoices, invoices_to_df
)

st.set_page_config(page_title="Purchases", page_icon="📦", layout="wide")

st.title("📦 Purchase Management")
st.markdown("Track natural gas purchases, supplier payments, and invoice balances")

settings = load_settings()
purchases = load_purchases()
invoices = load_invoices()

tab1, tab2, tab3, tab4 = st.tabs(["📝 Add Purchase", "📤 Bulk Upload", "📊 View Purchases", "📄 Invoice Tracking"])

with tab1:
    st.subheader("Add Single Purchase Entry")
    
    col1, col2 = st.columns(2)
    
    with col1:
        payment_date = st.date_input("Payment Date", value=date.today(), key="single_payment_date")
        supplier = st.selectbox("Supplier", options=settings.get("suppliers", ["Default Supplier"]), key="single_supplier")
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
        price_eur_mwh = st.number_input("Purchase Price (EUR/MWh)", min_value=0.0, step=0.01, key="single_price")
        quantity_mwh = st.number_input("Quantity (MWh)", min_value=0.0, step=1.0, key="single_quantity")
        gas_trading_name = st.selectbox("Gas Trading Name", options=settings.get("gas_trading_names", ["Default Trading Name"]), key="single_trading_name")
    
    if st.button("Add Purchase", type="primary", key="add_single"):
        new_purchase = {
            "id": generate_id(),
            "payment_date": str(payment_date),
            "supplier": supplier,
            "payment_method": payment_method,
            "amount_sent_eur": amount_sent,
            "invoice_number": invoice_number,
            "receipt_date": str(receipt_date),
            "amount_received_eur": amount_received,
            "price_eur_mwh": price_eur_mwh,
            "quantity_mwh": quantity_mwh,
            "gas_trading_name": gas_trading_name,
            "total_cost": price_eur_mwh * quantity_mwh
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
                "total_amount": total_amt,
                "paid_amount": amount_sent,
                "remaining_amount": max(0, total_amt - amount_sent),
                "status": "Paid" if amount_sent >= total_amt else "Partial"
            }
            invoices.append(new_invoice)
        save_invoices(invoices)
        
        st.success("Purchase added successfully!")
        st.rerun()

with tab2:
    st.subheader("Bulk Upload Purchases")
    st.markdown("Upload a CSV or Excel file with purchase data")
    
    with st.expander("📋 Required Columns Format"):
        st.markdown("""
        Your file should contain the following columns:
        - `payment_date` - Date of payment (YYYY-MM-DD)
        - `supplier` - Supplier name
        - `payment_method` - Payment method used
        - `amount_sent_eur` - Amount sent in EUR
        - `invoice_number` - Invoice reference
        - `invoice_total_eur` - Total invoice amount (for partial payment tracking)
        - `receipt_date` - Date received by supplier (YYYY-MM-DD)
        - `amount_received_eur` - Amount received by supplier in EUR
        - `price_eur_mwh` - Purchase price in EUR per MWh
        - `quantity_mwh` - Quantity in MWh
        - `gas_trading_name` - Gas trading name for delivery
        """)
        
        sample_data = pd.DataFrame({
            'payment_date': ['2024-11-01'],
            'supplier': ['Default Supplier'],
            'payment_method': ['Unicredit'],
            'amount_sent_eur': [10000],
            'invoice_number': ['INV-001'],
            'invoice_total_eur': [25000],
            'receipt_date': ['2024-11-03'],
            'amount_received_eur': [9950],
            'price_eur_mwh': [35.50],
            'quantity_mwh': [280],
            'gas_trading_name': ['Default Trading Name']
        })
        st.dataframe(sample_data)
        
        csv = sample_data.to_csv(index=False)
        st.download_button("Download Template CSV", csv, "purchases_template.csv", "text/csv")
    
    uploaded_file = st.file_uploader("Upload Purchases File", type=['csv', 'xlsx'], key="bulk_purchases")
    
    if uploaded_file:
        try:
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)
            
            st.subheader("Preview of Uploaded Data")
            st.dataframe(df, use_container_width=True)
            
            if st.button("Import All Rows", type="primary", key="import_purchases"):
                count = 0
                for _, row in df.iterrows():
                    invoice_num = str(row.get('invoice_number', ''))
                    amount_sent = float(row.get('amount_sent_eur', 0))
                    invoice_total = float(row.get('invoice_total_eur', amount_sent))
                    
                    new_purchase = {
                        "id": generate_id(),
                        "payment_date": str(row.get('payment_date', '')),
                        "supplier": str(row.get('supplier', settings['suppliers'][0])),
                        "payment_method": str(row.get('payment_method', settings['payment_methods'][0])),
                        "amount_sent_eur": amount_sent,
                        "invoice_number": invoice_num,
                        "receipt_date": str(row.get('receipt_date', '')),
                        "amount_received_eur": float(row.get('amount_received_eur', 0)),
                        "price_eur_mwh": float(row.get('price_eur_mwh', 0)),
                        "quantity_mwh": float(row.get('quantity_mwh', 0)),
                        "gas_trading_name": str(row.get('gas_trading_name', '')),
                        "total_cost": float(row.get('price_eur_mwh', 0)) * float(row.get('quantity_mwh', 0))
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
                            "total_amount": invoice_total,
                            "paid_amount": amount_sent,
                            "remaining_amount": max(0, invoice_total - amount_sent),
                            "status": "Paid" if amount_sent >= invoice_total else "Partial"
                        }
                        invoices.append(new_invoice)
                    
                    count += 1
                
                save_purchases(purchases)
                save_invoices(invoices)
                st.success(f"Successfully imported {count} purchases!")
                st.rerun()
        except Exception as e:
            st.error(f"Error reading file: {str(e)}")

with tab3:
    st.subheader("All Purchases")
    
    df = purchases_to_df(purchases)
    
    if not df.empty:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            total_sent = df['amount_sent_eur'].sum()
            st.metric("Total Amount Sent", f"€{total_sent:,.2f}")
        with col2:
            total_received = df['amount_received_eur'].sum()
            st.metric("Total Received by Supplier", f"€{total_received:,.2f}")
        with col3:
            total_quantity = df['quantity_mwh'].sum()
            st.metric("Total Quantity", f"{total_quantity:,.2f} MWh")
        with col4:
            if total_quantity > 0:
                avg_price = (df['price_eur_mwh'] * df['quantity_mwh']).sum() / total_quantity
                st.metric("Weighted Avg Price", f"€{avg_price:,.2f}/MWh")
            else:
                st.metric("Weighted Avg Price", "€0.00/MWh")
        
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        with col1:
            filter_supplier = st.multiselect("Filter by Supplier", options=df['supplier'].unique().tolist())
        with col2:
            filter_method = st.multiselect("Filter by Payment Method", options=df['payment_method'].unique().tolist())
        
        filtered_df = df.copy()
        if filter_supplier:
            filtered_df = filtered_df[filtered_df['supplier'].isin(filter_supplier)]
        if filter_method:
            filtered_df = filtered_df[filtered_df['payment_method'].isin(filter_method)]
        
        st.dataframe(filtered_df, use_container_width=True, hide_index=True)
        
        csv = filtered_df.to_csv(index=False)
        st.download_button("Export to CSV", csv, "purchases_export.csv", "text/csv")
        
        st.markdown("---")
        st.subheader("Delete Purchase")
        if len(purchases) > 0:
            delete_options = [f"{p['payment_date']} - {p['supplier']} - €{p['amount_sent_eur']}" for p in purchases]
            selected_delete = st.selectbox("Select purchase to delete", options=delete_options)
            if st.button("Delete Selected", type="secondary"):
                idx = delete_options.index(selected_delete)
                purchases.pop(idx)
                save_purchases(purchases)
                st.success("Purchase deleted!")
                st.rerun()
    else:
        st.info("No purchases recorded yet. Add your first purchase above!")

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
            new_inv_total = st.number_input("Total Amount (EUR)", min_value=0.0, step=100.0, key="new_inv_total")
            
            if st.button("Create Invoice", type="primary"):
                if new_inv_number:
                    new_invoice = {
                        "id": generate_id(),
                        "invoice_number": new_inv_number,
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
    else:
        st.info("No invoices recorded yet. Invoices are created when you add purchases.")
