---
title: H3C OSPF 邻居 down 排障
applies_to: [h3c, comware]
triggers: [OSPF neighbor state change, OSPF Down]
risk_level: L2
last_reviewed: 2026-05-11
---

## 现象

OSPF 邻居从 Full 退化为 Down、Init 或 ExStart，路由收敛可能受影响。

## 排查步骤

1. `display ospf peer`
2. `display ospf interface`
3. `display current-configuration interface <port>`

## 处置方案

优先确认物理链路、MTU、一致的 area 与认证参数；涉及接口 shutdown/no shutdown 的动作必须转入审批流程。

## 验证

确认邻居恢复 Full，路由表收敛正常，相关告警清除。
