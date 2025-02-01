import datetime
import json
import os
import random
import subprocess
import time
import zipfile
from pathlib import Path

import requests

Path("cache").mkdir(exist_ok=True)
Path("ext/comment").mkdir(parents=True, exist_ok=True)
Path("ext/longtext").mkdir(parents=True, exist_ok=True)
Path("resources/pic").mkdir(parents=True, exist_ok=True)
Path("resources/video").mkdir(parents=True, exist_ok=True)

HEADERS = {
    "authority": "m.weibo.cn",
    "accept": "application/json, text/plain, */*",
    "accept-language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
    "cache-control": "no-cache",
    "mweibo-pwa": "1",
    "origin": "https://m.weibo.cn",
    "pragma": "no-cache",
    "referer": "https://m.weibo.cn/compose/",
    "sec-ch-ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
    "sec-ch-ua-mobile": "?1",
    "sec-ch-ua-platform": '"Android"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "sec-ch-ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
    "sec-ch-ua-mobile": "?1",
    "sec-ch-ua-platform": '"Android"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "user-agent": "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Mobile Safari/537.36",
    "x-requested-with": "XMLHttpRequest",
}


# COOKIES: dict = json.load(open("cookie.json", "r", encoding="utf-8"))
# cookie: dict = COOKIES["weibo.cn"]

cookie: dict = json.load(open("cookie.json", "r", encoding="utf-8"))
cookie["MLOGIN"] = 1


cache_dir = Path("cache")
cache_dir.mkdir(exist_ok=True)


def __request(url: str, custom_headers: dict = {}) -> dict:
    headers = {
        **HEADERS,
        **custom_headers,
        "cookie": "; ".join([f"{k}={v}" for k, v in cookie.items()]),
        "x-xsrf-token": cookie.get("XSRF-TOKEN", ""),
    }
    return requests.get(url, headers=headers, timeout=(30, 60)).json()


def request(url: str, referer: str = "", cached: bool = False, all_ret=False) -> dict:
    cache_file = cache_dir / f"{url.split('/')[-1].replace('?','_')}.json"
    if cached and cache_file.exists():
        return json.load(cache_file.open("r", encoding="utf-8"))
    headers = {"referer": referer} if referer else {}
    resp = __request(url, headers)
    time.sleep(random.random() * 0.3 + 0.7)
    if "ok" not in resp:
        print(resp)
        raise NotImplementedError
    if resp["ok"] != 1:
        if resp.get("msg", "") in ["已过滤部分评论", "快来发表你的评论吧", "还没有人评论哦~快来抢沙发！"]:
            pass
        else:
            print(resp)
            refresh_cookie()
            resp = __request(url, headers)
    if not all_ret:
        resp = resp.get("data", {})
    if cached:
        json.dump(resp, cache_file.open("w", encoding="utf-8"), ensure_ascii=False)
    return resp


def refresh_cookie(return_uid=False):
    cookie["_T_WM"] = int(time.time() / 3600) * 100001
    resp = request("https://m.weibo.cn/api/config")
    cookie["XSRF-TOKEN"] = resp["st"]

    print(f"Time watermark: {cookie['_T_WM']}")
    print(f"XSRF token: {cookie['XSRF-TOKEN']}")

    if return_uid:
        return resp["uid"]


UID = refresh_cookie(return_uid=True)
# 如果你想爬取别人的微博，直接修改这里的 UID 即可
# UID = 1111681197

more_url = request(
    f"https://m.weibo.cn/profile/info?uid={UID}",
    referer=f"https://m.weibo.cn/profile/{UID}",
)["more"]

CID = int(more_url.split("/")[-1].split("_")[0])


# ====================================================================================================


def fetchRefreshedPost(post) -> dict:
    pid = post["id"]
    data = request(
        f"https://m.weibo.cn/api/container/getIndex?containerid={CID}_-_WEIBO_SECOND_PROFILE_WEIBO&page_type=03&since_id={pid}",
        referer=f"https://m.weibo.cn/p/{CID}_-_WEIBO_SECOND_PROFILE_WEIBO",
    )
    return data["cards"][0]["mblog"]


