# 个人部署与定制说明

更新日期：2026-10-07。个人测试服务器已发布 Hermes Agent **0.21.5** 加定制补丁，发布提交 `f10e61f1e1d0309c31b87b1339e017822a8a6146`，集成分支为 `integration/official-0215-quiet`。CLI、Gateway、Web UI Bridge 和原生 Dashboard 均已切换新版。公网后台路由修复、Dashboard 服务托管及真实对话验收尚未完成。

## 0.21.5 集成与本地验证

2026-10-04，在独立分支 `integration/official-0215-quiet` 中合入官方正式版
`v2026.9.24`，固定提交 `f97608f178d1ffeca59860195ab7da295f7c8e5f`（代码版本
`0.21.5`）。原官方基线到该正式版共 98 个提交、147 个文件变更；合并无冲突，
当前 12 个定制文件相对官方基线的差异完整保留。官方此次依赖声明和锁文件仅调整项目版本；
服务器新环境按锁文件安装，实际安装版本不保证与旧环境的未锁定传递依赖相同。

本地验证环境为 Windows、Python 3.13.14，使用独立虚拟环境按 `uv.lock` 安装 core、
dev、web 依赖，依赖一致性检查通过。通过 `scripts/run_tests.sh` 运行 18 个相关测试文件：
283 项通过、2 项失败、7 项跳过。覆盖微信静默与令牌持久化、主适配器凭据作用域、
会话搜索与数据库归属、凭据隔离、缓存释放作用域、cron 存储及投递作用域、配置迁移、
Dashboard profile 配置读取与认证，以及上游变更涉及的 Gateway 和记忆逻辑。

两项失败均位于 `tests/tools/test_memory_tool.py::TestMemoryFileLockPermissions`：
测试要求 POSIX `0600` 权限，而 Windows 返回 `0666`。在原定制版和升级版上分别调用
真实锁文件实现，新建与既有文件均复现同样结果，未改动生产逻辑或测试来掩盖该平台差异。
跳过项包含非 Windows 路径，不能视为服务器验证通过。

另通过一项临时真实文件验证：在 multiplex 模式下按 `default → home → default` 切换，
读取各自配置与测试凭据；home 缺失的凭据不回退到 default；会话搜索排除混合数据库内
其他 profile 的记录；各自数据库完整性检查通过；记忆及暂停的 cron 任务保持各自归属。
分别验证有版本标记与无版本标记配置的迁移，模型、微信显示配置、multiplex 设置、
`.env` 和 `SOUL.md` 保留预期值。临时验证数据未使用正式凭据，没有执行 cron 或发送消息。

该提交已部署到个人测试服务器。服务器验证结果见下文。
本地测试不代替服务器真实账号对话验收。

## 运行结构

CLI、Gateway 和独立 Web UI 的 Python Bridge 使用同一套核心源码及虚拟环境。Web UI 包保持 0.6.35，本次未升级其界面功能。

`default`、`home` 是两套独立 profile，共用一个 multiplex Gateway：default 承载微信、企业微信和 API，home 承载微信。只共享代码和依赖，不合并配置、凭据、会话、记忆、绑定或定时任务。Web UI Bridge 保留 profile 选择与隔离。

Gateway 与 Web UI 分别仅监听本机 8643、8658。其他项目与反向代理未随本次发布调整。

原生 Dashboard 作为独立后台验证进程监听本机 9119，显式使用 `-p default`，识别 default、home 两套 profile。尚未纳入 systemd 或开机自启，也未替换独立 Web UI 的公网入口。

## 定制变更

- 微信普通对话跳过会话重置提示和未设置主频道的引导，保留命令、错误及必要审批消息。
- multiplex 主适配器在所属 profile 的凭据作用域内创建。
- 微信文本与媒体过期令牌按旧值条件删除并持久化，避免误删新令牌；文本发送在锁内读取最新令牌。
- 会话搜索与浏览按当前会话的 profile 过滤，在数据库候选截取前应用条件，避免跨 profile 泄漏及候选挤占；显式指定 profile 的既有接口保留。
- 官方新版已覆盖 cron 任务及投递的凭据作用域，不重复套用旧 scheduler 补丁。

两套 profile 分别合并以下配置，其他字段保持原样：

```yaml
display:
  platforms:
    weixin:
      tool_progress: "off"
      show_reasoning: false
      interim_assistant_messages: false
      long_running_notifications: false
      busy_ack_detail: false
      busy_steer_ack_enabled: false
      streaming: false
```

