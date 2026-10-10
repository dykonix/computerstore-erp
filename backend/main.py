from fastapi import FastAPI

from app.api.routes.auth import router as auth_router
from app.api.routes.products import router as products_router
from app.api.routes.inventory import router as inventory_router
from app.api.routes.suppliers import router as suppliers_router
from app.api.routes.categories import router as categories_router
from app.api.routes.warranties import router as warranties_router
from app.api.routes.sales import router as sales_router
from app.api.routes import stores
from app.api.routes import customers
from app.api.routes import promotions


app = FastAPI(title="ComputerStore ERP API")

app.include_router(auth_router, prefix="/api")
app.include_router(products_router, prefix="/api")
app.include_router(inventory_router, prefix="/api")
app.include_router(suppliers_router, prefix="/api")
app.include_router(categories_router, prefix="/api")
app.include_router(warranties_router, prefix="/api")
app.include_router(sales_router, prefix="/api")
app.include_router(stores.router, prefix="/api")
app.include_router(customers.router, prefix="/api")
app.include_router(promotions.router, prefix="/api")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}