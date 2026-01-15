import streamlit as st
from database import get_settings, update_settings
from components import load_material_icons, page_header, section_header, setup_page
from auth import require_auth

st.set_page_config(
    page_title="Mix Gas Group | Settings",
    page_icon="https://slelguoygbfzlpylpxfs.supabase.co/storage/v1/render/image/public/project-uploads/704afe63-0b4a-4050-803e-5116d1754a58/Untitled-Project-1768468114127.png?width=8000&height=8000&resize=contain",
    layout="wide"
)

setup_page()
require_auth()

try:
    with open('style.css') as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
except:
    pass

load_material_icons()

page_header("Settings", "Manage suppliers, buyers, and payment methods")

settings = get_settings()

col1, col2, col3 = st.columns(3)

with col1:
    metric_card("business", "Suppliers", str(len(settings.get("suppliers", []))), "blue")
with col2:
    metric_card("credit_card", "Payment Methods", str(len(settings.get("payment_methods", []))), "green")
with col3:
    metric_card("groups", "Buyers", str(len(settings.get("buyers", []))), "orange")

st.markdown("<div style='height: 2rem;'></div>", unsafe_allow_html=True)

col1, col2 = st.columns(2)

with col1:
    section_header("business", "Suppliers")

    suppliers = settings.get("suppliers", [])

    st.markdown("""
        <div style="
            background: rgb(59, 130, 246);
            border: 1px solid rgb(59, 130, 246);
            border-radius: 12px;
            padding: 0.1rem;
            margin-bottom: 1rem;
        ">
    """, unsafe_allow_html=True)

    for i, supplier in enumerate(suppliers):
        col_a, col_b = st.columns([4, 1])
        with col_a:
            st.markdown(f"""
                <div style="padding: 0.5rem 0; display: flex; align-items: center; gap: 0.5rem;">
                    <span class="material-icons-round" style="color: #3b82f6; font-size: 18px;">store</span>
                    <span style="font-weight: 500;">{supplier}</span>
                </div>
            """, unsafe_allow_html=True)
        with col_b:
            if st.button("Delete", key=f"del_supplier_{i}"):
                delete_supplier(supplier)
                st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

    new_supplier = st.text_input("Add new supplier", key="new_supplier", placeholder="Enter supplier name")
    if st.button("Add Supplier", type="primary", key="add_supplier_btn"):
        if new_supplier and new_supplier not in suppliers:
            add_supplier(new_supplier)
            st.success(f"Added supplier: {new_supplier}")
            st.rerun()
        elif new_supplier in suppliers:
            st.warning("Supplier already exists")

    st.markdown("<div style='height: 2rem;'></div>", unsafe_allow_html=True)

    section_header("credit_card", "Payment Methods")

    payment_methods = settings.get("payment_methods", [])

    st.markdown("""
        <div style="
            background: rgb(59, 130, 246);
            border: 1px solid rgb(59, 130, 246);
            border-radius: 12px;
            padding: 0.1rem;
            margin-bottom: 1rem;
        ">
    """, unsafe_allow_html=True)

    for i, method in enumerate(payment_methods):
        col_a, col_b = st.columns([4, 1])
        with col_a:
            st.markdown(f"""
                <div style="padding: 0.5rem 0; display: flex; align-items: center; gap: 0.5rem;">
                    <span class="material-icons-round" style="color: #10b981; font-size: 18px;">account_balance</span>
                    <span style="font-weight: 500;">{method}</span>
                </div>
            """, unsafe_allow_html=True)
        with col_b:
            if st.button("Delete", key=f"del_method_{i}"):
                delete_payment_method(method)
                st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

    new_method = st.text_input("Add new payment method", key="new_method", placeholder="Enter payment method")
    if st.button("Add Payment Method", type="primary", key="add_method_btn"):
        if new_method and new_method not in payment_methods:
            add_payment_method(new_method)
            st.success(f"Added payment method: {new_method}")
            st.rerun()
        elif new_method in payment_methods:
            st.warning("Payment method already exists")

with col2:
    section_header("groups", "Buyers")

    buyers = settings.get("buyers", [])

    st.markdown("""
        <div style="
            background: rgb(59, 130, 246);
            border: 1px solid rgb(59, 130, 246);
            border-radius: 12px;
            padding: 0.1rem;
            margin-bottom: 1rem;
        ">
    """, unsafe_allow_html=True)

    for i, buyer in enumerate(buyers):
        col_a, col_b = st.columns([4, 1])
        with col_a:
            st.markdown(f"""
                <div style="padding: 0.5rem 0; display: flex; align-items: center; gap: 0.5rem;">
                    <span class="material-icons-round" style="color: #f59e0b; font-size: 18px;">person</span>
                    <span style="font-weight: 500;">{buyer}</span>
                </div>
            """, unsafe_allow_html=True)
        with col_b:
            if st.button("Delete", key=f"del_buyer_{i}"):
                delete_buyer(buyer)
                st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

    new_buyer = st.text_input("Add new buyer", key="new_buyer", placeholder="Enter buyer name")
    if st.button("Add Buyer", type="primary", key="add_buyer_btn"):
        if new_buyer and new_buyer not in buyers:
            add_buyer(new_buyer)
            st.success(f"Added buyer: {new_buyer}")
            st.rerun()
        elif new_buyer in buyers:
            st.warning("Buyer already exists")

st.markdown("<div style='height: 2rem;'></div>", unsafe_allow_html=True)

section_header("info", "Database Information")

st.markdown("""
    <div style="
        background: rgba(59, 130, 246, 0.1);
        border: 1px solid rgba(59, 130, 246, 0.2);
        border-radius: 12px;
        padding: 1.25rem;
        display: flex;
        align-items: center;
        gap: 1rem;
    ">
        <span class="material-icons-round" style="color: #3b82f6; font-size: 24px;">cloud_done</span>
        <div>
            <p style="margin: 0; font-weight: 600; color: #1e293b;">PostgreSQL Database</p>
            <p style="margin: 0.25rem 0 0 0; font-size: 0.875rem; color: #64748b;">Data is stored in PostgreSQL for better reliability and cross-referencing.</p>
        </div>
    </div>
""", unsafe_allow_html=True)
