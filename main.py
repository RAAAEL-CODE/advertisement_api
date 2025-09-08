from fastapi import FastAPI

app = FastAPI()


# Home page
@app.get("/")
def read_root():
    return {"message": "Welcome to RAAAEL Advertisement API"}
