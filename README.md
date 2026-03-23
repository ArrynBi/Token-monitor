# token-monitor

如果只想下载程序，直接点击这里：

- [GitHub Releases](https://github.com/ArrynBi/Token-monitor/releases)

`token-monitor` 是一个桌面置顶悬浮球，用来查看 OpenAI 兼容接口或 OpenAI 官方组织接口的用量情况。

当前版本重点展示：

- 套餐或来源名称
- 当前周期剩余额度
- 当前周期已用金额
- 请求数、输入输出 tokens、缓存读取、TPM / RPM、平均耗时
- 订阅到期时间
- 最近一次刷新状态
- API 列表快速切换

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
- 右键菜单和详情弹窗顶部都支持 `Switch API`
- 设置页可以添加多个 API 配置，并按列表选择切换

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

- `profiles`
  API 配置列表，每项都包含名称、Base URL、API Key、Organization ID
- `active_profile_index`
  当前启用的是列表里的第几个 API
- `fallback_budget_usd`
  当上游没有明确返回额度上限时，使用这个值估算剩余额度
- `refresh_interval_seconds`
  自动刷新间隔，最小 30 秒

`Base URL` 只填写主域名，例如 `https://mdlbus.com`，不要填写成 `https://mdlbus.com/v1`。

示例配置见 [config.example.json](./config.example.json)。

## 打包

项目现在分别提供 Windows 和 macOS 的打包入口：

- Windows: [token-monitor.win.spec](./token-monitor.win.spec) + [build_win.bat](./build_win.bat)
- macOS: [token-monitor.mac.spec](./token-monitor.mac.spec) + [build_macos.sh](./build_macos.sh)

### Windows

直接运行：

```powershell
build_win.bat
```

打包完成后，输出文件位于：

```text
dist/Token悬浮球.exe
```

同时会生成：

```text
release/token-monitor-win.zip
```

Windows 图标会在打包前自动由 `token_orb.svg` 生成 `token_orb.ico` 并嵌入 `exe`。

`build/`、`dist/`、`release/` 和生成出来的图标文件都属于本地产物，不再提交到 GitHub 仓库。

兼容旧入口：

```powershell
build_exe.bat
```

在 Windows `exe` 模式下，程序会在可执行文件同目录读取和生成 `config.json`。

### macOS

需要在 macOS 机器上运行：

```bash
chmod +x build_macos.sh
./build_macos.sh
```

打包完成后，输出文件位于：

```text
dist/Token悬浮球.app
```

同时会生成：

```text
release/token-monitor-macos.zip
```

macOS 图标现在会在打包前自动由 `token_orb.svg` 生成 `build/token_orb.iconset`，再通过 `iconutil` 生成 `src/token_monitor/assets/token_orb.icns` 并嵌入 `.app`。

macOS 发布包还会额外包含：

- `README-首次打开.txt`
- `打开Token悬浮球.command`

推荐首次使用时双击 `打开Token悬浮球.command`，它会自动移除下载隔离标记并启动应用。应用配置会保存到：

```text
~/Library/Application Support/Token悬浮球/config.json
```

## 依赖

- Python 3.11+
- PySide6
- Pillow

## 项目结构

```text
token-monitor/
  main.py
  config.example.json
  build_exe.bat
  build_win.bat
  build_macos.sh
  token-monitor.win.spec
  token-monitor.mac.spec
  src/
    token_monitor/
      __init__.py
      app.py
      config.py
      openai_api.py
      ui.py
```