官方 0.21.4 已不再按旧 `session_reset` 执行每日及空闲 24 小时会话重置；本次接受该上游行为变化，未重新实现旧规则。新功能需要额外配置时，不会因切换源码自动启用。

## 发布方式与回退

2026-10-04 已部署独立发布目录 `releases/20261004-0215-quiet/` 和 `venv`，保留
`releases/20260924-weixin-quiet/` 及其旧环境。新目录由固定官方提交归档与 12 个定制文件组成，
全部 15079 个受版本控制的条目按 Git blob 校验通过，不包含 Git 元数据。

CLI 启动脚本指向新环境；Gateway 专属 systemd 覆盖调整 PATH 和退出清理入口；Web UI 专属覆盖通过 `HERMES_AGENT_ROOT`、`HERMES_AGENT_BRIDGE_PYTHON` 选择新核心，并继续由 systemd 单独管理 Gateway 的启停。

停服前检查两个 profile 的活动 Agent 和 cron 执行记录，停止 Web UI／Bridge、独立
Dashboard 和共享 Gateway，确认旧核心进程退出后备份两套运行数据、配置、CLI 脚本和
相关服务覆盖文件，再切换入口。此次一致性数据备份约 203 MB，仅留服务器受限目录，
不进入仓库。维护切换于 2026-10-04 13:38（北京时间）完成，执行耗时约 38 秒。

回退需停止新版 Gateway、Web UI／Bridge 和独立 Dashboard，恢复旧入口、配置和覆盖文件，
再启动旧 Gateway、Web UI 和 Dashboard。若数据库发生不兼容迁移，必须恢复配套的一致性
数据备份；恢复备份可能丢失发布后的新消息。本次未触发回退。后续更新继续使用新的发布目录，
不直接修改保留的旧源码。

两套配置均从 schema v33 迁移至 v46。先在服务器副本中预演，再保留用户原有策略：
子任务最大迭代数 50、并发数 3、技能过期 30 天、归档 90 天，以及原有显示、模型目录缓存
和工具选择配置。发布后逐顶层字段比较，仅 `_config_version` 改变；两套 `.env` 摘要不变。
后续更新不能跳过预演、只修改版本标记，也不能无审查接受迁移器自动改变这些策略。

## 验证与限制

- 0.21.5 在服务器 ARM64、Python 3.11.15 环境通过仓库测试脚本单 worker 验证 9 个文件，134 项通过、0 项失败；依赖一致性检查通过。
- 两套真实配置与 SQLite 一致性副本在禁止网络连接的预演中通过迁移与数据库完整性检查；正式库在停写备份后、切换前检查正常。
- 服务器副本按 default → home → default 切换，profile 目录、配置和凭据作用域检查通过；未连接真实渠道或执行 cron。
- CLI、Gateway、Web UI Bridge、Dashboard 进程入口均指向新版；两个 profile 被共享 Gateway 服务，两套微信、企业微信及 API 均为 connected。
- Web UI 首页返回 200，Dashboard 首页返回 302，未认证配置 API 被拒绝；8643、8658、9119 均保持本机监听。
- default 的 4 个和 home 的 2 个 cron 任务数量及 ID 保留，没有手工触发任务。Nginx 与 x-ui 进程保持不变。
- 未跑全量套件，未发送真实微信消息或模型请求；本次未重新验收 Web UI Bridge 连续创建 Agent、Dashboard 正式账号登录及模型对话。相关实际使用路径仍待验收。

## 发布记录

| 日期 | 发布内容 | 验证边界 |
| --- | --- | --- |
| 2026-09-24 | 0.21.4 加定制补丁，统一 CLI、Gateway、Web UI Bridge 核心 | 168 项相关测试通过；真实消息验收待完成 |
| 2026-09-24 | 构建原生 Dashboard 前端，验证隔离配置与数据库副本 | 测试账号登录、静态资源、两个 profile 会话读取、WebSocket 握手及数据库完整性通过；隔离实例已停止 |
| 2026-10-04 | 启用 `dashboard_auth/basic`，显式选择 default 启动本机 Dashboard | 登录页 200、首页 302、状态接口 200；认证门禁启用，未认证 API / WebSocket 被拒绝；正式账号登录和模型对话未验证 |
| 2026-10-04 | 发布 0.21.5 定制版 `f10e61f1`，同步切换四个核心入口，配置 v33 → v46 | 服务器 134 项测试通过；副本迁移及 profile 切换通过；渠道连接、网页和认证门禁正常；真实对话未验收 |

