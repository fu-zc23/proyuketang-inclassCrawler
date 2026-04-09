# proyuketang-inclassCrawler

在荷塘雨课堂上课时提前获取当前课件和所有互动题目。

**该项目仅供个人学习参考，下载内容严禁传播或营利，使用完毕请及时删除。请自觉遵守相关法律法规，一切法律责任由用户自行承担。**

## 使用说明

### 1. 配置 `config.json` 文件

进入上课界面，将网址中的 `lesson_id` 复制到 `config.json` 文件的 `lesson_id` 项中，这通常是一个 19 位数字。例如，下面网址中的 `lesson_id` 为 `165471317xxxxxxxxxx`。

```
https://pro.yuketang.cn/lesson/student/v3/165471317xxxxxxxxxx?source=5
```

`sessionid` 项可留空，运行程序时扫码登录后会自动获取、保存。

### 2. 运行程序

确保安装所有依赖后运行该程序，注意 `fpdf` 需要安装 `fpdf2`。

```
python inclass_crawler.py --mode slides --workers 8
```

参数说明：

- `--mode`：指定下载模式，可选值为 `slides`、`problems` 或 `both`（默认）。
  - `slides`：仅下载课件，保存到当前目录，命名为 `slides.pdf`。
  - `problems`：仅下载互动题目，以 jpg 格式保存到 `problems` 目录下，命名为 `Slide_n.jpg`。其中 `n` 为该互动题目所在页码。
  - `both`：同时下载课件和互动题目。
- `--workers`：下载线程数，默认为 `4`。


### 3. 注意事项

注意该程序仅用于获取当前正在放映的课件，若课上放映了新的课件需要重新获取。

## LISENCE

本仓库的内容采用 [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/) 许可协议。您可以自由使用、修改、分发和创作衍生作品，但只能用于非商业目的，署名原作者，并以相同的授权协议共享衍生作品。

如果您认为文档的部分内容侵犯了您的合法权益，请联系项目维护者，我们会尽快删除相关内容。
