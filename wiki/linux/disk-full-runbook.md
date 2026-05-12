---
title: Linux 磁盘满排障
applies_to: [linux, ext4, xfs]
triggers: [Disk space is critically low, filesystem full]
risk_level: L1
last_reviewed: 2026-05-11
---

## 现象

主机触发磁盘空间不足告警，业务可能出现写入失败或日志异常增长。

## 排查步骤

1. `df -h`
2. `du -sh /var/log/* | sort -h`
3. `journalctl --disk-usage`

## 处置方案

优先清理可安全轮转的日志、临时文件和过期制品；禁止直接删除数据库或业务持久化目录。

## 验证

确认目标挂载点使用率回落，业务健康检查恢复，告警解除。
