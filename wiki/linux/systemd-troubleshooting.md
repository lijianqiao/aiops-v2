---
title: systemd 服务异常排障
applies_to: [linux, systemd]
triggers: [Service nginx is down, systemd unit failed]
risk_level: L1
last_reviewed: 2026-05-11
---

## 现象

systemd 单元进入 failed 或 inactive 状态，业务实例不可用。

## 排查步骤

1. `systemctl status <service>`
2. `journalctl -u <service> -n 200 --no-pager`
3. `systemctl show <service> --property=ActiveState,SubState,ExecMainStatus`

## 处置方案

优先识别配置错误、依赖故障和端口占用；重启前必须确认服务属于允许自动恢复的白名单。

## 验证

确认单元恢复为 active，关键探针通过，错误日志不再持续增长。
