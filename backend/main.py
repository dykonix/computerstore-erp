from fastapi import FastAPI

from app.api.routes.auth import router as auth_router
from app.api.routes.products import router as products_router
from app.api.routes.inventory import router as inventory_router
from app.api.routes.suppliers import router as suppliers_router
from app.api.routes.categories import router as categories_router
from app.api.routes.warranties import router as warranties_router
from app.api.routes.sales import router as sales_router


app = FastAPI(title="ComputerStore ERP API")

app.include_router(auth_router)
app.include_router(products_router)
app.include_router(inventory_router)
app.include_router(suppliers_router)
app.include_router(categories_router)
app.include_router(warranties_router)
app.include_router(sales_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}