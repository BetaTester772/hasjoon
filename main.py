from operator import index

from fastapi import FastAPI
import crawl
from fastapi_utilities import repeat_at
import pandas as pd
from fastapi.middleware.cors import CORSMiddleware
import logging
from datetime import datetime, timedelta

app = FastAPI()

origins = ["*"]  # TODO: change to frontend url

app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

try:
    updated_at: datetime = datetime.strptime(open("updated_at.txt", "r").read(), "%Y-%m-%d %H:%M:%S")
    if updated_at < datetime.now() - timedelta(days=1):
        raise FileNotFoundError
    user_data: pd.DataFrame = pd.read_csv("user_data.csv", index_col=0)
    organization_data: pd.DataFrame = pd.read_csv("organization_data.csv")
except FileNotFoundError:
    logger.info("data syncing")
    crawl.main()
    updated_at: datetime = datetime.strptime(open("updated_at.txt", "r").read(), "%Y-%m-%d %H:%M:%S")
    user_data: pd.DataFrame = pd.read_csv("user_data.csv", index_col=0)
    organization_data: pd.DataFrame = pd.read_csv("organization_data.csv")


@repeat_at(cron="0 0 * * *")
def sync():
    global user_data, organization_data, updated_at

    logger.info("syncing organization_data")

    crawl.main()
    updated_at = datetime.strptime(open("updated_at.txt", "r").read(), "%Y-%m-%d %H:%M:%S")
    user_data = pd.read_csv("user_data.csv", index_col=0)
    organization_data = pd.read_csv("organization_data.csv")

    user_data.to_csv(f'user_data_{(datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")}.csv', index=False)
    organization_data.to_csv(f'organization_data_{(datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")}.csv',
                             index=False)


@app.get("/organization")
async def get_organization_data() -> dict[str, dict]:
    return {"organization_data": organization_data.to_dict(orient="records")[0]}


@app.get("/updated")
async def get_updated_time() -> datetime:
    return updated_at


@app.get("/user")
async def get_user_data() -> dict[str, list]:
    return {"user_data": user_data.to_dict(orient="records")}
