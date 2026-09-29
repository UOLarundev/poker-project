from fastapi import FastAPI

from api.routes import games

app = FastAPI(title="Poker API")
app.include_router(games.router)
