import streamlit as st
import pandas as pd
from datetime import datetime, date
from database import (
    load_payments_received, save_payments_received, load_settings, load_sales, save_sales,
    payments_to_df, sales_to_df, generate_id, calculate_outstanding_receivables
)

st.set_page_config(page_title="Payments", page_icon="💳", layout="wide")

st.title("💳 Payment Tracking")
st.markdown("Track payments received from buyers and reconcile outstanding balances")

settings = load_settings()
payments = load_payments_received()
sales = load_sales()

sales_df = sales_to_df(sales)
payments_df = payments_to_df(payments)

total_revenue = sales_df['total_revenue'].sum() if not sales_df.empty and 'total_revenue' in sales_df.columns else 0
total_received = payments_df['amount_eur'].sum() if not payments_df.empty and 'amount_eur' in payments_df.columns else 0
outstanding = total_revenue - total_received

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Total Revenue (from Sales)", f"€{total_revenue:,.2f}")
with col2:
    st.metric("Total Payments Received", f"€{total_received:,.2f}")
with col3:
    st.metric("Outstanding Receivables", f"€{outstanding:,.2f}", delta=f"{'Owed' if outstanding > 0 else 'Cleared'}")

st.markdown("---")

tab1, tab2, tab3 = st.tabs(["📝 Record Payment", "📤 Bulk Upload", "📊 View Payments"])

with tab1:
    st.subheader("Record Payment Received")
    
    col1, col2 = st.columns(2)
    
    with col1:
        payment_date = st.date_input("Payment Received Date", value=date.today(), key="single_payment_recv_date")
        amount = st.number_input("Amount Received (EUR)", min_value=0.0, step=100.0, key="single_recv_amount")
        buyer = st.selectbox("Buyer", options=settings.get("buyers", ["Keler"]), key="single_recv_buyer")
    
    with col2:
        pending_sales = [s for s in sales if s.get('payment_status') != 'Paid']
        if pending_sales:
            sale_options = ["None"] + [f"{s['contract_date']} - €{s['total_revenue']:.2f}" for s in pending_sales]
            related_sales = st.multiselect("Related Sales (for settlement)", options=sale_options[1:])
        else:
            related_sales = []
            st.info("No pending sales to link")
        
        notes = st.text_area("Notes", key="single_recv_notes", placeholder="e.g., Settlement for gas days Nov 1-3")
    
    if st.button("Record Payment", type="primary", key="add_payment"):
        new_payment = {
            "id": generate_id(),
            "payment_date": str(payment_date),
            "amount_eur": amount,
            "buyer": buyer,
            "related_sales_dates": related_sales,
            "notes": notes
        }
        payments.append(new_payment)
        save_payments_received(payments)
        
        if related_sales:
            for sale_ref in related_sales:
                for sale in sales:
                    if f"{sale['contract_date']} - €{sale['total_revenue']:.2f}" == sale_ref:
                        sale['payment_status'] = 'Paid'
            save_sales(sales)
        
        st.success("Payment recorded successfully!")
        st.rerun()

with tab2:
    st.subheader("Bulk Upload Payments")
    st.markdown("Upload a CSV or Excel file with payment data")
    
    with st.expander("📋 Required Columns Format"):
        st.markdown("""
        Your file should contain the following columns:
        - `payment_date` - Date payment received (YYYY-MM-DD)
        - `amount_eur` - Amount received in EUR
        - `buyer` - Buyer name
        - `notes` - Optional notes about the payment
        """)
        
        sample_data = pd.DataFrame({
            'payment_date': ['2024-11-03'],
            'amount_eur': [11200],
            'buyer': ['Keler'],
            'notes': ['Settlement for Nov 1-2']
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
                    new_payment = {
                        "id": generate_id(),
                        "payment_date": str(row.get('payment_date', '')),
                        "amount_eur": float(row.get('amount_eur', 0)),
                        "buyer": str(row.get('buyer', settings['buyers'][0])),
                        "related_sales_dates": [],
                        "notes": str(row.get('notes', ''))
                    }
                    payments.append(new_payment)
                    count += 1
                
                save_payments_received(payments)
                st.success(f"Successfully imported {count} payments!")
                st.rerun()
        except Exception as e:
            st.error(f"Error reading file: {str(e)}")

with tab3:
    st.subheader("All Payments Received")
    
    df = payments_to_df(payments)
    
    if not df.empty:
        col1, col2 = st.columns(2)
        with col1:
            filter_buyer = st.multiselect("Filter by Buyer", options=df['buyer'].unique().tolist())
        with col2:
            pass
        
        filtered_df = df.copy()
        if filter_buyer:
            filtered_df = filtered_df[filtered_df['buyer'].isin(filter_buyer)]
        
        st.dataframe(filtered_df, use_container_width=True, hide_index=True)
        
        csv = filtered_df.to_csv(index=False)
        st.download_button("Export to CSV", csv, "payments_export.csv", "text/csv")
        
        st.markdown("---")
        st.subheader("Delete Payment")
        if len(payments) > 0:
            payment_options = [f"{p['payment_date']} - {p['buyer']} - €{p['amount_eur']}" for p in payments]
            selected_payment = st.selectbox("Select payment to delete", options=payment_options)
            if st.button("Delete Selected", type="secondary"):
                idx = payment_options.index(selected_payment)
                payments.pop(idx)
                save_payments_received(payments)
                st.success("Payment deleted!")
                st.rerun()
    else:
        st.info("No payments recorded yet. Record your first payment above!")

st.markdown("---")
st.subheader("📊 Payment Analysis by Buyer")

if not payments_df.empty:
    buyer_summary = payments_df.groupby('buyer').agg({
        'amount_eur': ['sum', 'count']
    }).reset_index()
    buyer_summary.columns = ['Buyer', 'Total Received (EUR)', 'Number of Payments']
    st.dataframe(buyer_summary, use_container_width=True, hide_index=True)
