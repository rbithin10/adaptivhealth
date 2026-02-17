"""Minimal test to see if uvicorn starts at all."""
from fastapi import FastAPI
app = FastAPI()

@app.get("/")
async def root():
    return {"msg": "hello"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8090)
