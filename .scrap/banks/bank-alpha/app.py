from fastapi import FastAPI, Body

app = FastAPI(title="Bank Alpha Demo")


@app.get("/health")
def health():
	return {"bank": "alpha", "status": "ok"}


@app.get("/accounts")
def accounts():
	return {"bank": "alpha", "accounts": [{"id": "A1", "balance": 1000.5}]}


@app.post("/auth/login")
def login(username: str = Body(...), password: str = Body(...)):
	# demo only; do not use in production
	return {"bank": "alpha", "message": f"welcome {username}"}




