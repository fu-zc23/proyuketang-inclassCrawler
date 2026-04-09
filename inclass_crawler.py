import os
import re
import sys
import json
import time
import argparse
import requests
import websocket
from fpdf import FPDF
from PIL import Image
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor


def download_slide(slide_info, sessionid, auth):
    idx, slide = slide_info
    headers = {
        "cookie": f"sessionid={sessionid}",
        "authorization": f"Bearer {auth}",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36"
    }
    try:
        response = requests.get(slide['cover'], headers=headers, timeout=30)
        if response.status_code == 200:
            return idx, slide, response.content
    except Exception as e:
        print(f"Failed to get slide {idx}. Error: {e}")
    return idx, slide, None


def login_and_get_sessionid(session):
    # 1. 获取 csrftoken
    url = "https://pro.yuketang.cn/v/course_meta/user_info"
    response = session.get(url)
    csrftoken = response.cookies.get("csrftoken")
    if not csrftoken:
        print("Error: failed to get csrftoken.")
        sys.exit()
    session.headers.update({
        "cookie": f"csrftoken={csrftoken}"
    })

    # 2. 获取微信登录参数
    url = "https://pro.yuketang.cn/api/v3/user/login/wechat-auth-param"
    response = session.post(url)
    data = response.json()["data"]
    appId = data["appId"]
    state = data["state"]
    redirectUri = data["redirectUri"]

    # 3. 获取 uuid
    params = {
        "appid": appId,
        "scope": "snsapi_login",
        "state": state,
        "redirect_uri": redirectUri
    }
    url = "https://open.weixin.qq.com/connect/qrconnect"
    response = session.get(url, params=params)
    uuid = re.search(r"uuid=([a-zA-Z0-9]+)", response.text).group(1)

    # 4. 获取二维码并弹窗显示
    url = f"https://open.weixin.qq.com/connect/qrcode/{uuid}"
    response = session.get(url)
    img = Image.open(BytesIO(response.content))
    img.show()
    print("请扫码登录...")

    # 5. 轮询扫码状态
    login_url = "https://lp.open.weixin.qq.com/connect/l/qrconnect"
    code = None
    while True:
        params = {
            "uuid": uuid,
            "_": int(time.time() * 1000)
        }
        response = session.get(login_url, params=params)
        text = response.text
        if "wx_errcode=405" in text:
            code = re.search(r"wx_code='(.*?)'", text).group(1)
            print("扫码成功")
            break
        elif "wx_errcode=404" in text:
            print("已扫码，等待确认...")
        elif "wx_errcode=408" in text:
            print("等待扫码...")
        time.sleep(1)

    # 6. 登录平台
    params = {
        "code": code,
        "state": state
    }
    session.get(redirectUri, params=params)

    # 7. 获取 sessionid
    sessionid = session.cookies.get("sessionid")
    if not sessionid:
        print("Error: login failed.")
        sys.exit()
    print(f"登录成功，sessionid: {sessionid}")
    return sessionid


def is_sessionid_valid(session):
    try:
        res = session.get("https://pro.yuketang.cn/api/v3/user/basic-info", timeout=10).json()
        return res.get("code") == 0
    except:
        return False


def save_config(config):
    with open("config.json", "w") as f:
        json.dump(config, f, ensure_ascii=False, indent=4)


def get_presentation_id(sessionid, lesson_id, user_id, auth):
    ws = None
    try:
        ws = websocket.create_connection(
            "wss://pro.yuketang.cn/wsapp/",
            timeout=10,
            header=[
                "Origin: https://pro.yuketang.cn",
                f"Cookie: sessionid={sessionid}",
                "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36"
            ]
        )
        hello_msg = {
            "op": "hello",
            "userid": str(user_id),
            "role": "student",
            "auth": auth,
            "lessonid": str(lesson_id)
        }
        ws.send(json.dumps(hello_msg))
        msg = json.loads(ws.recv())

        if msg.get("presentation"):
            return msg["presentation"]
        else:
            print("Error: failed to get presentation_id from websocket.")
            print("Response: ")
            print(msg)
            sys.exit()

    except Exception as e:
        print(f"Error: failed to get presentation_id from websocket. {e}")
        sys.exit()
    finally:
        if ws is not None:
            ws.close()
    print("Error: failed to get presentation_id.")
    sys.exit()


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode",
        choices=["slides", "problems", "both"],
        default="both",
        help="slides: 导出整份课件PDF；problems: 导出互动题图片；both: 两者都导出"
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="下载线程数"
    )
    args = parser.parse_args()


    # load config
    try:
        with open("config.json", "r") as f:
            config = json.load(f)
            sessionid = config["sessionid"]
            lesson_id = config["lesson_id"]
    except:
        print("Error: config.json not found or invalid.")
        sys.exit()


    # login
    session = requests.Session()
    session.headers.update({
        "cookie": f"sessionid={sessionid}",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36"
    })
    if not is_sessionid_valid(session):
        sessionid = login_and_get_sessionid(session)
        config["sessionid"] = sessionid
        save_config(config)
        session.headers.update({
            "cookie": f"sessionid={sessionid}"
        })


    # checkin
    data = {
        "lessonId": lesson_id,
        "source": 5
    }
    url = "https://pro.yuketang.cn/api/v3/lesson/checkin"

    response = session.post(url, json=data)
    auth = response.headers.get("Set-Auth")
    session.headers.update({"authorization": "Bearer " + auth})
    identity_id = response.json()["data"]["identityId"]
    lesson_token = response.json()["data"]["lessonToken"]


    # get presentation_id
    presentation_id = get_presentation_id(sessionid, lesson_id, identity_id, lesson_token)
    print(f"Auto detected presentation_id: {presentation_id}")


    # get slides
    url = f"https://pro.yuketang.cn/api/v3/lesson/presentation/fetch?presentation_id={presentation_id}"
    response = session.get(url)
    if response.status_code != 200:
        print(f"Error: {response.status_code}")
        sys.exit()
    response = response.json()
    if response["code"] != 0:
        print(f"Error: {response['message']}")
        sys.exit()

    slides = response["data"]["slides"]


    # download slides
    if args.mode in ["slides", "both"]:
        pdf = FPDF()

    if args.mode in ["problems", "both"]:
        os.makedirs("problems", exist_ok=True)

    tasks = []
    for idx, slide in enumerate(slides, start=1):
        need_download = False
        if args.mode in ["slides", "both"]:
            need_download = True
        elif args.mode == "problems":
            try:
                problem = slide["problem"]
                need_download = True
            except:
                need_download = False
        if need_download:
            tasks.append((idx, slide))

    results = [None] * len(tasks)
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = [executor.submit(download_slide, task, sessionid, auth) for task in tasks]
        for i, future in enumerate(futures, start=1):
            idx, slide, content = future.result()
            if content is None:
                print(f"Error: failed to download slide {idx}.")
                sys.exit()
            results[i - 1] = (idx, slide, content)

    for idx, slide, content in results:
        if args.mode in ["slides", "both"]:
            img = Image.open(BytesIO(content))
            width, height = img.size
            pdf.add_page(format=(width * 25.4 / 72, height * 25.4 / 72))
            pdf.image(BytesIO(content), x=0, y=0, w=width * 25.4 / 72, h=height * 25.4 / 72)
        if args.mode in ["problems", "both"]:
            try:
                problem = slide["problem"]
                with open(f"problems/Slide_{slide['index']}.jpg", "wb") as f:
                    f.write(content)
            except:
                pass

    if args.mode in ["slides", "both"]:
        pdf.output("slides.pdf")

    print("Done.")