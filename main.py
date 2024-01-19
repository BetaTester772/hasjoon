import os
from fastapi import FastAPI
import crawl
from fastapi_utilities import repeat_at
import pandas as pd
from fastapi.middleware.cors import CORSMiddleware
import logging
from datetime import datetime, timedelta
from fastapi.responses import RedirectResponse
import json

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
    open("problem_info.json", 'r')
    open("high_school_data.csv", 'r')
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
    high_school_data = pd.read_csv("high_school_data.csv")

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
    high_school_data.to_csv(
            f'./history/high_school_data_{(datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")}.csv',
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


@app.get("/problem")
async def get_problem_list(problem_id: int = None):
    with open("problem_info.json", "r") as f:
        problem_dict = json.load(f)
    if problem_id:
        return {"problem_dict": problem_dict.get(str(problem_id), None)}
    else:
        return {"problem_dict": problem_dict}


@app.get("/vs/high_school")
async def get_vs_high_school(hs_name: str):
    high_school_data = pd.read_csv("high_school_data.csv")
    rival_high_school = high_school_data[high_school_data['name'] == hs_name].to_dict(orient="records")[0]
    my_high_school = high_school_data[high_school_data['name'] == "하나고등학교"].to_dict(orient="records")[0]

    rating_diff = my_high_school['rating'] - rival_high_school['rating']
    user_count_diff = my_high_school['user_count'] - rival_high_school['user_count']
    solved_count_diff = my_high_school['solved_count'] - rival_high_school['solved_count']
    rank_diff = rival_high_school['rank'] - my_high_school['rank']

    diff = {
            "rating"      : str(rating_diff) if rating_diff > 0 else "+" + str(rating_diff),
            "user_count"  : str(user_count_diff) if user_count_diff > 0 else "+" + str(user_count_diff),
            "solved_count": str(solved_count_diff) if solved_count_diff > 0 else "+" + str(solved_count_diff),
            "rank"        : str(rank_diff) if rank_diff > 0 else "+" + str(rank_diff),
    }

    return {"opponent": rival_high_school, "us": my_high_school, "diff": diff}
