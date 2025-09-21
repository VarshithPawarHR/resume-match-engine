import uvicorn
from fastapi import FastAPI
from Api import routes as api_routes

app = FastAPI()

app.include_router(api_routes.router)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
