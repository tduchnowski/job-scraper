from fastapi import FastAPI, Request

app = FastAPI()


@app.post("/webhook")
async def webhook(request: Request):
    """
    Telegram bot updates
    """
    return {"ok": True}


@app.post("/scrape")
async def scrape_jobs():
    """
    Triggers scraping of job boards and updating DB with new jobs
    """
    return {"ok": True}


@app.post("/dispatch")
async def dispatch_jobs():
    """
    Triggers sending new jobs to users
    """
    return {"ok": True}
