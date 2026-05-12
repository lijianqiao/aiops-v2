---
title: H3C 接口抖动排障
applies_to: [h3c, comware]
triggers: [Interface flap, interface down/up frequently]
risk_level: L2
last_reviewed: 2026-05-11
---

## 现象

接口在短时间内反复 down/up，可能伴随链路抖动和上层会话闪断。

## 排查步骤

1. `display interface brief`
2. `display interface <port>`
3. `display logbuffer | include <port>`

## 处置方案

先确认是否为物理层故障、双工速率不匹配或上联异常，再决定是否进入人工审批的变更流程。

## 验证

观察接口稳定时间窗内无再次 flap，关键业务与邻居协议恢复正常。
