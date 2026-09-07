"""Offline advertising order and bookkeeping ERP for Windows (Python 3.10+)."""
from __future__ import annotations

import csv
import shutil
import sqlite3
from datetime import date, datetime
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

APP_TITLE = "广告开单 ERP"
DEFAULT_DIR = Path.home() / "AppData" / "Local" / "AdvertisingERP"


class Database:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self._schema()

    def _schema(self):
        self.conn.executescript("""
        CREATE TABLE IF NOT EXISTS customers (id INTEGER PRIMARY KEY, name TEXT UNIQUE NOT NULL,
          contact TEXT, phone TEXT, address TEXT, credit_limit REAL DEFAULT 0, active INTEGER DEFAULT 1,
          created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS orders (id INTEGER PRIMARY KEY, number TEXT UNIQUE NOT NULL,
          customer_id INTEGER NOT NULL REFERENCES customers(id), project TEXT NOT NULL, media TEXT,
          quantity REAL NOT NULL DEFAULT 1, unit_price REAL NOT NULL DEFAULT 0, tax_rate REAL DEFAULT 0,
          order_date TEXT NOT NULL, start_date TEXT, end_date TEXT, salesperson TEXT, status TEXT NOT NULL,
          note TEXT, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS receipts (id INTEGER PRIMARY KEY, number TEXT UNIQUE NOT NULL,
          order_id INTEGER NOT NULL REFERENCES orders(id), amount REAL NOT NULL CHECK(amount > 0),
          receipt_date TEXT NOT NULL, method TEXT, note TEXT, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS expenses (id INTEGER PRIMARY KEY, number TEXT UNIQUE NOT NULL,
          vendor TEXT NOT NULL, category TEXT NOT NULL, amount REAL NOT NULL CHECK(amount > 0),
          expense_date TEXT NOT NULL, note TEXT, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS closures (period TEXT PRIMARY KEY, revenue REAL NOT NULL, receipts REAL NOT NULL,
          expenses REAL NOT NULL, receivable REAL NOT NULL, profit REAL NOT NULL, closed_at TEXT NOT NULL);
        """)
        self.conn.commit()

    def execute(self, sql, values=()):
        cur = self.conn.execute(sql, values)
        self.conn.commit()
        return cur

    def rows(self, sql, values=()):
        return self.conn.execute(sql, values).fetchall()

    def value(self, sql, values=()):
        row = self.conn.execute(sql, values).fetchone()
        return row[0] if row else 0

    def number(self, prefix):
        return f"{prefix}{datetime.now():%Y%m%d%H%M%S%f}"