def fetchLongText(post, dirname) -> None:
    pid = post["id"]
    filename = f"{dirname}/longtext/{pid}.json"
    if Path(filename).exists():
        post["longtext"] = json.load(open(filename, "r", encoding="utf-8"))
        return
    longtext = request(
        f"https://m.weibo.cn/statuses/extend?id={pid}",
        referer=f"https://m.weibo.cn/detail/{pid}",
    ).get("longTextContent", "")
    json.dump(longtext, open(filename, "w", encoding="utf-8"), ensure_ascii=False)
    post["longtext"] = longtext


def fetchPhoto(pic, post_id: str, dirname) -> None:
    pid = pic["pid"]
    url = pic["large"]["url"]
    if url.split(".")[-1] in ["jpg", "gif"]:
        filename = f"{dirname}/pic/{post_id}_{pid}.{url.split('.')[-1]}"
    else:
        print(pic)
        raise NotImplementedError
    if not Path(filename).exists():
        print("[+] Downloading Photo", pid, "from", url)
        resp = requests.get(url, headers={"referer": "https://weibo.com/"})
        open(filename, "wb").write(resp.content)

    if "type" not in pic:
        return
    if pic["type"] == "livephotos":
        url = pic["videoSrc"]
        if url.split(".")[-1] in ["mov"]:
            filename = f"{dirname}/pic/{post_id}_{pid}.{url.split('.')[-1]}"
        else:
            print(pic)
            raise NotImplementedError
        if not Path(filename).exists():
            print("[+] Downloading Live Photo", pid, "from", url)
            resp = requests.get(url, headers={"referer": "https://weibo.com/"})
            open(filename, "wb").write(resp.content)
    elif pic["type"] == "gifvideos":
        pass
    else:
        print(pic)
        raise NotImplementedError


def fetchVideo(post, dirname) -> None:
    pid = post["id"]
    url = list(post["page_info"]["urls"].values())[0]
    ext = url.split("?")[0].split(".")[-1]
    filename = f"{dirname}/video/{pid}.mp4"
    if Path(filename).exists():
        return
    print("[+] Downloading Video", pid, "from", url)
    url = list(fetchRefreshedPost(post)["page_info"]["urls"].values())[0]
    if ext == "mp4":
        resp = requests.get(url)
        open(filename, "wb").write(resp.content)
    else:
        command = f'ffmpeg -i "{url}" -c copy -bsf:a aac_adtstoasc {filename}'
        subprocess.run(command, shell=True)


def fetchSecondComments(mid, cid, max_id, dirname) -> tuple[list, int]:
    if int(max_id) == 0:
        filename = f"{dirname}/comment/{mid}_{cid}.json"
    else:
        filename = f"{dirname}/comment/{mid}_{cid}_{max_id}.json"
    if Path(filename).exists():
        data = json.load(open(filename, "r", encoding="utf-8"))
    else:
        print("[+] Downloading Comment Child", cid, max_id)
        url = f"https://m.weibo.cn/comments/hotFlowChild?cid={cid}&max_id={max_id}&max_id_type=0"
        data = request(url, all_ret=True)
        json.dump(data, open(filename, "w", encoding="utf-8"), ensure_ascii=False)
    if "data" not in data:
        if data["errno"] == "100011" and data["msg"] == "暂无数据":
            return [], 0
        print(data)
        raise NotImplementedError
    comments = data["data"]
    max_id = data["max_id"]
    return comments, max_id


