import streamlit as st
from database import get_settings, add_supplier, add_buyer, add_payment_method, delete_supplier, delete_buyer, delete_payment_method

st.set_page_config(page_title="Settings", page_icon="⚙️", layout="wide")

try:
    with open('style.css') as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
except:
    pass

st.title("⚙️ Settings")
st.markdown("Manage suppliers, buyers, and payment methods")

settings = get_settings()

col1, col2 = st.columns(2)

with col1:
    st.subheader("👥 Suppliers")
    st.markdown("Manage the list of gas suppliers")
    
    suppliers = settings.get("suppliers", [])
    
    for i, supplier in enumerate(suppliers):
        col_a, col_b = st.columns([3, 1])
        with col_a:
            st.text(supplier)
        with col_b:
            if st.button("🗑️", key=f"del_supplier_{i}"):
                delete_supplier(supplier)
                st.rerun()
    
    new_supplier = st.text_input("Add new supplier", key="new_supplier")
    if st.button("Add Supplier", type="primary", key="add_supplier_btn"):
        if new_supplier and new_supplier not in suppliers:
            add_supplier(new_supplier)
            st.success(f"Added supplier: {new_supplier}")
            st.rerun()
        elif new_supplier in suppliers:
            st.warning("Supplier already exists")
    
    st.markdown("---")
    
    st.subheader("💳 Payment Methods")
    st.markdown("Manage payment methods for supplier transactions")
    
    payment_methods = settings.get("payment_methods", [])
    
    for i, method in enumerate(payment_methods):
        col_a, col_b = st.columns([3, 1])
        with col_a:
            st.text(method)
        with col_b:
            if st.button("🗑️", key=f"del_method_{i}"):
                delete_payment_method(method)
                st.rerun()
    
    new_method = st.text_input("Add new payment method", key="new_method")
    if st.button("Add Payment Method", type="primary", key="add_method_btn"):
        if new_method and new_method not in payment_methods:
            add_payment_method(new_method)
            st.success(f"Added payment method: {new_method}")
            st.rerun()
        elif new_method in payment_methods:
            st.warning("Payment method already exists")

with col2:
    st.subheader("🏢 Buyers")
    st.markdown("Manage the list of gas buyers")
    
    buyers = settings.get("buyers", [])
    
    for i, buyer in enumerate(buyers):
        col_a, col_b = st.columns([3, 1])
        with col_a:
            st.text(buyer)
        with col_b:
            if st.button("🗑️", key=f"del_buyer_{i}"):
                delete_buyer(buyer)
                st.rerun()
    
    new_buyer = st.text_input("Add new buyer", key="new_buyer")
    if st.button("Add Buyer", type="primary", key="add_buyer_btn"):
        if new_buyer and new_buyer not in buyers:
            add_buyer(new_buyer)
            st.success(f"Added buyer: {new_buyer}")
            st.rerun()
        elif new_buyer in buyers:
            st.warning("Buyer already exists")

st.markdown("---")

st.subheader("📋 Current Configuration Summary")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Suppliers", len(settings.get("suppliers", [])))
with col2:
    st.metric("Payment Methods", len(settings.get("payment_methods", [])))
with col3:
    st.metric("Buyers", len(settings.get("buyers", [])))

st.markdown("---")

st.subheader("📊 Database Info")
st.info("Data is now stored in PostgreSQL database for better reliability and cross-referencing.")