上表认证插件启用操作仅修改 default 的插件配置，未重启 Gateway、Web UI 或 Nginx。
随后 0.21.5 核心发布重启了 Gateway、Web UI／Bridge 和 Dashboard；两套配置仅版本标记变化，
凭据文件摘要不变，Nginx 未调整。

## Dashboard 发布流程

1. 核对发布目录、全局 active profile、端口和运行服务；备份配置及一致性数据库副本，备份不进入仓库。
2. 按当前源码 engines 选择 Node/npm，使用锁文件安装 Web 工作区并构建。此前 npm 11.16.0 被拒绝；0.21.5 发布复用 Node 24.18.0 和已有 npm 11.17.0，在新目录安装、构建成功，未升级系统工具：

   ```bash
   export npm_config_cache="$PWD/.dashboard-npm-cache"
   export NODE_OPTIONS=--max-old-space-size=1024
   npm exec --yes --package=npm@11.17.0 -- npm ci --workspace web --include-workspace-root=false --no-audit --no-fund
   npm exec --yes --package=npm@11.17.0 -- npm run build --workspace web
   ```

3. 使用隔离 HERMES_HOME、测试认证配置和数据库副本验证；不复制渠道凭据，不连接真实消息平台或 MCP，不发送模型消息。
4. 确认 default 的认证配置及 `plugins.enabled` 中包含 `dashboard_auth/basic`，保留其他配置。将 `HERMES_HOME` 指向正式数据根目录、`HERMES_WEB_DIST` 指向当前发布的 `hermes_cli/web_dist`，并通过 `HERMES_DASHBOARD_PUBLIC_URL` 声明实际外部访问域名以启用密码门禁。
5. 用当前发布环境执行 `hermes -p default dashboard --host 127.0.0.1 --port 9119 --no-open --skip-build`。显式 profile 防止机器上 active profile 与认证凭据所属 profile 不同；该命令本身不配置后台托管。
6. 检查页面和静态资源、`auth_required`、认证正反向路径、profile 及 WebSocket，复核既有服务。正式密码登录和模型调用单独验收，不能仅凭状态接口判定对话可用。
7. 进程托管、反向代理和公网入口切换需明确实施范围并验证后，再停止独立 Web UI。当前未完成这一步。

单独回退认证插件配置时，只恢复该次修改字段，不覆盖后续配置。回退核心发布则按前述
发布回退流程处理 Dashboard 进程和核心路径，保留原认证配置。

## 服务器连接与只读排查

2026-10-07 复核：Windows OpenSSH 经本机代理的 SOCKS 通道可连接测试服务器。
服务器地址、SSH 端口、登录用户名、私钥位置及可执行的连接参数，只保存在用户指定的
仓库外敏感包 `server-info.md` 中；项目文档不复制这些值。私钥不读入聊天、不上传服务器。

### 连接前检查

1. 读取敏感包的连接节，以该文件所在目录解析相对私钥路径。历史示例中的盘符可能过期，
   先确认文件存在，不凭旧路径猜测。
2. 使用 `C:\Windows\System32\OpenSSH\ssh.exe`；本机 `ssh` 曾不在 PATH 中。
   代理辅助程序为 Git for Windows 自带的 `C:\Program Files\Git\mingw64\bin\connect.exe`，
   不在 `usr\bin` 下。先用 `Test-Path` 确认两个程序存在。
3. 读取系统代理，并检查对应本机端口是否监听、进程是否为预期代理程序。代理端口每次确认，
   不作为项目固定配置。Windows 的系统 HTTP 代理不会自动让 OpenSSH 走代理。

   ```powershell
   Get-ItemProperty 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' |
     Select-Object ProxyEnable, ProxyServer
   # $proxyPort 从当前本机代理设置取得
   Get-NetTCPConnection -State Listen -LocalPort $proxyPort |
     Select-Object LocalAddress, LocalPort, OwningProcess
   ```

4. 核对用户 `known_hosts` 中已有的主机密钥。首次连接或密钥变化时，先通过可信渠道核验指纹；
   不用 `StrictHostKeyChecking=no`，不通过删除旧记录绕过不匹配。

### SSH 方式与参数

敏感包内提供可直接使用的 PowerShell 参数模板。通用连接结构如下，变量须先由敏感包和
当前本机代理配置赋值，不能将占位变量直接当作服务器参数：

