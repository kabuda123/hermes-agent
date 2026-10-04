# 个人部署与定制说明

更新日期：2026-10-04。基于官方 Hermes Agent **0.21.4**，固定上游提交 `02ed55e572a96246d34f0e2fb3aa51197db50df5`，集成分支为 `integration/official-weixin-quiet`。核心已发布；原生 Dashboard 已完成本机启动与认证保护验证，公网切换及正式对话验收尚未完成。

## 0.21.5 本地升级候选（尚未部署）

2026-10-04，在独立分支 `integration/official-0215-quiet` 中合入官方正式版
`v2026.9.24`，固定提交 `f97608f178d1ffeca59860195ab7da295f7c8e5f`（代码版本
`0.21.5`）。原官方基线到该正式版共 98 个提交、147 个文件变更；合并无冲突，
当前 12 个定制文件相对官方基线的差异完整保留。依赖声明和锁文件仅调整项目版本，
没有升级依赖版本。

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

此候选尚未推送或部署。服务器两套真实配置和数据库副本迁移、ARM64/Python 3.11
验证、独立 Web UI Bridge 连续切换创建 Agent、真实微信对话及 Dashboard 模型对话
仍需在发布阶段验收。本次未构建前端、未切换现有服务入口；下文部署状态仍指已发布的
0.21.4。正式更新继续采用新的独立发布目录和配套一致性备份。

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

2026-09-24 已部署独立发布目录 `releases/20260924-weixin-quiet/` 和 `venv`，不覆盖旧源码、旧环境或未提交修改。发布目录是固定源码归档加补丁，不包含 Git 元数据。

CLI 启动脚本指向新环境；Gateway 专属 systemd 覆盖调整 PATH 和退出清理入口；Web UI 专属覆盖通过 `HERMES_AGENT_ROOT`、`HERMES_AGENT_BRIDGE_PYTHON` 选择新核心，并继续由 systemd 单独管理 Gateway 的启停。

停服前检查两个 profile 的活动任务，停止两个 Hermes 服务及 Bridge 后备份两套运行数据、配置、CLI 脚本和服务单元，再切换入口。备份仅留服务器，不进入仓库。

回退需停止两个 Hermes 服务及 Bridge，恢复旧入口、配置和覆盖文件，再依次启动旧 Gateway 与 Web UI。若数据库发生不兼容迁移，必须恢复配套的一致性数据备份；恢复备份可能丢失发布后的新消息。后续更新应准备新的发布目录，不直接修改保留的旧源码来更新当前服务。

## 验证与限制

- 本地相关测试通过；服务器 ARM64、Python 3.11.15 环境使用仓库测试脚本单 worker 重跑 11 个文件，168 项通过、0 项失败，依赖检查通过。
- 两套数据库副本迁移完整性检查通过，正式库发布后检查正常。
- 现有 Web UI Bridge 在隔离环境按 default → home → default 创建新版 Agent 成功。
- CLI 与 Bridge 使用新版核心；两套微信、企业微信及 API 已连接；网页及 API 健康检查正常，启动日志未发现错误。
- 这些检查不代表全量项目测试或真实账号对话验收。两个微信账号及网页模型对话仍待用户手工验收。

## 发布记录

| 日期 | 发布内容 | 验证边界 |
| --- | --- | --- |
| 2026-09-24 | 0.21.4 加定制补丁，统一 CLI、Gateway、Web UI Bridge 核心 | 168 项相关测试通过；真实消息验收待完成 |
| 2026-09-24 | 构建原生 Dashboard 前端，验证隔离配置与数据库副本 | 测试账号登录、静态资源、两个 profile 会话读取、WebSocket 握手及数据库完整性通过；隔离实例已停止 |
| 2026-10-04 | 启用 `dashboard_auth/basic`，显式选择 default 启动本机 Dashboard | 登录页 200、首页 302、状态接口 200；认证门禁启用，未认证 API / WebSocket 被拒绝；正式账号登录和模型对话未验证 |

本次正式配置仅增加认证插件，复用已有凭据；home 配置及两套凭据文件摘要不变。Gateway、Web UI、Nginx 在操作前后的 PID 和状态一致，消息/API 通道仍 connected。

## Dashboard 发布流程

1. 核对发布目录、全局 active profile、端口和运行服务；备份配置及一致性数据库副本，备份不进入仓库。
2. 按当前源码 engines 选择 Node/npm，使用锁文件安装 Web 工作区并构建。本次 npm 11.16.0 被拒绝，改用发布目录缓存中的 npm 11.17.0，未升级系统工具：

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

回退时只停止核实身份后的新增 Dashboard 进程，并恢复本次插件字段，不覆盖后续其他配置。涉及数据库不兼容迁移时沿用前述一致性备份回退规则。

## 已知问题与修复记录

| 问题 | 修复 / 状态 |
| --- | --- |
| 缺少前端构建产物 | 已构建 `hermes_cli/web_dist`，静态资源验证通过 |
| npm `EBADENGINE` | 使用符合当前项目约束的 npm 11.17.0，安装与构建通过 |
| 本机模式下密码登录后认证 API 不可用 | 显式声明外部 public URL 启用认证中间件；隔离登录、API 与 WS 握手通过 |
| 保存密码后仍无认证 provider | 启用 basic 插件并显式选择持有认证配置的 default；本机启动通过 |
| 旧公网后台 502 | 旧反向代理未指向新 Dashboard 端口，尚未修复和重新验收 |
| Dashboard 自动恢复与开机自启 | 当前仅后台验证进程，尚未实施服务托管 |

独立 Web UI 停止时不会连带停止共享 Gateway，但会停止自己的 Python Bridge 并中断网页操作；现有反向代理不调整则网页入口也会失效。不能把“配置未丢失”视为“全部使用方式不受影响”。

本文件不记录服务器地址、账号凭据、私钥、真实认证值或用户会话内容。环境专属路径、备份位置和检查记录保留在仓库外的 `ARCHITECTURE_AND_PROGRESS.md`。
