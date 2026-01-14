import os
from fastapi import FastAPI, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from datetime import datetime
from collections import defaultdict
import database

app = FastAPI()

# Database initialization
database.initialize_database_system()

# Templates configuration
templates = Jinja2Templates(directory="templates")

# Routes

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    metrics = database.get_dashboard_metrics()
    sales = database.get_sales()
    
    # Prepare chart data
    sales_by_date = defaultdict(lambda: {"revenue": 0, "profit": 0, "volume": 0})
    for sale in sales:
        date_str = str(sale['contract_date'])
        sales_by_date[date_str]["revenue"] += float(sale['total_revenue'])
        sales_by_date[date_str]["profit"] += float(sale['total_margin'])
        sales_by_date[date_str]["volume"] += float(sale['quantity_mwh'])
    
    sorted_dates = sorted(sales_by_date.keys())
    chart_data = {
        "dates": sorted_dates,
        "revenue": [sales_by_date[d]["revenue"] for d in sorted_dates],
        "profit": [sales_by_date[d]["profit"] for d in sorted_dates],
        "volume": [sales_by_date[d]["volume"] for d in sorted_dates]
    }
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "active_page": "dashboard",
        "metrics": metrics,
        "chart_data": chart_data
    })

@app.get("/sales", response_class=HTMLResponse)
async def sales_page(request: Request):
    sales = database.get_sales()
    settings = database.get_settings()
    return templates.TemplateResponse("sales.html", {
        "request": request,
        "active_page": "sales",
        "sales": sales,
        "settings": settings
    })

@app.post("/sales/add")
async def add_sale(
    contract_date: str = Form(...),
    buyer_name: str = Form(...),
    supplier_name: str = Form(None),
    quantity_mwh: float = Form(...),
    sales_price: float = Form(...),
    purchase_price: float = Form(...),
    capacity_cost: float = Form(0),
    transport_cost: float = Form(0),
    customs_cost: float = Form(0)
):
    database.add_sale(
        contract_date, buyer_name, quantity_mwh, sales_price, 
        purchase_price, capacity_cost, transport_cost, supplier_name, customs_cost
    )
    return RedirectResponse(url="/sales", status_code=303)

@app.post("/sales/delete/{sale_id}")
async def delete_sale(sale_id: int):
    database.delete_sale(sale_id)
    return RedirectResponse(url="/sales", status_code=303)

@app.get("/purchases", response_class=HTMLResponse)
async def purchases_page(request: Request):
    purchases = database.get_supplier_payments()
    settings = database.get_settings()
    return templates.TemplateResponse("purchases.html", {
        "request": request,
        "active_page": "purchases",
        "purchases": purchases,
        "settings": settings
    })

@app.post("/purchases/add")
async def add_purchase(
    payment_date: str = Form(...),
    supplier_name: str = Form(...),
    payment_method: str = Form(...),
    amount_sent: float = Form(...),
    invoice_number: str = Form(None),
    receipt_date: str = Form(None),
    amount_received: float = Form(None)
):
    database.add_supplier_payment(
        payment_date, supplier_name, payment_method, amount_sent,
        invoice_number, receipt_date, amount_received
    )
    return RedirectResponse(url="/purchases", status_code=303)

@app.post("/purchases/delete/{payment_id}")
async def delete_purchase(payment_id: int):
    database.delete_supplier_payment(payment_id)
    return RedirectResponse(url="/purchases", status_code=303)

@app.get("/payments", response_class=HTMLResponse)
async def payments_page(request: Request):
    payments = database.get_payments_received()
    settings = database.get_settings()
    return templates.TemplateResponse("payments.html", {
        "request": request,
        "active_page": "payments",
        "payments": payments,
        "settings": settings
    })

@app.post("/payments/add")
async def add_payment(
    payment_date: str = Form(...),
    buyer_name: str = Form(...),
    amount_eur: float = Form(...),
    notes: str = Form("")
):
    database.add_payment_received(payment_date, buyer_name, amount_eur, notes)
    return RedirectResponse(url="/payments", status_code=303)

@app.post("/payments/delete/{payment_id}")
async def delete_payment(payment_id: int):
    database.delete_payment(payment_id)
    return RedirectResponse(url="/payments", status_code=303)

@app.get("/balance", response_class=HTMLResponse)
async def balance_page(request: Request):
    metrics = database.get_dashboard_metrics()
    return templates.TemplateResponse("seller_balance.html", {
        "request": request,
        "active_page": "balance",
        "metrics": metrics
    })

@app.get("/analytics", response_class=HTMLResponse)
async def analytics_page(request: Request):
    metrics = database.get_dashboard_metrics()
    sales = database.get_sales()
    
    # Buyer analytics
    buyer_stats = defaultdict(lambda: {"profit": 0, "volume": 0})
    # Monthly analytics
    monthly_data = defaultdict(lambda: {"revenue": 0, "profit": 0, "volume": 0})
    
    for sale in sales:
        buyer = sale['buyer']
        buyer_stats[buyer]["profit"] += float(sale['total_margin'])
        buyer_stats[buyer]["volume"] += float(sale['quantity_mwh'])
        
        # Month string (YYYY-MM)
        if sale['contract_date']:
            month_str = sale['contract_date'].strftime('%Y-%m')
            monthly_data[month_str]["revenue"] += float(sale['total_revenue'])
            monthly_data[month_str]["profit"] += float(sale['total_margin'])
            monthly_data[month_str]["volume"] += float(sale['quantity_mwh'])
            
    buyer_data = {
        "names": list(buyer_stats.keys()),
        "profits": [buyer_stats[b]["profit"] for b in buyer_stats],
        "volumes": [buyer_stats[b]["volume"] for b in buyer_stats]
    }
    
    sorted_months = sorted(monthly_data.keys(), reverse=True)
    monthly_stats = []
    for m in sorted_months:
        monthly_stats.append({
            "month": m,
            "revenue": monthly_data[m]["revenue"],
            "profit": monthly_data[m]["profit"],
            "volume": monthly_data[m]["volume"]
        })
    
    return templates.TemplateResponse("analytics.html", {
        "request": request,
        "active_page": "analytics",
        "metrics": metrics,
        "buyer_data": buyer_data,
        "monthly_stats": monthly_stats
    })

@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    settings = database.get_settings()
    return templates.TemplateResponse("settings.html", {
        "request": request,
        "active_page": "settings",
        "settings": settings
    })

@app.post("/settings/suppliers/add")
async def add_supplier(name: str = Form(...)):
    database.add_supplier(name)
    return RedirectResponse(url="/settings", status_code=303)

@app.post("/settings/suppliers/delete")
async def delete_supplier(name: str = Form(...)):
    database.delete_supplier(name)
    return RedirectResponse(url="/settings", status_code=303)

@app.post("/settings/buyers/add")
async def add_buyer(name: str = Form(...)):
    database.add_buyer(name)
    return RedirectResponse(url="/settings", status_code=303)

@app.post("/settings/buyers/delete")
async def delete_buyer(name: str = Form(...)):
    database.delete_buyer(name)
    return RedirectResponse(url="/settings", status_code=303)

@app.post("/settings/payment_methods/add")
async def add_payment_method(name: str = Form(...)):
    database.add_payment_method(name)
    return RedirectResponse(url="/settings", status_code=303)

@app.post("/settings/payment_methods/delete")
async def delete_payment_method(name: str = Form(...)):
    database.delete_payment_method(name)
    return RedirectResponse(url="/settings", status_code=303)

@app.post("/settings/database/initialize")
async def initialize_db():
    database.initialize_database_system()
    return RedirectResponse(url="/settings", status_code=303)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