def fetchFirstComments(mid, max_id, dirname) -> tuple[list, int]:
    if int(max_id) == 0:
        filename = f"{dirname}/comment/{mid}.json"
    else:
        filename = f"{dirname}/comment/{mid}_{max_id}.json"
    if Path(filename).exists():
        data = json.load(open(filename, "r", encoding="utf-8"))
    else:
        print("[+] Downloading Comment", mid, max_id)
        url = f"https://m.weibo.cn/comments/hotflow?mid={mid}&max_id={max_id}&max_id_type=0"
        data = request(url, all_ret=True)
        json.dump(data, open(filename, "w", encoding="utf-8"), ensure_ascii=False)
    if "data" not in data:
        return [], 0
    data = data["data"]
    comments = []
    for x in data["data"]:
        if x["comments"] and x["total_number"] != len(x["comments"]):
            comments_all = []
            _max_id = 0
            while True:
                _data, _max_id = fetchSecondComments(mid, x["id"], _max_id, dirname)
                comments_all += _data
                if _max_id == 0:
                    break
            x["comments_all"] = comments_all
        comments.append(x)
    max_id = data["max_id"]
    return comments, max_id


def fetchComments(post, dirname) -> None:
    mid = post["mid"]
    if post["comments_count"] == 0:
        post["comments"] = []
        return
    max_id = 0
    comments = []
    while True:
        _comments, max_id = fetchFirstComments(mid, max_id, dirname)
        comments += _comments
        if max_id == 0:
            break
    post["comments"] = comments


def fetchRelatedContent(post):
    # 原创的微博
    if post["isLongText"]:
        fetchLongText(post, "ext")
    if "raw_text" in post and "page_info" in post:
        page_info = post["page_info"]
        if page_info["type"] == "video" and page_info["urls"] is not None:
            fetchVideo(post, "resources")
    if "pics" in post:
        for pic in post["pics"]:
            fetchPhoto(pic, post["id"], "resources")
    fetchComments(post, "ext")

    # 转发的微博
    # if "retweeted_status" in post and post["retweeted_status"].get("isLongText", False):
    #     post["retweeted_status"]["longtext"] = fetchLongText(post["retweeted_status"])
    # if "retweeted_status" in post and post["retweeted_status"].get("pics", []):
    #     for pic in post["retweeted_status"]["pics"]:
    #         fetchPhoto(pic)


# ====================================================================================================


def fetchIncrementalPosts():
    data = request(
        f"https://m.weibo.cn/api/container/getIndex?containerid={CID}_-_WEIBO_SECOND_PROFILE_WEIBO",
        referer=f"https://m.weibo.cn/p/{CID}_-_WEIBO_SECOND_PROFILE_WEIBO",
    )
    posts = json.load(open("posts.json", "r", encoding="utf-8"))
    post_ids = set([post["id"] for post in posts])
    while len(data["cards"]) > 0 and "since_id" in data["cardlistInfo"]:
        since_id: int = data["cardlistInfo"]["since_id"]
        for card in data["cards"]:
            if card["card_type"] == 9:
                if card["mblog"]["id"] in post_ids:
                    continue
                fetchRelatedContent(card["mblog"])
                posts.append(card["mblog"])
            elif card["card_type"] == 11 and "card_group" in card:
                for sub_card in card["card_group"]:
                    if sub_card["card_type"] == 9:
                        if sub_card["mblog"]["id"] in post_ids:
                            continue
                        fetchRelatedContent(sub_card["mblog"])
                        posts.append(sub_card["mblog"])
                    else:
                        print("[+] Unknown card type", sub_card["card_type"])
            else:
                print("[+] Unknown card type", card["card_type"])
        print("[+]", len(posts), "posts", posts[-1]["created_at"], since_id)
        if str(since_id) in post_ids:
            break
        data = request(
            f"https://m.weibo.cn/api/container/getIndex?containerid={CID}_-_WEIBO_SECOND_PROFILE_WEIBO&page_type=03&since_id={since_id}",
            referer=f"https://m.weibo.cn/p/{CID}_-_WEIBO_SECOND_PROFILE_WEIBO",
            cached=True,
        )

    # last page case
    if len(data["cards"]) == 0:
        return posts
    for card in data["cards"]:
        if card["card_type"] == 9:
            if card["mblog"]["id"] in post_ids:
                continue
            fetchRelatedContent(card["mblog"])
            posts.append(card["mblog"])
        elif card["card_type"] == 11 and "card_group" in card:
            for sub_card in card["card_group"]:
                if sub_card["card_type"] == 9:
                    if sub_card["mblog"]["id"] in post_ids:
                        continue
                    fetchRelatedContent(sub_card["mblog"])
                    posts.append(sub_card["mblog"])
                else:
                    print("[+] Unknown card type", sub_card["card_type"])
        else:
            print("[+] Unknown card type", card["card_type"])  
    if not posts:
        print("[+]", "No posts found!")
        return posts
    print("[+]", len(posts), "posts", posts[-1]["created_at"], "last page!")
    return posts


