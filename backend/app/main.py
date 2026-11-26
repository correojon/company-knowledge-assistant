from fastapi import FastAPI

app = FastAPI(title="Knowledge Assistant")

@app.get("/health")
def health():
    return {"status": "ok"}