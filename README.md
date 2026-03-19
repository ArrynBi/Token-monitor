# token-monitor

如果只想下载程序，直接点击这里：

- [下载 token-monitor.exe](https://github.com/ArrynBi/Token-monitor/releases/latest/download/token-monitor.exe)

`token-monitor` 是一个面向 Windows 的置顶悬浮球，用来查看 OpenAI 兼容接口或 OpenAI 官方组织接口的用量情况。

当前版本重点展示：

- 套餐或来源名称
- 当前周期剩余额度
- 当前周期已用金额
- 请求数、输入输出 tokens、缓存读取、TPM / RPM、平均耗时
- 订阅到期时间
- 最近一次刷新状态

## 支持的取数方式

程序现在支持两类上游：

1. OpenAI 兼容网关

- 优先请求 `GET /v1/usage`
- 适合像 `https://aixj.vip` 这类会直接返回套餐、余额、请求统计的服务

2. OpenAI 官方组织接口

- `GET /v1/organization/usage/completions`
- `GET /v1/organization/costs`

当 `Base URL` 包含 `api.openai.com` 时，程序会自动切换到 OpenAI 官方组织统计逻辑。

## 界面说明

悬浮球主界面会显示：

- 中间主数字：当前剩余额度
- 进度环：当前周期已用比例
- 底部信息：请求数与已用百分比
- 侧边小色点：当前状态提示

详情弹窗会显示：

- `Remaining`
- `Used Today`
- `Requests`
- `Tokens`
- `Cache Read`
- `TPM / RPM`
- `Avg Delay`
- `Expires`
- `Status`

## 使用方式

- 左键拖动悬浮球可以移动位置
- 双击悬浮球可以展开或收起详情弹窗
- 右键悬浮球可以打开快捷菜单
- 详情弹窗顶部可以快速执行 `Refresh`、`Help`、`Settings`、`Close`

## 安装与运行

1. 进入项目目录
2. 安装依赖

```powershell
python -m pip install -r requirements.txt
```

3. 运行程序

```powershell
python main.py
```

首次运行会自动生成 `config.json`。

## 配置说明

可在设置窗口或 `config.json` 中配置：

- `base_url`
  OpenAI 兼容服务地址，默认是 `https://aixj.vip`
- `api_key`
  你的 API Key
- `organization_id`
  使用 OpenAI 官方组织接口时需要填写；兼容网关通常可留空
- `fallback_budget_usd`
  当上游没有明确返回额度上限时，使用这个值估算剩余额度
- `refresh_interval_seconds`
  自动刷新间隔，最小 30 秒

示例配置见 [config.example.json](./config.example.json)。

## 打包 EXE

项目已包含 PyInstaller 配置：

- [token-monitor.spec](./token-monitor.spec)
- [build_exe.bat](./build_exe.bat)

直接运行：

```powershell
build_exe.bat
```

打包完成后，输出文件位于：

```text
dist/token-monitor.exe
```

在 `exe` 模式下，程序会在可执行文件同目录读取和生成 `config.json`。

## 依赖

- Python 3.11+
- PySide6

## 项目结构

```text
token-monitor/
  main.py
  config.example.json
  build_exe.bat
  token-monitor.spec
  src/
    token_monitor/
      __init__.py
      app.py
      config.py
      openai_api.py
      ui.py
```
