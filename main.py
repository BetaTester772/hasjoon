from fastapi import FastAPI
import crawl
from fastapi_utilities import repeat_at
import pandas as pd
from fastapi.middleware.cors import CORSMiddleware
import logging
from datetime import datetime

app = FastAPI()

origins = ["*"]  # TODO: change to frontend url

app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
)

# get_logger
logger = logging.getLogger(__name__)

updated_at: datetime = datetime.now()

# check if data exists
try:
    user_data: pd.DataFrame = pd.read_csv("user_data.csv", index_col=0)
    organization_data: pd.DataFrame = pd.read_csv("organization_data.csv", index_col=0)
except FileNotFoundError:
    logger.info("data syncing")
    crawl.main()
    user_data: pd.DataFrame = pd.read_csv("user_data.csv", index_col=0)
    organization_data: pd.DataFrame = pd.read_csv("organization_data.csv", index_col=0)


@repeat_at(cron="0 0 * * *")
def sync():
    logger.info("syncing organization_data")
    global organization_data
    organization_data = crawl.get_organization_data()
    organization_data.to_csv(f'organization_data_{(datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")}.csv',
                             index=True)
    logger.info("syncing user_data")
    global user_data
    user_data = crawl.main()
    user_data.to_csv(f'user_data_{(datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")}.csv', index=True)
    logger.info("syncing done")


@app.get("/organization")
async def get_organization_data() -> dict:
    return organization_data.iloc[0].to_dict()


@app.get("/updated")
async def get_updated_time() -> datetime:
    return updated_at


@app.get("/user")
async def get_user_data() -> dict:
    user_data_dict = user_data.to_dict()
    return user_data_dict
