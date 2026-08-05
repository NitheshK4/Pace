from fastapi import FastAPI
from pace import PaceClient

app = FastAPI(title="Pace FastAPI Example")

pace = PaceClient(api_key="pace_demo_fastapi_key", endpoint="http://localhost:8000")

@app.get("/")
def read_root():
    return {"message": "Pace telemetry active"}

@app.get("/health")
def health():
    return {"status": "ok"}
