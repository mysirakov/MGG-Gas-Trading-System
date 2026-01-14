import streamlit as st
import csv
import io
from datetime import datetime, date
from database import (
    get_payments_received, add_payment_received, delete_payment, get_settings, get_sales,
    payments_to_df, sales_to_df, get_unpaid_sales, get_dashboard_metrics
)
from components import load_material_icons, page_header, metric_card, section_header, empty_state

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
keler_purchase_cost = metrics.get('keler_purchase_cost', 0)
outstanding = metrics['outstanding_receivables']
unallocated = total_received - total_allocated

col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    metric_card("attach_money", "Total Revenue", f"€{total_revenue:,.0f}", "blue")
with col2:
    metric_card("check_circle", "Received", f"€{total_received:,.0f}", "green")
with col3:
    metric_card("swap_horiz", "Keler Offset", f"€{keler_purchase_cost:,.0f}", "purple")
with col4:
    metric_card("receipt_long", "Outstanding", f"€{outstanding:,.0f}", "orange")
with col5:
    metric_card("account_balance", "Unallocated", f"€{max(0, unallocated):,.0f}", "blue")

st.markdown("<div style='height: 1.5rem;'></div>", unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["View Payments", "Record Payment", "Bulk Upload"])

with tab1:
    df = payments_to_df(payments)

    if df:
        col1, col2 = st.columns(2)
        with col1:
            buyers_list = sorted(list(set(row.get('buyer') for row in df if row.get('buyer'))))
            filter_buyer = st.multiselect("Filter by Buyer", options=buyers_list)

        filtered_df = df
        if filter_buyer:
            filtered_df = [row for row in df if row.get('buyer') in filter_buyer]

        display_cols = ['payment_date', 'buyer', 'amount_eur', 'allocated_amount', 'notes']
        
        display_filtered = []
        for row in filtered_df:
            new_row = {}
            for col in display_cols:
                if col in row:
                    val = row[col]
                    if col == 'payment_date' and val:
                        if isinstance(val, str):
                            try:
                                val = datetime.strptime(val, '%Y-%m-%d').strftime('%b %d, %Y')
                            except:
                                pass
                        elif hasattr(val, 'strftime'):
                            val = val.strftime('%b %d, %Y')
                    new_row[col] = val
            
            # Add derived columns
            amt = float(new_row.get('amount_eur', 0))
            alloc = float(new_row.get('allocated_amount', amt))
            new_row['unallocated'] = amt - alloc
            display_filtered.append(new_row)
            
        st.dataframe(display_filtered, width="stretch", hide_index=True, height=300)

        col1, col2 = st.columns([1, 4])
        with col1:
            output = io.StringIO()
            if filtered_df:
                writer = csv.DictWriter(output, fieldnames=filtered_df[0].keys())
                writer.writeheader()
                writer.writerows(filtered_df)
            csv_data = output.getvalue()
            st.download_button("Export", csv_data, "payments_export.csv", "text/csv")

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
        empty_state("payments", "No payments recorded yet")

    st.markdown("<div style='height: 2rem;'></div>", unsafe_allow_html=True)
    
    section_header("assignment", "Sales Payment Status")

    if sales_df:
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Outstanding Sales**")
            unpaid_sales = get_unpaid_sales()
            if unpaid_sales:
                for sale in unpaid_sales[:10]:
                    owed = float(sale.get('outstanding', 0))
                    paid = float(sale.get('amount_paid', 0))
                    st.markdown(f"""
                        <div class="list-item-card">
                            <div class="list-item-header warning">
                                <span class="material-icons-round">receipt_long</span>
                                <span class="list-item-title">{sale['contract_date']} - {sale.get('buyer', 'Unknown')}</span>
                            </div>
                            <div class="list-item-details">
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
            if payments_df:
                buyer_sum = {}
                for row in payments_df:
                    b = row.get('buyer', 'Unknown')
                    if b not in buyer_sum:
                        buyer_sum[b] = 0.0
                    buyer_sum[b] += float(row.get('amount_eur', 0))
                
                buyer_summary_data = [{'Buyer': b, 'Total Received (EUR)': amt} for b, amt in buyer_sum.items()]
                st.dataframe(buyer_summary_data, width="stretch", hide_index=True)
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
                    <div class="list-item-card">
                        <div class="list-item-header primary">
                            <span class="material-icons-round">receipt</span>
                            <span class="list-item-title">{sale['contract_date']}</span>
                        </div>
                        <div class="list-item-details">
                            Owed: €{sale_owed:,.2f}
                        </div>
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
            cls = "success" if status == "Full" else "warning"
            st.markdown(f"""
                <div class="list-item-card">
                    <div class="list-item-header {cls}">
                        <span class="material-icons-round">{icon}</span>
                        <span class="list-item-title">{alloc['contract_date']}</span>
                    </div>
                    <div class="list-item-details">
                        Allocated: €{alloc['amount']:,.2f} ({status})
                    </div>
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

        sample_data = [
            {
                'payment_date': '03/11/2024',
                'amount_eur': 11200,
                'buyer': 'Keler',
                'notes': 'Settlement for Nov 1-2'
            }
        ]
        st.dataframe(sample_data)

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=sample_data[0].keys())
        writer.writeheader()
        writer.writerows(sample_data)
        csv_data = output.getvalue()
        st.download_button("Download Template CSV", csv_data, "payments_template.csv", "text/csv")

    uploaded_file = st.file_uploader("Upload Payments File", type=['csv'], key="bulk_payments")

    if uploaded_file:
        try:
            content = uploaded_file.read().decode('utf-8')
            reader = csv.DictReader(io.StringIO(content))
            data = list(reader)

            st.markdown("##### Preview of Uploaded Data")
            st.dataframe(data, width="stretch")

            if st.button("Import & Auto-Allocate All", type="primary", key="import_payments"):
                count = 0
                for row in data:
                    payment_date_str = str(row.get('payment_date', ''))
                    payment_date = date.today()
                    for fmt in ['%d/%m/%Y', '%Y-%m-%d', '%m/%d/%Y']:
                        try:
                            payment_date = datetime.strptime(payment_date_str, fmt).date()
                            break
                        except:
                            continue
                    
                    add_payment_received(
                        payment_date,
                        str(row.get('buyer', settings['buyers'][0] if settings['buyers'] else 'Unknown')),
                        float(row.get('amount_eur', 0) or 0),
                        str(row.get('notes', ''))
                    )
                    count += 1

                st.success(f"Imported {count} payments with auto-allocation!")
                st.rerun()
        except Exception as e:
            st.error(f"Error reading file: {str(e)}")
