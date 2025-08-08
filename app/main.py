from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.api.stores import router as stores_router
from app.api.places import router as place_id_router
from app.api.reviews import router as reviews_router
from app.api.store_controller import router as store_router
from app.middlewares import create_middlewares

app = FastAPI(title="Naver Map Crawling API")

app.include_router(stores_router, prefix="/api")
app.include_router(reviews_router, prefix="/api")
app.include_router(place_id_router, prefix="/api")
app.include_router(store_router, prefix="/api/v2")

create_middlewares(app)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8001, reload=True)