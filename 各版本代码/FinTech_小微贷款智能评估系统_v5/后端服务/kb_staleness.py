"""
v5 知识库时效性检查模块
定期扫描 kb/data/ 中所有政策、案例的最后验证日期，标记过期或即将过期的条目。
"""

import os
import csv
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

KB_DATA = Path(__file__).resolve().parent.parent.parent / "kb" / "data"

# 时效阈值
WARN_DAYS = 90     # 3个月未验证 → 警告
STALE_DAYS = 180   # 6个月未验证 → 过期
EXPIRY_DAYS = 365  # 1年 → 严重过期


def check_all() -> dict:
    """
    扫描所有知识库文件，返回时效性报告。
    """
    report = {
        "checked_at": datetime.now().isoformat(),
        "total_entries": 0,
        "fresh": 0,
        "warning": [],      # 即将过期
        "stale": [],        # 已过期
        "expired": [],      # 严重过期
        "no_date": [],      # 无日期字段
        "files": {},
    }

    # 扫描各类型文件
    for csv_name in ["national_policies.csv", "provincial_policies.csv"]:
        rows = _read_csv(str(KB_DATA / "policies" / csv_name))
        _check_rows(rows, csv_name, report, date_field="last_verified_at")

    for csv_name in ["teaching_cases_basic.csv", "teaching_cases_enhanced.csv"]:
        rows = _read_csv(str(KB_DATA / "cases" / csv_name))
        _check_rows(rows, csv_name, report, date_field="created_at")

    rows = _read_csv(str(KB_DATA / "governance" / "data_source_registry.csv"))
    _check_rows(rows, "data_source_registry.csv", report, date_field="last_verified_at")

    report["stale_count"] = len(report["stale"])
    report["expired_count"] = len(report["expired"])
    report["warning_count"] = len(report["warning"])
    report["health_score"] = max(0, 100 - len(report["stale"]) * 5 - len(report["expired"]) * 15)

    return report


def _check_rows(rows: list[dict], filename: str, report: dict, date_field: str):
    now = datetime.now()
    for row in rows:
        report["total_entries"] += 1
        date_str = row.get(date_field, "").strip()

        if not date_str:
            report["no_date"].append({
                "file": filename,
                "entry": row.get("document_title", row.get("case_id", row.get("id", "unknown"))),
                "field": date_field,
            })
            continue

        try:
            # 尝试多种日期格式
            for fmt in ["%Y-%m-%d", "%Y/%m/%d", "%Y-%m-%dT%H:%M:%S", "%Y%m%d"]:
                try:
                    d = datetime.strptime(date_str[:10], fmt)
                    break
                except ValueError:
                    continue
            else:
                report["no_date"].append({"file": filename, "entry": date_str, "field": date_field})
                continue

            days_ago = (now - d).days
            entry_info = {
                "file": filename,
                "entry": row.get("document_title", row.get("case_id", row.get("name", "unknown"))),
                "last_verified": date_str,
                "days_ago": days_ago,
            }

            if days_ago > EXPIRY_DAYS:
                report["expired"].append(entry_info)
            elif days_ago > STALE_DAYS:
                report["stale"].append(entry_info)
            elif days_ago > WARN_DAYS:
                report["warning"].append(entry_info)
            else:
                report["fresh"] += 1

        except Exception:
            report["no_date"].append({"file": filename, "entry": date_str, "field": date_field})


def get_staleness_summary() -> str:
    """生成可读摘要（供 Agent 使用）"""
    r = check_all()
    lines = [
        f"知识库时效性检查 ({r['checked_at'][:10]})",
        f"总条目: {r['total_entries']} | 新鲜: {r['fresh']} | 健康分: {r['health_score']}/100",
    ]
    if r["expired"]:
        lines.append(f"严重过期 ({len(r['expired'])}条): {', '.join(e['entry'][:30] for e in r['expired'][:3])}")
    if r["stale"]:
        lines.append(f"已过期 ({len(r['stale'])}条): {', '.join(e['entry'][:30] for e in r['stale'][:3])}")
    if r["warning"]:
        lines.append(f"即将过期 ({len(r['warning'])}条): 建议在 1 个月内更新")
    if not r["stale"] and not r["expired"]:
        lines.append("所有知识库条目均在有效期内。")
    return "\n".join(lines)


def _read_csv(path: str) -> list[dict]:
    if not os.path.exists(path):
        return []
    rows = []
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append({k.strip(): (v.strip() if v else "") for k, v in row.items() if k and k.strip()})
    except Exception:
        pass
    return rows
