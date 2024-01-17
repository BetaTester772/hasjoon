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
        return None

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
        if user_dict is not None:
            df = pd.concat([df, pd.DataFrame(user_dict, index=[i])])

    # add boj rank
    df['boj_rank'] = df.index + 1
    df = df.reset_index(drop=True)

    # solved_rank by rank
    df = df.sort_values(by='rating', ascending=False)
    df = df.reset_index()
    df['solved_rank'] = df.index + 1

    return df


def main() -> tuple[pd.DataFrame, dict]:
    user_data = get_user_data(get_user_handle_list(get_organization_id("하나고등학교")))
    print(user_data)
    user_data.to_csv(f'user_data.csv', index=True)  # data.

    organization_data = get_organization_info("하나고등학교")
    pd.DataFrame(organization_data, index=[0]).to_csv(f'organization_data.csv', index=True)
    print(organization_data)

    return user_data, organization_data


if __name__ == '__main__':
    main()
