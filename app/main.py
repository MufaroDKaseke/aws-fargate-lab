from fastapi import FastAPI
import uvicorn

app = FastAPI()


@app.get("/")
def read_root():
	return {"message": "FastAPI app is running"}


@app.get("/health")
def health_check():
	return {"status": "ok"}


@app.get("/compute")
def compute(a: float, b: float):
	return {"a": a, "b": b, "result": a + b}

if __name__ == "__main__":
	uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)