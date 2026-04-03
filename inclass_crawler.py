import os
import sys
import json
import argparse
import requests
from fpdf import FPDF
from PIL import Image
from io import BytesIO


parser = argparse.ArgumentParser()
parser.add_argument(
    "--mode",
    choices=["slides", "problems", "both"],
    default="both",
    help="slides: 导出整份课件PDF；problems: 导出互动题图片；both: 两者都导出"
)
args = parser.parse_args()


# load config
try:
    with open("config.json", "r") as f:
        config = json.load(f)
        sessionid = config["sessionid"]
        lesson_id = config["lesson_id"]
        presentation_id = config["presentation_id"]
except:
    print("Error: config.json not found or invalid.")
    sys.exit()


# set authorization
session = requests.Session()
session.headers.update({
    "cookie"    : f"sessionid={sessionid}",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36"
})
data = {
    "lessonId": lesson_id,
    "source": 5
}
url = "https://pro.yuketang.cn/api/v3/lesson/checkin"

response = session.post(url, json=data)
session.headers.update({"authorization": "Bearer " + response.headers.get("Set-Auth")})


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

if args.mode in ["slides", "both"]:
    pdf = FPDF()

if args.mode in ["problems", "both"]:
    os.makedirs("problems", exist_ok=True)

for slide in slides:
    need_download = False

    if args.mode in ["slides", "both"]:
        need_download = True
    elif args.mode == "problems":
        try:
            problem = slide["problem"]
            need_download = True
        except:
            need_download = False

    if not need_download:
        continue

    response = session.get(f"{slide['cover']}")
    if response.status_code != 200:
        print(f"Error: {response.status_code}")
        sys.exit()

    if args.mode in ["slides", "both"]:
        img = Image.open(BytesIO(response.content))
        width, height = img.size
        pdf.add_page(format=(width * 25.4 / 72, height * 25.4 / 72))
        pdf.image(BytesIO(response.content), x=0, y=0, w=width * 25.4 / 72, h=height * 25.4 / 72)

    if args.mode in ["problems", "both"]:
        try:
            problem = slide["problem"]
            with open(f"problems/Slide_{slide['index']}.jpg", "wb") as f:
                f.write(response.content)
        except:
            pass

if args.mode in ["slides", "both"]:
    pdf.output("slides.pdf")

print("Done.")