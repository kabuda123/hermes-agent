# 个人部署与定制说明

更新日期：2026-09-24。基于官方 Hermes Agent **0.21.4**，固定上游提交 `02ed55e572a96246d34f0e2fb3aa51197db50df5`，集成分支为 `integration/official-weixin-quiet`。

## 运行结构

CLI、Gateway 和独立 Web UI 的 Python Bridge 使用同一套核心源码及虚拟环境。Web UI 包保持 0.6.35，本次未升级其界面功能。

`default`、`home` 是两套独立 profile，共用一个 multiplex Gateway：default 承载微信、企业微信和 API，home 承载微信。只共享代码和依赖，不合并配置、凭据、会话、记忆、绑定或定时任务。Web UI Bridge 保留 profile 选择与隔离。

Gateway 与 Web UI 分别仅监听本机 8643、8658。其他项目与反向代理未随本次发布调整。

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

本文件不记录服务器地址、账号凭据、私钥、真实配置值或用户会话内容。
