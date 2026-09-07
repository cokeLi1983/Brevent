# 广告开单 ERP（Windows 桌面版）

这是一个可离线运行的广告业务开单、收款、费用、结账和报表工具。数据保存在本机独立的 SQLite 数据库中，不需要安装数据库服务器。

## 功能

- 客户档案：客户名称、联系人、电话、地址、信用额度和状态。
- 广告订单：自动生成订单号，记录媒体/项目、数量、单价、税率、业务员、开始/结束日期和备注；订单确认后自动生成应收款。
- 收款登记：支持一个订单分多次收款，自动显示订单余额，并保留收款方式与收据号。
- 费用登记：记录供应商、费用科目、金额、日期和说明。
- 月度结账：对指定月份创建不可重复的结账快照，汇总开单、收款、费用、应收、利润；已结账月份禁止再新增或删除业务数据。
- 报表：业务汇总、客户应收余额、收款明细和费用明细，可导出为 UTF-8 CSV（可由 Excel 打开）。
- 数据库：使用独立的本地 SQLite 数据库，并支持备份数据库文件。

## Windows 安装与启动

1. 在 Windows 安装 Python 3.10 或更新版本，并在安装时勾选 **Add Python to PATH**。
2. 双击 `install_windows.bat` 检查运行环境。
3. 双击 `run_windows.bat` 启动。首次启动会自动创建默认数据库。

本程序只使用 Python 标准库（Tkinter、SQLite），无需联网和额外依赖。数据默认位于 `%LOCALAPPDATA%\AdvertisingERP\advertising_erp.db`。

## 打包为 Windows EXE

在一台 Windows 电脑中运行：

```bat
python -m pip install pyinstaller
build_windows_exe.bat
```

生成的便携版位于 `dist\广告ERP\`。将该目录压缩为 RAR 可使用已安装的 WinRAR：

```bat
"C:\Program Files\WinRAR\WinRAR.exe" a -r 广告ERP-windows.rar dist\广告ERP\
```

> 本仓库的构建环境不是 Windows，且未安装 WinRAR，因此不能在这里产出可验证的 `.exe`/`.rar` 二进制包；提供的 Windows 脚本会在 Windows 上生成它们。

## 数据与安全

- 结账前请使用“备份数据库”保留副本。
- 测试数据可直接删除；生产使用前建议先录入正式客户资料。
- 该工具提供业务记账管理，不替代依法要求的财务软件、发票系统或审计流程。
