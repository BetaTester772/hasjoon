from typing import Dict

import requests
import bs4 as bs
import pandas as pd
import json
from io import StringIO  # StringIO를 추가합니다.
from datetime import datetime, timedelta


def get_user_handle_list(organization_id: int = 804) -> list:
    handle_list = []
    i = 1

    while True:
        response = requests.get(f'https://www.acmicpc.net/school/ranklist/{organization_id}/{i}',
                                headers={'User-Agent': 'Mozilla/5.0'})

        if response.status_code != 200:
            break

        html = bs.BeautifulSoup(response.text, 'html.parser')

        # 테이블에서 모든 행을 찾아냅니다.
        table = html.find('table')

        # DataFrame을 직접 생성
        df = pd.read_html(StringIO(str(table)), header=0)[0]  # StringIO로 감싸 문자열을 전달합니다.

        handle_list.extend(df['아이디'].tolist())
        i += 1

    return handle_list


def get_organization_id(name: str) -> int:
    url = "https://solved.ac/api/v3/ranking/organization"

    headers = {"Accept": "application/json"}
    i = 1
    while True:
        querystring = {"page": str(i)}

        response = requests.get(url, headers=headers, params=querystring)
        if response.status_code == 200 and name in response.text:
            break
        i += 1

    for i in response.json()['items']:
        if i['name'] == name:
            return i['organizationId']


def get_organization_info(name: str = "하나고등학교") -> dict:
    url = "https://solved.ac/api/v3/ranking/organization"

    headers = {"Accept": "application/json"}
    i = 1
    while True:
        querystring = {"page": str(i)}

        response = requests.get(url, headers=headers, params=querystring)
        if response.status_code == 200 and name in response.text:
            break
        i += 1

    for i in response.json()['items']:
        if i['name'] == name:
            data = {
                    'rank'        : i['rank'],
                    'count'       : response.json()['count'],
                    "user_count"  : i["userCount"],
                    "solved_count": i["solvedCount"],
                    "vote_count"  : i["voteCount"],
                    "name"        : i["name"],
                    "rating"      : i["rating"],
            }

    i = 1
    while True:
        querystring = {"page": str(i), "type": "high_school"}

        response = requests.get(url, headers=headers, params=querystring)
        if response.status_code == 200 and name in response.text:
            break
        i += 1

    for i in response.json()['items']:
        if i['name'] == name:
            data['rank_high_school'] = i['rank']

    return data


def get_user_info(handle: str) -> dict | None:
    url1 = f"https://www.acmicpc.net/user/{handle}"

    html = bs.BeautifulSoup(requests.get(url1, headers={'User-Agent': 'Mozilla/5.0'}).text, 'html.parser')

    rank_element = html.find('th', string='등수')

    # 등수 요소에서 등수를 추출합니다.
    rank = rank_element.find_next('td').text.strip()

    url2 = "https://solved.ac/api/v3/user/show"

    querystring = {"handle": handle}

    headers = {"Accept": "application/json"}

    response = requests.get(url2, headers=headers, params=querystring)

    if response.status_code != 200:
        return {
                'handle'          : handle,
                'solved_count'    : None,
                'vote_count'      : None,
                'class'           : None,
                'class_decoration': None,
                'tier'            : None,
                'rating'          : None,
                'coins'           : None,
                'stardusts'       : None,
                'solved_rank_all' : None,
                'boj_rank_all'    : rank,
        }

    res_dict = response.json()
    return {
            'handle'          : res_dict['handle'],
            'solved_count'    : res_dict['solvedCount'],
            'vote_count'      : res_dict['voteCount'],
            'class'           : res_dict['class'],
            'class_decoration': res_dict['classDecoration'],
            'tier'            : res_dict['tier'],
            'rating'          : res_dict['rating'],
            'coins'           : res_dict['coins'],
            'stardusts'       : res_dict['stardusts'],
            'solved_rank_all' : res_dict['rank'],
            'boj_rank_all'    : rank,
    }


def get_user_data(handle_list: list):
    df = pd.DataFrame(columns=['handle', 'solved_count', 'vote_count', 'class', 'class_decoration', 'tier', 'rating',
                               'coins', 'stardusts', 'solved_rank', 'boj_rank', 'solved_rank_all', 'boj_rank_all'])

    for i, handle in enumerate(handle_list):
        user_dict = get_user_info(handle)
        df = pd.concat([df, pd.DataFrame(user_dict, index=[i])])

    # add boj rank
    df['boj_rank'] = df.index + 1
    df = df.reset_index(drop=True)

    # solved_rank by rank
    df = df.sort_values(by='rating', ascending=False)
    df = df.reset_index(drop=True)
    for i in range(len(df)):
        if df.loc[i, 'rating'] is not None:
            if i > 0 and df.loc[i, 'rating'] == df.loc[i - 1, 'rating']:
                df.loc[i, 'solved_rank'] = df.loc[i - 1, 'solved_rank']
            else:
                df.loc[i, 'solved_rank'] = i + 1
    return df


