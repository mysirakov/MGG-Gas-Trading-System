import streamlit as st
import pandas as pd
from datetime import datetime, date
from database import (
    get_payments_received, add_payment_received, delete_payment, get_settings, get_sales,
    payments_to_df, sales_to_df, get_unpaid_sales, get_dashboard_metrics
)
from components import load_material_icons, page_header, metric_card, section_header

st.set_page_config(page_title="Payments", page_icon="💳", layout="wide")

try:
    with open('style.css') as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
except:
    pass

load_material_icons()

page_header("Payments", "Track payments received from buyers and reconcile outstanding balances")

settings = get_settings()
payments = get_payments_received()
sales = get_sales()
metrics = get_dashboard_metrics()

sales_df = sales_to_df(sales)
payments_df = payments_to_df(payments)

total_revenue = metrics['total_revenue']
total_received = metrics['payments_received']
total_allocated = metrics['total_allocated']
outstanding = metrics['outstanding_receivables']
unallocated = total_received - total_allocated

col1, col2, col3, col4 = st.columns(4)
with col1:
    metric_card("attach_money", "Total Revenue", f"€{total_revenue:,.0f}", "blue")
with col2:
    metric_card("check_circle", "Received", f"€{total_received:,.0f}", "green")
with col3:
    metric_card("receipt_long", "Outstanding", f"€{outstanding:,.0f}", "orange")
with col4:
    metric_card("account_balance", "Unallocated", f"€{max(0, unallocated):,.0f}", "purple")

st.markdown("<div style='height: 1.5rem;'></div>", unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["View Payments", "Record Payment", "Bulk Upload"])