def fetchPosts():
    if Path("posts.json").exists():
        print("检测到 posts.json 文件，将进行增量备份")
        return fetchIncrementalPosts()
    data = request(
        f"https://m.weibo.cn/api/container/getIndex?containerid={CID}_-_WEIBO_SECOND_PROFILE_WEIBO",
        referer=f"https://m.weibo.cn/p/{CID}_-_WEIBO_SECOND_PROFILE_WEIBO",
        cached=True,
    )
    posts = []
    while len(data["cards"]) > 0 and "since_id" in data["cardlistInfo"]:
        since_id = data["cardlistInfo"]["since_id"]
        for card in data["cards"]:
            if card["card_type"] == 9:
                fetchRelatedContent(card["mblog"])
                posts.append(card["mblog"])
            elif card["card_type"] == 11 and "card_group" in card:
                for sub_card in card["card_group"]:
                    if sub_card["card_type"] == 9:
                        fetchRelatedContent(sub_card["mblog"])
                        posts.append(sub_card["mblog"])
                    else:
                        print("[+] Unknown card type", sub_card["card_type"])
            else:
                print("[+] Unknown card type", card["card_type"])
        print("[+]", len(posts), "posts", posts[-1]["created_at"], since_id)
        data = request(
            f"https://m.weibo.cn/api/container/getIndex?containerid={CID}_-_WEIBO_SECOND_PROFILE_WEIBO&page_type=03&since_id={since_id}",
            referer=f"https://m.weibo.cn/p/{CID}_-_WEIBO_SECOND_PROFILE_WEIBO",
            cached=True,
        )

    # last page case:
    if len(data["cards"]) == 0:
        return posts
    for card in data["cards"]:
        if card["card_type"] == 9:
            fetchRelatedContent(card["mblog"])
            posts.append(card["mblog"])
        elif card["card_type"] == 11 and "card_group" in card:
            for sub_card in card["card_group"]:
                if sub_card["card_type"] == 9:
                    fetchRelatedContent(sub_card["mblog"])
                    posts.append(sub_card["mblog"])
                else:
                    print("[+] Unknown card type", sub_card["card_type"])
        else:
            print("[+] Unknown card type", card["card_type"])
    if not posts:
        print("[+]", "No posts found!")
        return posts
    print("[+]", len(posts), "posts", posts[-1]["created_at"], "last page!")
    return posts


if __name__ == "__main__":
    posts = fetchPosts()
    print("Total", len(posts), "posts")

    posts = sorted(posts, key=lambda x: x["id"], reverse=True)
    print(f"[+] Saving into posts.json")
    json.dump(posts, open("posts.json", "w", encoding="utf-8"), ensure_ascii=False)

    def zipdir(path, ziph):
        for root, dirs, files in os.walk(path):
            for file in files:
                ziph.write(
                    os.path.join(root, file),
                    os.path.relpath(os.path.join(root, file), os.path.join(path, "..")),
                )

    current_date = datetime.datetime.now().strftime("%Y%m%d")
    zip_filename = f"weibo_archive_{current_date}.zip"
    print(f"[+] Saving into {zip_filename}")
    zipf = zipfile.ZipFile(zip_filename, "w", zipfile.ZIP_DEFLATED)
    zipf.write("posts.json")
    folders = ["ext", "resources"]
    for folder in folders:
        zipdir(folder, zipf)
    zipf.close()
