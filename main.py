import os
from fastapi import FastAPI
import crawl
from fastapi_utilities import repeat_at
import pandas as pd
from fastapi.middleware.cors import CORSMiddleware
import logging
from datetime import datetime, timedelta
from fastapi.responses import RedirectResponse

app = FastAPI()


@app.get('/')
async def root_redirection():
    return RedirectResponse("/docs")


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
    open("user_data.csv", 'r')
    open("organization_data.csv", 'r')
    open("problem_count_by_level.csv", 'r')
    open("problem_count_by_tag.csv", 'r')
except FileNotFoundError:
    crawl.main()
    while True:
        break  # TODO: delete(disable retry)
        try:
            crawl.main()
            break
        except Exception as e:
            logger.error(e)
            logger.info("retrying...")  # pd.read_csv("user_data.csv", index_col=0)
    # pd.read_csv("organization_data.csv")


async def get_user_dataFrame() -> pd.DataFrame:
    return pd.read_csv("user_data.csv").fillna('null')


async def get_organization_dataFrame() -> pd.DataFrame:
    return pd.read_csv("organization_data.csv")


@app.on_event("startup")
@repeat_at(cron="0 0 * * *", raise_exceptions=True, logger=logging.getLogger(__name__))
def sync():
    global updated_at

    logger.info("syncing organization_data")
    while True:
        try:
            crawl.main()
            break
        except Exception as e:
            logger.error(e)
            logger.info("retrying...")

    updated_at = datetime.strptime(open("updated_at.txt", "r").read(), "%Y-%m-%d %H:%M:%S")
    user_data = pd.read_csv("user_data.csv", index_col=0)
    organization_data = pd.read_csv("organization_data.csv")
    problem_by_level = pd.read_csv("problem_count_by_level.csv")
    problem_by_tag = pd.read_csv("problem_count_by_tag.csv")

    os.makedirs("./history", exist_ok=True)

    user_data.to_csv(f'./history/user_data_{(datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")}.csv',
                     index=False)
    organization_data.to_csv(
            f'./history/organization_data_{(datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")}.csv',
            index=False)
    problem_by_level.to_csv(
            f'./history/problem_count_by_level_{(datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")}.csv',
            index=False)
    problem_by_tag.to_csv(
            f'./history/problem_count_by_tag_{(datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")}.csv',
            index=False)


@app.get("/organization")
async def get_organization_data() -> dict[str, dict]:
    organization_data = await get_organization_dataFrame()
    return {"organization_data": organization_data.to_dict(orient="records")[0]}


@app.get("/updated")
async def get_updated_time() -> datetime:
    return updated_at


@app.get("/user")
async def get_user_data() -> dict[str, list]:
    user_data = await get_user_dataFrame()
    return {"user_data": user_data.to_dict(orient="records")}


@app.get("/problem/level")
async def get_problem_list(level_id: int = None) -> dict[str, list]:
    problem_by_level = pd.read_csv("problem_count_by_level.csv")
    if level_id:
        return {"problem_list": problem_by_level[problem_by_level['level'] == level_id].to_dict(orient="records")}
    else:
        return {"problem_list": problem_by_level.to_dict(orient="records")}


@app.get("/problem/tag")
async def get_problem_tag(tag_id: int = None) -> dict[str, list]:
    problem_by_tag = pd.read_csv("problem_count_by_tag.csv")
    if tag_id:
        return {"problem_list": problem_by_tag[problem_by_tag['tag_id'] == tag_id].to_dict(orient="records")}
    else:
        return {"problem_tag": problem_by_tag.to_dict(orient="records")}
