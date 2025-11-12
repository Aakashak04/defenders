from fastapi import FastAPI, Body

app = FastAPI(title="Bank Beta Demo")


@app.get("/health")
def health():
	return {"bank": "beta", "status": "ok"}


@app.get("/accounts")
def accounts():
	return {"bank": "beta", "accounts": [{"id": "B9", "balance": 42.0}]}


@app.post("/auth/login")
def login(username: str = Body(...), password: str = Body(...)):
	return {"bank": "beta", "message": f"hello {username}"}