with tab1:
    df = payments_to_df(payments)

    if not df.empty:
        col1, col2 = st.columns(2)
        with col1:
            if 'buyer' in df.columns:
                filter_buyer = st.multiselect("Filter by Buyer", options=df['buyer'].dropna().unique().tolist())
            else:
                filter_buyer = []

        filtered_df = df.copy()
        if filter_buyer:
            filtered_df = filtered_df[filtered_df['buyer'].isin(filter_buyer)]

        display_cols = ['payment_date', 'buyer', 'amount_eur', 'allocated_amount', 'notes']
        available_cols = [c for c in display_cols if c in filtered_df.columns]
        
        display_filtered = filtered_df[available_cols].copy()
        if 'payment_date' in display_filtered.columns:
            display_filtered['payment_date'] = pd.to_datetime(display_filtered['payment_date']).dt.strftime('%b %d, %Y')
        if 'allocated_amount' not in display_filtered.columns:
            display_filtered['allocated_amount'] = display_filtered['amount_eur']
        display_filtered['unallocated'] = display_filtered['amount_eur'] - display_filtered['allocated_amount']
        
        st.dataframe(display_filtered, use_container_width=True, hide_index=True, height=300)

        col1, col2 = st.columns([1, 4])
        with col1:
            csv = filtered_df.to_csv(index=False)
            st.download_button("Export", csv, "payments_export.csv", "text/csv")

        st.markdown("<div style='height: 2rem;'></div>", unsafe_allow_html=True)
        
        section_header("delete", "Delete Payment")
        if len(payments) > 0:
            payment_options = {f"{p['payment_date']} - {p.get('buyer', 'N/A')} - €{float(p['amount_eur']):.2f}": p['id'] for p in payments}
            col1, col2 = st.columns([3, 1])
            with col1:
                selected_payment = st.selectbox("Select payment to delete", options=list(payment_options.keys()), label_visibility="collapsed")
            with col2:
                if st.button("Delete", type="secondary"):
                    payment_id = payment_options[selected_payment]
                    delete_payment(payment_id)
                    st.success("Payment deleted!")
                    st.rerun()
    else:
        st.markdown("""
            <div style="
                background: rgba(255, 255, 255, 0.7);
                border: 1px solid rgba(255, 255, 255, 0.5);
                border-radius: 16px;
                padding: 4rem 2rem;
                text-align: center;
                color: #64748b;
                backdrop-filter: blur(12px);
            ">
                <span class="material-icons-round" style="font-size: 56px; opacity: 0.4; color: #3b82f6;">payments</span>
                <p style="margin: 1.5rem 0 0 0; font-size: 1.1rem; font-weight: 500;">No payments recorded yet</p>
                <p style="margin: 0.5rem 0 0 0; font-size: 0.9rem; opacity: 0.7;">Record your first payment in the 'Record Payment' tab!</p>
            </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height: 2rem;'></div>", unsafe_allow_html=True)
    
    section_header("assignment", "Sales Payment Status")

    if not sales_df.empty:
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Outstanding Sales**")
            unpaid_sales = get_unpaid_sales()
            if unpaid_sales:
                for sale in unpaid_sales[:10]:
                    owed = float(sale.get('outstanding', 0))
                    paid = float(sale.get('amount_paid', 0))
                    st.markdown(f"""
                        <div style="padding: 0.75rem; background: rgba(255, 255, 255, 0.5); border-radius: 8px; margin-bottom: 0.5rem;">
                            <div style="display: flex; align-items: center; gap: 0.5rem;">
                                <span class="material-icons-round" style="color: #f59e0b; font-size: 18px;">receipt_long</span>
                                <span style="font-weight: 500;">{sale['contract_date']} - {sale.get('buyer', 'Unknown')}</span>
                            </div>
                            <div style="font-size: 0.85rem; color: #64748b; margin-top: 0.25rem;">
                                Revenue: €{float(sale['total_revenue']):,.2f} | Paid: €{paid:,.2f} | Owed: €{owed:,.2f}
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
                if len(unpaid_sales) > 10:
                    st.caption(f"...and {len(unpaid_sales) - 10} more")
            else:
                st.success("All sales fully paid!")

        with col2:
            st.markdown("**Payment Summary by Buyer**")
            if not payments_df.empty and 'buyer' in payments_df.columns:
                buyer_summary = payments_df.groupby('buyer')['amount_eur'].sum().reset_index()
                buyer_summary.columns = ['Buyer', 'Total Received (EUR)']
                st.dataframe(buyer_summary, use_container_width=True, hide_index=True)
            else:
                st.info("No payment data yet")

with tab2:
    section_header("add_card", "Record Payment Received")

    col1, col2 = st.columns(2)

    with col1:
        payment_date = st.date_input("Payment Received Date", value=date.today(), key="single_payment_recv_date")
        amount = st.number_input("Amount Received (EUR)", min_value=0.0, step=100.0, key="single_recv_amount")
        buyer = st.selectbox("Buyer", options=settings.get("buyers", ["Keler"]), key="single_recv_buyer")
        notes = st.text_area("Notes", key="single_recv_notes", placeholder="e.g., Settlement for gas days Nov 1-3")

    with col2:
        unpaid_sales = get_unpaid_sales(buyer)
        
        if unpaid_sales and amount > 0:
            st.markdown("**Outstanding Sales (oldest first)**")

            for sale in unpaid_sales[:5]:
                sale_owed = float(sale.get('outstanding', 0))
                st.markdown(f"""
                    <div style="padding: 0.5rem; background: rgba(255, 255, 255, 0.5); border-radius: 6px; margin-bottom: 0.5rem; font-size: 0.9rem;">
                        <span class="material-icons-round" style="color: #3b82f6; font-size: 16px; vertical-align: middle;">receipt</span>
                        {sale['contract_date']} - Owed: €{sale_owed:,.2f}
                    </div>
                """, unsafe_allow_html=True)

            if len(unpaid_sales) > 5:
                st.caption(f"...and {len(unpaid_sales) - 5} more outstanding sales")
        elif not unpaid_sales:
            st.success("No outstanding sales for this buyer!")
        else:
            st.info("Enter payment amount to see allocation preview")

    if amount > 0 and unpaid_sales:
        allocation_preview = []
        remaining = amount

        for sale in unpaid_sales:
            sale_owed = float(sale.get('outstanding', 0))
            if sale_owed > 0 and remaining > 0:
                alloc_amount = min(remaining, sale_owed)
                allocation_preview.append({
                    'contract_date': str(sale['contract_date']),
                    'amount': alloc_amount,
                    'owed': sale_owed
                })
                remaining -= alloc_amount

        st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)
        st.markdown("**Auto-allocation Preview (oldest first)**")

        for alloc in allocation_preview:
            status = "Full" if alloc['amount'] >= alloc['owed'] else "Partial"
            icon = "check_circle" if status == "Full" else "pending"
            color = "#10b981" if status == "Full" else "#f59e0b"
            st.markdown(f"""
                <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.25rem;">
                    <span class="material-icons-round" style="color: {color}; font-size: 18px;">{icon}</span>
                    <span>{alloc['contract_date']}: €{alloc['amount']:,.2f} ({status})</span>
                </div>
            """, unsafe_allow_html=True)

        total_to_allocate = sum(a['amount'] for a in allocation_preview)
        if remaining > 0:
            st.warning(f"€{remaining:,.2f} will remain unallocated after clearing oldest balances")
        else:
            st.success(f"€{total_to_allocate:,.2f} will be fully allocated to {len(allocation_preview)} sale(s)")

    st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)
    
    if st.button("Record Payment & Auto-Allocate", type="primary", key="add_payment"):
        if amount <= 0:
            st.error("Please enter a payment amount")
        else:
            add_payment_received(payment_date, buyer, amount, notes)
            st.success("Payment recorded and allocated!")
            st.rerun()

with tab3:
    section_header("upload_file", "Bulk Upload Payments")

    with st.expander("Required Columns Format"):
        st.markdown("""
        Your file should contain the following columns:
        - `payment_date` - Date payment received (DD/MM/YYYY)
        - `amount_eur` - Amount received in EUR
        - `buyer` - Buyer name
        - `notes` - Optional notes about the payment

        Payments will be automatically allocated to oldest outstanding sales first (FIFO).
        """)

        sample_data = pd.DataFrame({
            'payment_date': ['03/11/2024'],
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

            st.markdown("##### Preview of Uploaded Data")
            st.dataframe(df, use_container_width=True)

            if st.button("Import & Auto-Allocate All", type="primary", key="import_payments"):
                count = 0
                for _, row in df.iterrows():
                    payment_date_str = str(row.get('payment_date', ''))
                    try:
                        payment_date = pd.to_datetime(payment_date_str, dayfirst=True).date()
                    except:
                        payment_date = date.today()
                    
                    add_payment_received(
                        payment_date,
                        str(row.get('buyer', settings['buyers'][0] if settings['buyers'] else 'Unknown')),
                        float(row.get('amount_eur', 0)),
                        str(row.get('notes', ''))
                    )
                    count += 1

                st.success(f"Imported {count} payments with auto-allocation!")
                st.rerun()
        except Exception as e:
            st.error(f"Error reading file: {str(e)}")
