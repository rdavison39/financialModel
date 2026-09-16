import tkinter as tk
from datetime import date, datetime, timedelta
from decimal import Decimal
from tkinter import messagebox, ttk
from sqlalchemy import select

from src.database import get_session
from src.database_init import initialize_database
from src.models.portfolio_snapshot import PortfolioSnapshot
from src.services.portfolio_comparison_service import PortfolioComparisonService

class ComparisonTab(ttk.Frame):
    CONSOLIDATED = "Consolidated Portfolio"

    def __init__(self, parent: tk.Misc) -> None:
        super().__init__(parent)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(4, weight=1)
        self.accounts = {}
        self._build_ui()
        self.after(100, self._load_accounts)

    def _build_ui(self):
        ttk.Label(self, text="Portfolio Comparison",
                  font=("Segoe UI", 18, "bold")).grid(row=0, column=0, sticky="w", pady=(0,15))
        controls = ttk.Frame(self)
        controls.grid(row=1, column=0, sticky="ew", pady=(0,10))
        ttk.Label(controls, text="Scope:").pack(side="left")
        self.scope = tk.StringVar(value=self.CONSOLIDATED)
        self.combo = ttk.Combobox(controls, textvariable=self.scope, state="readonly", width=42)
        self.combo.pack(side="left", padx=(6,20))
        self.combo.bind("<<ComboboxSelected>>", lambda e: self._set_heading())
        ttk.Label(controls, text="From:").pack(side="left")
        self.from_var = tk.StringVar()
        ttk.Entry(controls, textvariable=self.from_var, width=12).pack(side="left", padx=5)
        ttk.Label(controls, text="To:").pack(side="left")
        self.to_var = tk.StringVar()
        ttk.Entry(controls, textvariable=self.to_var, width=12).pack(side="left", padx=5)
        ttk.Button(controls, text="Compare", command=self._compare).pack(side="left", padx=8)

        self.heading = ttk.Label(self, text=self.CONSOLIDATED,
                                 font=("Segoe UI", 13, "bold"))
        self.heading.grid(row=2, column=0, sticky="w", pady=(0,8))

        summary = ttk.Frame(self)
        summary.grid(row=3, column=0, sticky="ew", pady=(0,8))
        self.from_value = self._summary(summary, "From Value:", 0)
        self.to_value = self._summary(summary, "To Value:", 2)
        self.change = self._summary(summary, "Change:", 4)
        self.count = ttk.Label(summary, text="Holdings: --")
        self.count.grid(row=0, column=6, padx=20)

        frame = ttk.Frame(self)
        frame.grid(row=4, column=0, sticky="nsew")
        frame.columnconfigure(0, weight=1); frame.rowconfigure(0, weight=1)
        cols = ("symbol","company","q1","q2","dq","a1","a2","mv1","mv2","g1","g2","status")
        self.tree = ttk.Treeview(frame, columns=cols, show="headings")
        heads = {
            "symbol":"Symbol","company":"Company","q1":"Qty From","q2":"Qty To",
            "dq":"Qty Change","a1":"Avg Cost From","a2":"Avg Cost To",
            "mv1":"Market Value From","mv2":"Market Value To",
            "g1":"Unrealized Gain From","g2":"Unrealized Gain To","status":"Status"
        }
        widths = [100,220,90,90,100,115,115,140,140,145,145,100]
        for c,w in zip(cols,widths):
            self.tree.heading(c, text=heads[c])
            self.tree.column(c, width=w, minwidth=70, stretch=False,
                             anchor="w" if c in ("symbol","company","status") else "e")
        self.tree.grid(row=0,column=0,sticky="nsew")
        sb=ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        sb.grid(row=0,column=1,sticky="ns"); self.tree.configure(yscrollcommand=sb.set)
        self.tree.tag_configure("increase", foreground="green")
        self.tree.tag_configure("decrease", foreground="red")
        self.tree.tag_configure("neutral", foreground="black")
        self.status=ttk.Label(self,text="")
        self.status.grid(row=5,column=0,sticky="w",pady=(8,0))

    @staticmethod
    def _summary(parent, label, col):
        ttk.Label(parent,text=label,font=("Segoe UI",10,"bold")).grid(row=0,column=col,sticky="e")
        v=ttk.Label(parent,text="--"); v.grid(row=0,column=col+1,sticky="w",padx=(5,0))
        return v

    def _load_accounts(self):
        session=None
        try:
            initialize_database(); session=get_session()
            rows=PortfolioComparisonService(session).get_accounts()
            self.accounts={
                f"{x.brokerage_name} — Account {x.account_number}"
                + (f" — {x.account_name}" if x.account_name else ""): x.account_id
                for x in rows
            }
            self.combo["values"]=[self.CONSOLIDATED,*self.accounts.keys()]
            self.combo.current(0)
            snaps=session.scalars(select(PortfolioSnapshot.snapshot_date).distinct()
                                  .order_by(PortfolioSnapshot.snapshot_date.desc()).limit(2)).all()
            if len(snaps)>=2:
                self.to_var.set(self._fmt_date(snaps[0])); self.from_var.set(self._fmt_date(snaps[1]))
            elif snaps:
                self.to_var.set(self._fmt_date(snaps[0])); self.from_var.set(self._fmt_date(snaps[0]))
            else:
                d=date.today(); self.to_var.set(self._fmt_date(d)); self.from_var.set(self._fmt_date(d-timedelta(days=1)))
        except Exception as e:
            self.status.configure(text=f"Unable to load accounts: {type(e).__name__}: {e}")
        finally:
            if session: session.close()

    def _set_heading(self): self.heading.configure(text=self.scope.get())
    @staticmethod
    def _fmt_date(d): return d.strftime("%Y-%m-%d")
    @staticmethod
    def _date(s): return datetime.strptime(s.strip(),"%Y-%m-%d").date()
    @staticmethod
    def _qty(v):
        if v is None: return "--"
        if v == v.to_integral_value(): return f"{int(v):,}"
        return f"{v:,.4f}".rstrip("0").rstrip(".")
    @classmethod
    def _sq(cls,v):
        if v is None:return "--"
        return ("+" if v>0 else "")+cls._qty(v)
    @staticmethod
    def _money(v):
        return "--" if v is None else f"${v:,.2f}"
    @staticmethod
    def _smoney(v):
        if v is None:return "--"
        if v==0:return "$0.00"
        return ("+" if v>0 else "-")+f"${abs(v):,.2f}"

    def _compare(self):
        try:
            d1,d2=self._date(self.from_var.get()),self._date(self.to_var.get())
            if d1>d2:
                messagebox.showwarning("Portfolio Comparison","From date must be on or before To date."); return
            initialize_database(); session=get_session()
            try:
                aid=self.accounts.get(self.scope.get())
                result=PortfolioComparisonService(session).compare(d1,d2,aid)
            finally: session.close()
            self._display(result,d1,d2)
        except ValueError:
            messagebox.showwarning("Portfolio Comparison","Enter dates using YYYY-MM-DD.")
        except Exception as e:
            messagebox.showerror("Portfolio Comparison",f"Unable to compare portfolios:\n\n{type(e).__name__}: {e}")

    def _display(self,r,d1,d2):
        self._set_heading()
        self.from_value.configure(text=self._money(r.first_value))
        self.to_value.configure(text=self._money(r.second_value))
        self.change.configure(text=self._smoney(r.value_difference))
        active=[p for p in r.positions if p.first_quantity!=0 or p.second_quantity!=0]
        self.count.configure(text=f"Holdings: {len(active)}")
        for item in self.tree.get_children(): self.tree.delete(item)
        for p in r.positions:
            tag="increase" if p.quantity_difference>0 else "decrease" if p.quantity_difference<0 else "neutral"
            self.tree.insert("", "end", values=(
                p.symbol,p.company_name,self._qty(p.first_quantity),self._qty(p.second_quantity),
                self._sq(p.quantity_difference),self._money(p.first_average_cost),self._money(p.second_average_cost),
                self._money(p.first_market_value),self._money(p.second_market_value),
                self._smoney(p.first_unrealized_gain),self._smoney(p.second_unrealized_gain),p.status
            ),tags=(tag,))
        self.status.configure(text=f"{d1:%Y-%m-%d} → {d2:%Y-%m-%d}   {len(active)} active holdings")
