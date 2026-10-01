# Account — 个人记账App

记录每一笔人民币花销的桌面记账软件，支持两级分类、统计图表、导出备份、搜索筛选、预算提醒。

## 怎么启动（日常使用）

打开终端，进入本文件夹，运行：

```bash
./start.sh
```

第一次运行会自动创建数据库和默认分类。

## 开发环境

- Ubuntu 22.04 + Python（conda 环境 `vibe_coding_learning`）
- PySide6（桌面界面）+ SQLite（数据存储）+ matplotlib（图表）+ openpyxl（Excel 导出）