def main() -> tuple[pd.DataFrame, dict]:
    updated_at: datetime = datetime.now()

    user_data = get_user_data(get_user_handle_list(get_organization_id("하나고등학교")))
    # print(user_data)

    organization_data = get_organization_info("하나고등학교")
    # print(organization_data)

    problem_by_level, problem_by_tag = get_organization_solved_problems_by_level_and_tag()
    # print(problem_by_level)
    # print(problem_by_tag)

    user_data.to_csv(f'user_data.csv', index=False)
    pd.DataFrame(organization_data, index=[0]).to_csv(f'organization_data.csv', index=False)
    level_problem_count = get_solvedac_problem_level_count()
    df = pd.DataFrame(columns=['level', 'count', 'solved_count'])
    idx = 0
    for level, problem_list in problem_by_level.items():
        df = pd.concat([df, pd.DataFrame(
                {'level': level, 'count': level_problem_count[level], 'solved_count': len(problem_list)},
                index=[idx])])
        idx += 1
    df.to_csv(f'problem_count_by_level.csv', index=False)

    df = pd.DataFrame(columns=['tag_id', 'ko', 'en', 'count', 'solved_count'])
    idx = 0
    for tag_id, tag_data in problem_by_tag.items():
        df = pd.concat([df, pd.DataFrame({'tag_id'      : tag_id, 'ko': tag_data['ko'], 'en': tag_data['en'],
                                          'count'       : tag_data['count'],
                                          'solved_count': tag_data['solved_count']}, index=[idx])])
        idx += 1
    df.to_csv(f'problem_count_by_tag.csv', index=False)
    with open('updated_at.txt', 'w') as f:
        f.write(updated_at.strftime("%Y-%m-%d %H:%M:%S"))

    return user_data, organization_data


def get_user_solved_problem_list(handle: str):
    url = "https://solved.ac/api/v3/search/problem"

    querystring = {"query": f"s@{handle}", "sort": "id"}

    headers = {"Accept": "application/json"}

    i = 1

    problem_list = []

    while True:
        querystring["page"] = i

        response = requests.get(url, headers=headers, params=querystring)

        # is empty
        if not response.json()['items']:
            break

        problem_list.extend(response.json()['items'])

        i += 1

    return problem_list


def get_organization_solved_problems_by_level_and_tag(name: str = "하나고등학교"):
    level_problems: dict[int, set[int] | list[int]] = {i: [] for i in range(31)}

    tag_data = get_solvedac_tag_dict()
    tag_problems: dict[int, list[int]] = {i: [] for i in range(max(tag_data.keys()) + 1)}

    for handle in get_user_handle_list(get_organization_id(name)):  # Delete when deploy
        problems = get_user_solved_problem_list(handle)

        for problem in problems:
            level_problems[problem['level']].append(problem['problemId'])

            for tag in problem['tags']:
                tag_problems[tag['bojTagId']].append(problem['problemId'])

    level_problems = {key: list(sorted(set(value))) for key, value in level_problems.items()}

    tag_problems = {key: list(sorted(set(value))) for key, value in tag_problems.items()}

    for key, value in tag_data.items():
        new_value = value.copy()
        new_value['solved_count'] = len(tag_problems[key])
        tag_data[key] = new_value

    return level_problems, tag_data


def get_solved_problem_info(name="하나고등학교"):
    solved_problems_user: dict[int, dict[str, int | str]] = {}

    user_data = get_user_data(get_user_handle_list(get_organization_id(name)))

    for handle in user_data:
        problems = get_user_solved_problem_list(handle)

        for problem in problems:
            print(problem)
            if solved_problems_user.get(problem['problemId']) is None:
                solved_problems_user[problem['problemId']] = {"handle": "", "tier": 0, "user_count": 0}
            if handle['tier'] > solved_problems_user[problem['problemId']]["tier"]:
                solved_problems_user[problem['problemId']]["handle"] = handle["handle"]
                solved_problems_user[problem['problemId']]["tier"] = handle["tier"]
            solved_problems_user[problem['problemId']]['user_count'] += 1

    return solved_problems_user


def get_solvedac_tag_list():
    url = "https://solved.ac/api/v3/tag/list"

    querystring = {"sort": "problemCount"}

    headers = {"Accept": "application/json"}

    i = 1

    tag_list = []

    while True:
        querystring["page"] = i

        response = requests.get(url, headers=headers, params=querystring)

        # is empty
        if not response.json()['items']:
            break

        tag_list.extend(response.json()['items'])

        i += 1

    return tag_list


def get_solvedac_tag_dict():
    tag_data = {}
    tags = get_solvedac_tag_list()

    for tag in tags:
        tag_data[tag['bojTagId']] = {'count': tag['problemCount'],
                                     'ko'   : tag['displayNames'][0]['name'],
                                     'en'   : tag['displayNames'][1]['name']}

    return tag_data


def get_solvedac_problem_level_count():
    url = "https://solved.ac/api/v3/problem/level"

    headers = {"Accept": "application/json"}

    response = requests.get(url, headers=headers)

    data = {}
    for i in response.json():
        data[i['level']] = i['count']

    return data


if __name__ == '__main__':
    main()
    # print(get_solved_problem_info())