class ERP(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1280x760")
        self.minsize(1050, 650)
        self.db = Database(DEFAULT_DIR / "advertising_erp.db")
        self._menu()
        self.tabs = ttk.Notebook(self)
        self.tabs.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.pages = {}
        for name, build in [("仪表盘", self.dashboard), ("客户", self.customers), ("广告订单", self.orders),
                            ("收款", self.receipts), ("费用", self.expenses), ("结账与报表", self.reports)]:
            page = ttk.Frame(self.tabs, padding=10)
            self.tabs.add(page, text=name)
            self.pages[name] = page
            build(page)
        self.refresh_all()

    def _menu(self):
        menu = tk.Menu(self)
        file_menu = tk.Menu(menu, tearoff=False)
        file_menu.add_command(label="备份数据库…", command=self.backup)
        file_menu.add_command(label="打开数据文件夹", command=self.show_db_path)
        file_menu.add_separator(); file_menu.add_command(label="退出", command=self.destroy)
        menu.add_cascade(label="文件", menu=file_menu)
        help_menu = tk.Menu(menu, tearoff=False)
        help_menu.add_command(label="关于", command=lambda: messagebox.showinfo(APP_TITLE, "广告开单、收款、费用与结账管理\n版本 1.0（离线 SQLite）"))
        menu.add_cascade(label="帮助", menu=help_menu)
        self.config(menu=menu)

    @staticmethod
    def money(v): return f"¥{float(v or 0):,.2f}"
    @staticmethod
    def today(): return date.today().isoformat()

    def form(self, parent, fields, submit):
        box = ttk.LabelFrame(parent, text="新增记录", padding=10); box.pack(fill="x", pady=(0, 8))
        values = {}
        for i, (key, label, default) in enumerate(fields):
            ttk.Label(box, text=label).grid(row=i // 4 * 2, column=i % 4, sticky="w", padx=4)
            var = tk.StringVar(value=default); values[key] = var
            ttk.Entry(box, textvariable=var, width=27).grid(row=i // 4 * 2 + 1, column=i % 4, sticky="ew", padx=4, pady=(0, 5))
        ttk.Button(box, text="保存", command=lambda: submit(values)).grid(row=(len(fields) - 1) // 4 * 2 + 2, column=0, sticky="w", padx=4)
        return values

    def tree(self, parent, columns, widths=None):
        wrap = ttk.Frame(parent); wrap.pack(fill="both", expand=True)
        view = ttk.Treeview(wrap, columns=[x[0] for x in columns], show="headings", selectmode="browse")
        for idx, (key, title) in enumerate(columns):
            view.heading(key, text=title); view.column(key, width=(widths or {}).get(key, 120), anchor="w")
        bar = ttk.Scrollbar(wrap, orient="vertical", command=view.yview); view.configure(yscrollcommand=bar.set)
        view.pack(side="left", fill="both", expand=True); bar.pack(side="right", fill="y")
        return view

    def dashboard(self, page):
        self.dashboard_text = tk.StringVar()
        ttk.Label(page, text="经营概览", font=("Microsoft YaHei UI", 18, "bold")).pack(anchor="w", pady=(0, 10))
        ttk.Label(page, textvariable=self.dashboard_text, justify="left", font=("Microsoft YaHei UI", 12)).pack(anchor="w")
        ttk.Label(page, text="操作流程：维护客户 → 新增并确认广告订单 → 登记收款和费用 → 月末结账 → 导出报表。", foreground="#555").pack(anchor="w", pady=20)

    def customers(self, page):
        self.customer_vars = self.form(page, [("name", "客户名称*", ""), ("contact", "联系人", ""), ("phone", "联系电话", ""), ("address", "地址", ""), ("credit", "信用额度", "0")], self.add_customer)
        ttk.Button(page, text="删除选中客户", command=self.delete_customer).pack(anchor="w", pady=(0, 6))
        self.customer_tree = self.tree(page, [("id", "ID"), ("name", "客户名称"), ("contact", "联系人"), ("phone", "电话"), ("credit", "信用额度"), ("balance", "应收余额")], {"name": 230, "address": 200})

    def orders(self, page):
        self.order_vars = self.form(page, [("customer", "客户名称*", ""), ("project", "广告项目*", ""), ("media", "媒体/渠道", ""), ("quantity", "数量", "1"), ("price", "单价", "0"), ("tax", "税率(%)", "0"), ("date", "开单日期", self.today()), ("sales", "业务员", ""), ("start", "投放开始", self.today()), ("end", "投放结束", self.today()), ("note", "备注", "")], self.add_order)
        ttk.Button(page, text="确认选中订单", command=self.confirm_order).pack(anchor="w", pady=(0, 6))
        self.order_tree = self.tree(page, [("id", "ID"), ("number", "订单号"), ("customer", "客户"), ("project", "项目"), ("amount", "含税金额"), ("date", "开单日"), ("status", "状态"), ("balance", "未收款")], {"number": 190, "customer": 160, "project": 200})

    def receipts(self, page):
        self.receipt_vars = self.form(page, [("order", "订单号*", ""), ("amount", "收款金额*", ""), ("date", "收款日期", self.today()), ("method", "收款方式", "银行转账"), ("note", "收据号/备注", "")], self.add_receipt)
        ttk.Button(page, text="删除选中收款", command=lambda: self.delete_record("receipts", self.receipt_tree, "收款")).pack(anchor="w", pady=(0, 6))
        self.receipt_tree = self.tree(page, [("id", "ID"), ("number", "收款单号"), ("order", "订单号"), ("customer", "客户"), ("amount", "金额"), ("date", "日期"), ("method", "方式")], {"number": 190, "order": 190, "customer": 180})

    def expenses(self, page):
        self.expense_vars = self.form(page, [("vendor", "供应商*", ""), ("category", "费用科目*", "制作费"), ("amount", "金额*", ""), ("date", "费用日期", self.today()), ("note", "备注", "")], self.add_expense)
        ttk.Button(page, text="删除选中费用", command=lambda: self.delete_record("expenses", self.expense_tree, "费用")).pack(anchor="w", pady=(0, 6))
        self.expense_tree = self.tree(page, [("id", "ID"), ("number", "费用单号"), ("vendor", "供应商"), ("category", "科目"), ("amount", "金额"), ("date", "日期"), ("note", "备注")], {"number": 190, "vendor": 170, "note": 260})

    def reports(self, page):
        top = ttk.LabelFrame(page, text="月度结账", padding=10); top.pack(fill="x", pady=(0, 8))
        ttk.Label(top, text="结账月份 (YYYY-MM)：").pack(side="left")
        self.period = tk.StringVar(value=f"{date.today():%Y-%m}"); ttk.Entry(top, textvariable=self.period, width=12).pack(side="left")
        ttk.Button(top, text="执行结账", command=self.close_period).pack(side="left", padx=8)
        ttk.Button(top, text="导出当前报表 CSV…", command=self.export_report).pack(side="left")
        self.report_summary = tk.StringVar(); ttk.Label(page, textvariable=self.report_summary, font=("Microsoft YaHei UI", 11, "bold")).pack(anchor="w", pady=8)
        self.report_tree = self.tree(page, [("customer", "客户"), ("revenue", "确认开单"), ("received", "累计收款"), ("balance", "应收余额")], {"customer": 280, "revenue": 180, "received": 180, "balance": 180})
        ttk.Label(page, text="已结账月份（已结账月份的数据不可新增或删除）").pack(anchor="w", pady=(9, 2))
        self.closure_tree = self.tree(page, [("period", "期间"), ("revenue", "开单"), ("receipts", "收款"), ("expenses", "费用"), ("profit", "利润"), ("closed", "结账时间")], {"closed": 190})

    def error(self, message): messagebox.showerror("无法保存", message)
    def closed(self, day): return bool(self.db.value("SELECT 1 FROM closures WHERE period=?", (day[:7],)))
    def valid_date(self, value): datetime.strptime(value, "%Y-%m-%d")
    def add_customer(self, v):
        try:
            if not v["name"].get().strip(): raise ValueError("客户名称不能为空。")
            self.db.execute("INSERT INTO customers(name,contact,phone,address,credit_limit,created_at) VALUES(?,?,?,?,?,?)", (v["name"].get().strip(), v["contact"].get().strip(), v["phone"].get().strip(), v["address"].get().strip(), float(v["credit"].get() or 0), self.today()))
            self.refresh_all()
        except (ValueError, sqlite3.IntegrityError) as e: self.error(f"客户保存失败：{e}")
    def add_order(self, v):
        try:
            day = v["date"].get(); self.valid_date(day)
            if self.closed(day): raise ValueError("此月份已结账，不能新增订单。")
            customer = self.db.rows("SELECT id FROM customers WHERE name=? AND active=1", (v["customer"].get().strip(),))
            if not customer or not v["project"].get().strip(): raise ValueError("请输入存在的客户名称和广告项目。")
            q, p, tax = float(v["quantity"].get()), float(v["price"].get()), float(v["tax"].get() or 0)
            if q <= 0 or p < 0 or tax < 0: raise ValueError("数量须大于零，单价和税率不能为负数。")
            self.db.execute("INSERT INTO orders(number,customer_id,project,media,quantity,unit_price,tax_rate,order_date,start_date,end_date,salesperson,status,note,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (self.db.number("AD"), customer[0][0], v["project"].get().strip(), v["media"].get().strip(), q, p, tax, day, v["start"].get(), v["end"].get(), v["sales"].get().strip(), "已确认", v["note"].get().strip(), datetime.now().isoformat(timespec="seconds")))
            self.refresh_all()
        except (ValueError, sqlite3.IntegrityError) as e: self.error(f"订单保存失败：{e}")
    def add_receipt(self, v):
        try:
            day = v["date"].get(); self.valid_date(day)
            if self.closed(day): raise ValueError("此月份已结账，不能新增收款。")
            order = self.db.rows("SELECT id FROM orders WHERE number=? AND status='已确认'", (v["order"].get().strip(),)); amount = float(v["amount"].get())
            if not order or amount <= 0: raise ValueError("请输入已确认的订单号和大于零的金额。")
            self.db.execute("INSERT INTO receipts(number,order_id,amount,receipt_date,method,note,created_at) VALUES(?,?,?,?,?,?,?)", (self.db.number("RC"), order[0][0], amount, day, v["method"].get().strip(), v["note"].get().strip(), datetime.now().isoformat(timespec="seconds")))
            self.refresh_all()
        except (ValueError, sqlite3.IntegrityError) as e: self.error(f"收款保存失败：{e}")
    def add_expense(self, v):
        try:
            day = v["date"].get(); self.valid_date(day)
            if self.closed(day): raise ValueError("此月份已结账，不能新增费用。")
            amount = float(v["amount"].get())
            if not v["vendor"].get().strip() or not v["category"].get().strip() or amount <= 0: raise ValueError("供应商、费用科目和大于零的金额均为必填。")
            self.db.execute("INSERT INTO expenses(number,vendor,category,amount,expense_date,note,created_at) VALUES(?,?,?,?,?,?,?)", (self.db.number("EX"), v["vendor"].get().strip(), v["category"].get().strip(), amount, day, v["note"].get().strip(), datetime.now().isoformat(timespec="seconds")))
            self.refresh_all()
        except (ValueError, sqlite3.IntegrityError) as e: self.error(f"费用保存失败：{e}")
    def confirm_order(self):
        item = self.order_tree.selection()
        if not item: return self.error("请先选择一个订单。")
        self.db.execute("UPDATE orders SET status='已确认' WHERE id=?", (self.order_tree.item(item[0])["values"][0],)); self.refresh_all()
    def delete_customer(self): self.delete_record("customers", self.customer_tree, "客户")
    def delete_record(self, table, view, label):
        item = view.selection()
        if not item: return self.error(f"请先选择要删除的{label}。")
        row_id = view.item(item[0])["values"][0]
        day_col = {"receipts": "receipt_date", "expenses": "expense_date"}.get(table)
        if day_col and self.closed(self.db.value(f"SELECT {day_col} FROM {table} WHERE id=?", (row_id,))): return self.error("该月份已经结账，不能删除。")
        if messagebox.askyesno("确认删除", f"确定删除选中的{label}吗？"):
            try: self.db.execute(f"DELETE FROM {table} WHERE id=?", (row_id,)); self.refresh_all()
            except sqlite3.IntegrityError: self.error("该客户已有订单，不能删除。")
    def refresh_all(self):
        for tree, rows in [(self.customer_tree, self.db.rows("SELECT c.id,c.name,c.contact,c.phone,c.credit_limit, COALESCE(SUM(CASE WHEN o.status='已确认' THEN o.quantity*o.unit_price*(1+o.tax_rate/100) ELSE 0 END),0)-COALESCE((SELECT SUM(r.amount) FROM receipts r JOIN orders ro ON r.order_id=ro.id WHERE ro.customer_id=c.id),0) balance FROM customers c LEFT JOIN orders o ON o.customer_id=c.id GROUP BY c.id ORDER BY c.id DESC")), (self.order_tree, self.db.rows("SELECT o.id,o.number,c.name customer,o.project,o.quantity*o.unit_price*(1+o.tax_rate/100) amount,o.order_date,o.status,o.quantity*o.unit_price*(1+o.tax_rate/100)-COALESCE((SELECT SUM(amount) FROM receipts WHERE order_id=o.id),0) balance FROM orders o JOIN customers c ON c.id=o.customer_id ORDER BY o.id DESC")), (self.receipt_tree, self.db.rows("SELECT r.id,r.number,o.number 'order',c.name customer,r.amount,r.receipt_date,r.method FROM receipts r JOIN orders o ON o.id=r.order_id JOIN customers c ON c.id=o.customer_id ORDER BY r.id DESC")), (self.expense_tree, self.db.rows("SELECT id,number,vendor,category,amount,expense_date,note FROM expenses ORDER BY id DESC"))]:
            tree.delete(*tree.get_children())
            for row in rows:
                values = list(row); values = [self.money(x) if isinstance(x, float) and ("amount" in row.keys() or "balance" in row.keys() or "credit_limit" in row.keys()) else x for x in values]; tree.insert("", "end", values=values)
        rev = self.db.value("SELECT COALESCE(SUM(quantity*unit_price*(1+tax_rate/100)),0) FROM orders WHERE status='已确认'"); rec = self.db.value("SELECT COALESCE(SUM(amount),0) FROM receipts"); exp = self.db.value("SELECT COALESCE(SUM(amount),0) FROM expenses")
        self.dashboard_text.set(f"累计确认开单：{self.money(rev)}\n累计收款：{self.money(rec)}\n累计费用：{self.money(exp)}\n累计应收：{self.money(rev-rec)}\n累计经营利润：{self.money(rev-exp)}")
        report = self.db.rows("SELECT c.name customer,COALESCE(SUM(o.quantity*o.unit_price*(1+o.tax_rate/100)),0) revenue,COALESCE((SELECT SUM(r.amount) FROM receipts r JOIN orders oo ON oo.id=r.order_id WHERE oo.customer_id=c.id),0) received FROM customers c LEFT JOIN orders o ON o.customer_id=c.id AND o.status='已确认' GROUP BY c.id HAVING revenue<>0 OR received<>0")
        self.report_tree.delete(*self.report_tree.get_children())
        for r in report: self.report_tree.insert("", "end", values=(r["customer"], self.money(r["revenue"]), self.money(r["received"]), self.money(r["revenue"]-r["received"])))
        self.report_summary.set(f"客户应收报表：确认开单 {self.money(rev)}  |  收款 {self.money(rec)}  |  应收余额 {self.money(rev-rec)}  |  费用 {self.money(exp)}")
        self.closure_tree.delete(*self.closure_tree.get_children())
        for r in self.db.rows("SELECT period,revenue,receipts,expenses,profit,closed_at FROM closures ORDER BY period DESC"): self.closure_tree.insert("", "end", values=(r["period"], self.money(r["revenue"]), self.money(r["receipts"]), self.money(r["expenses"]), self.money(r["profit"]), r["closed_at"]))
    def close_period(self):
        period = self.period.get()
        try: datetime.strptime(period, "%Y-%m")
        except ValueError: return self.error("月份格式必须为 YYYY-MM。")
        if self.closed(period): return self.error("该月份已经结账。")
        if not messagebox.askyesno("确认结账", f"确认结账 {period}？之后该月份不能再增加或删除业务数据。"): return
        rev = self.db.value("SELECT COALESCE(SUM(quantity*unit_price*(1+tax_rate/100)),0) FROM orders WHERE status='已确认' AND order_date LIKE ?", (period+"%",)); rec = self.db.value("SELECT COALESCE(SUM(amount),0) FROM receipts WHERE receipt_date LIKE ?", (period+"%",)); exp = self.db.value("SELECT COALESCE(SUM(amount),0) FROM expenses WHERE expense_date LIKE ?", (period+"%",))
        self.db.execute("INSERT INTO closures VALUES(?,?,?,?,?,?,?)", (period, rev, rec, exp, rev-rec, rev-exp, datetime.now().isoformat(timespec="seconds"))); self.refresh_all(); messagebox.showinfo("结账完成", f"{period} 已结账。")
    def export_report(self):
        path = filedialog.asksaveasfilename(title="导出客户应收报表", defaultextension=".csv", filetypes=[("CSV 文件", "*.csv")], initialfile=f"客户应收报表_{date.today()}.csv")
        if not path: return
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f); writer.writerow(["客户", "确认开单", "累计收款", "应收余额"])
            for item in self.report_tree.get_children(): writer.writerow(self.report_tree.item(item)["values"])
        messagebox.showinfo("导出完成", f"报表已导出到：\n{path}")
    def backup(self):
        target = filedialog.asksaveasfilename(title="备份数据库", defaultextension=".db", initialfile=f"广告ERP备份_{date.today()}.db", filetypes=[("SQLite 数据库", "*.db")])
        if target: self.db.conn.commit(); shutil.copy2(self.db.path, target); messagebox.showinfo("备份完成", f"数据库已备份到：\n{target}")
    def show_db_path(self): messagebox.showinfo("数据文件位置", str(self.db.path))

if __name__ == "__main__":
    ERP().mainloop()
