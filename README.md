# token-monitor

一个为 Windows 设计的置顶浮窗。当前版本使用 Qt 透明窗口来绘制悬浮球，优先适配 `https://aixj.vip`，展示：

- 当前套餐名称
- 今日剩余额度
- 今日已用金额
- 请求数、tokens、缓存命中、TPM / RPM、平均耗时
- 过期时间

## 说明

这个项目现在有两种取数模式：

1. `aixj.vip` / 类似网关

- 优先使用 `GET /v1/usage`
- 这也是你这次提供的 JSON extractor 对应的接口

2. OpenAI 官方

- 使用 `GET /v1/organization/usage/completions`
- 使用 `GET /v1/organization/costs`

## 已实测的 aixj.vip 返回内容

我已用你提供的 API Key 对 `https://aixj.vip/v1/usage` 做过真实请求，返回字段包括：

- `isValid`
- `planName`
- `remaining`
- `unit`
- `subscription.daily_limit_usd`
- `subscription.daily_usage_usd`
- `subscription.expires_at`
- `usage.average_duration_ms`
- `usage.rpm`
- `usage.tpm`
- `usage.today.actual_cost`
- `usage.today.input_tokens`
- `usage.today.output_tokens`
- `usage.today.cache_read_tokens`
- `usage.today.requests`
- `usage.today.total_tokens`
- `usage.total.*`

其中一次真实返回里，关键值是：

- `planName = Codex100刀订阅专用`
- `remaining = 99.121656`
- `subscription.daily_limit_usd = 100`
- `subscription.daily_usage_usd = 0.878344`
- `usage.today.requests = 28`
- `usage.today.input_tokens = 119620`
- `usage.today.output_tokens = 27831`
- `usage.today.cache_read_tokens = 671616`
- `usage.average_duration_ms = 22944.75`
- `usage.tpm = 7475`

所以这个程序现在会把 `aixj.vip` 版本的主视图设计成：

- 大号主数字显示“今日剩余金额”
- 进度条显示“今日已用 / 每日总额度”
- 下方卡片显示请求、tokens、缓存读取、吞吐和平均时延
- Footer 显示过期时间和最近刷新状态

## 关于 aixj.vip 官网

我还检查了它首页公开资源：

- 首页是一个前端单页应用
- 页面公开配置里能看到站点名 `AI新境 - AI API Gateway`
- 前端资源里至少能明确看到 `/api/v1` 这一组后端入口

这次我没有使用你提供的网站账号密码登录后台，因为公开 API 响应已经足够完成这个版本，也更安全。

## 运行

1. 进入项目目录
2. 安装依赖

```powershell
python -m pip install -r requirements.txt
```

3. 用 Python 3.11+ 运行

```powershell
python main.py
```

首次运行会在项目根目录生成一个 `config.json`。然后在设置里填入：

- `Base URL`，默认是 `https://aixj.vip`
- `API Key`
- `Organization ID`
  使用 `aixj.vip` 时通常可以留空
  使用 `api.openai.com` 时需要填写 `org_...`
- `Fallback Budget (USD)`
  当服务没有明确返回额度上限时，用这个值兜底
- `Refresh Interval`

## 关于第三方 OpenAI 兼容地址

像 `https://aixj.vip` 这类 OpenAI 兼容网关，除了常见的：

- `GET /v1/models`
- `POST /v1/chat/completions`

有些还会像 `aixj.vip` 一样额外提供：

- `GET /v1/usage`

这比 OpenAI 官方的 organization 统计接口更适合做个人浮窗监控，因为它直接返回：

- 是否有效
- 当前套餐名
- 剩余额度
- 每日额度和每日使用
- 当日请求与 token 数据

如果你切回 OpenAI 官方地址，程序会自动改用 organization usage / costs 逻辑。

## OpenAI 官方参考

- `Base URL = https://api.openai.com`
- 拥有组织统计权限的 `Admin API Key`
- 对应的 `Organization ID`

官方文档：

- https://platform.openai.com/docs/api-reference/usage/completions_object
- https://platform.openai.com/docs/api-reference/usage/costs
- https://platform.openai.com/docs/api-reference/administration

## 使用

- 拖动顶部标题条可以移动浮窗
- `Refresh` 立即刷新
- `Settings` 打开配置窗口
- `X` 关闭程序

## 打包 EXE

这个项目已经补好了 `PyInstaller` 打包配置：

- [token-monitor.spec](C:/Users/Allen/Desktop/Coding/token-monitor/token-monitor.spec)
- [build_exe.bat](C:/Users/Allen/Desktop/Coding/token-monitor/build_exe.bat)

直接双击或在终端运行：

```powershell
build_exe.bat
```

打包完成后，产物在：

```text
dist/token-monitor.exe
```

`exe` 模式下会在 `exe` 同目录自动生成和读取 `config.json`。

## 文件结构

```text
token-monitor/
  main.py
  config.example.json
  src/
    token_monitor/
      app.py
      config.py
      openai_api.py
      ui.py
```
