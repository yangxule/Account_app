# Account — 个人记账App

记录每一笔人民币花销的桌面记账软件，支持两级分类、统计图表、导出备份、搜索筛选、预算提醒，内置贪吃蛇小游戏。

> 本项目基于[黑马程序员 vibe_coding 课程](https://www.bilibili.com/video/BV1RFTc62EaK/?spm_id_from=333.788.player.switch&p=15)所写出的记账 App，所有内容由 Claude Code agent 和 DeepSeek 大模型写出。

## 怎么启动（日常使用）

打开终端，进入本文件夹，运行：

```bash
./start.sh
```

第一次运行会自动创建数据库和默认分类。

## 小游戏：贪吃蛇 🐍

主窗口「🎮 小游戏」标签页内置了贪吃蛇小游戏，和记账功能完全独立、不碰账本数据：

- 键盘**方向键**（或 WASD）控制蛇移动，每吃一个 🍎 +1 分、变长一节
- 撞墙或撞到自己 → 游戏结束，点「↺ 重新开始」再来一局
- 切到其他标签页自动暂停，切回继续（蛇不会在记账时偷偷撞死）

## 开发环境

- Ubuntu 22.04 + Python（conda 环境 `vibe_coding_learning`）
- PySide6（桌面界面）+ SQLite（数据存储）+ matplotlib（图表）+ openpyxl（Excel 导出）

## 常见问题

**启动报错 `qt.qpa.plugin: ... libxcb-cursor0 is needed ...`**

Ubuntu 22.04 默认缺少 Qt6 需要的鼠标光标库，安装一次即可：

```bash
sudo apt install -y libxcb-cursor0
```