```powershell
$sshExe = 'C:\Windows\System32\OpenSSH\ssh.exe'
$connectExe = 'C:/Program Files/Git/mingw64/bin/connect.exe'
$proxyCommand = 'ProxyCommand="{0}" -S {1}:{2} %h %p' -f $connectExe, $proxyHost, $proxyPort
$sshArgs = @('-F', 'NUL', '-i', $keyPath, '-p', "$sshPort",
  '-o', 'BatchMode=yes', '-o', 'IdentitiesOnly=yes',
  '-o', 'StrictHostKeyChecking=yes', '-o', 'UpdateHostKeys=no',
  '-o', 'ConnectTimeout=20', '-o', $proxyCommand, "$sshUser@$serverAddress")
& $sshExe @sshArgs 'uname -sm'
```

- `-F NUL` 排除本机其他 SSH 配置的影响；`-i` 与 `IdentitiesOnly=yes` 固定身份来源。
- `BatchMode=yes` 不等待密码交互；本次使用现有私钥登录。
- `ProxyCommand` 显式走 SOCKS 代理。包含空格的辅助程序路径必须保留双引号。
- `%h`、`%p` 由 SSH 替换；`UpdateHostKeys=no` 避免此次连接自动修改已保存的主机密钥。
- 使用 HTTP CONNECT 时，辅助程序参数为 `-H`；代理必须确实支持该协议，不因失败改走直连。

只读多行排查脚本可通过 PowerShell 单引号 here-string 管道输入远端 `python -B -`，
避免本地展开脚本中的变量；Python 路径使用敏感包中核实的当前环境。`-B` 仅禁止生成
字节码，脚本本身仍须保持只读，不导入可能写入配置或启动服务的应用入口。

### 排查顺序与失败判断

- 先检查连接、系统架构和服务状态，再核对进程实际启动路径。不要仅根据 `VIRTUAL_ENV`
  判断运行版本，发布后可能保留旧环境变量。
- 配置只输出目标字段，例如模型名、推理强度、配置 schema 和 profile 名称；读取进程环境
  时只输出需要的路径字段，不打印完整环境、`.env`、认证文件、令牌或用户消息。
- `Connection timed out during banner exchange` 表示尚未完成 SSH banner 交换，不足以判断
  私钥失效。依次检查本地代理、代理出口到 SSH 端口的可达性、服务器状态及安全组。
- HTTP 代理返回 `200 Connection established` 只表示代理接受隧道；仍需收到 SSH banner 并
  完成主机密钥及用户认证，才算登录成功。网页 HTTP 200 也不能证明 SSH 可用。
- 本次曾发生 HTTP/SOCKS 通道握手超时，后来使用相同 SOCKS 方式重试成功，没有关闭主机
  校验或改用直连。重试应有次数和超时限制。
- `Permission denied (publickey)` 再核对用户、密钥路径及授权；`UNPROTECTED PRIVATE KEY FILE`
  则按敏感包修复本地 ACL，不放宽权限。变更 ACL 与远端配置前确认执行授权。
- Clash/Mihomo Fake-IP 可能影响本机 DNS；域名核查应通过代理上下文或服务器侧完成。

连接成功后默认只读，不自动执行 `doctor --fix`、升级、迁移、服务启停、路由或防火墙修改。
文件上传使用相同代理与主机校验参数；`scp` 的端口选项是大写 `-P`，并在两端校验摘要。
上传、部署和备份恢复均属于另外的写入操作，不由“测试连接”隐含授权。

## 已知问题与修复记录

| 问题 | 修复 / 状态 |
| --- | --- |
| 缺少前端构建产物 | 已构建 `hermes_cli/web_dist`，静态资源验证通过 |
| npm `EBADENGINE` | 使用符合当前项目约束的 npm 11.17.0，安装与构建通过 |
| 本机模式下密码登录后认证 API 不可用 | 显式声明外部 public URL 启用认证中间件；隔离登录、API 与 WS 握手通过 |
| 保存密码后仍无认证 provider | 启用 basic 插件并显式选择持有认证配置的 default；本机启动通过 |
| 旧公网后台路由不一致 | 已核实 `/admin/` 仍代理到未监听的 8648，Dashboard 在 9119；本次未修改 Nginx，公网后台尚未修复验收 |
| Dashboard 自动恢复与开机自启 | 当前仅后台验证进程，尚未实施服务托管 |

独立 Web UI 停止时不会连带停止共享 Gateway，但会停止自己的 Python Bridge 并中断网页操作；现有反向代理不调整则网页入口也会失效。不能把“配置未丢失”视为“全部使用方式不受影响”。

本文件不记录服务器地址、账号凭据、私钥、真实认证值或用户会话内容。此次部署的具体备份、
迁移预演和切换记录留在服务器受限备份目录；历史环境说明由仓库外文档管理，不假定其内容已同步更新。
