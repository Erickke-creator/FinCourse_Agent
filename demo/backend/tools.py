"""
DeFi 协议健康度监控 Agent — 工具函数 & Schema 定义
数据源：DefiLlama API（免费、无需认证）
"""

import httpx
import time
from typing import Optional

# ============================================================
# 内存缓存（避免重复请求 DefiLlama API）
# ============================================================
_cache: dict = {}
CACHE_TTL = 60  # 秒


def _cache_get(key: str) -> Optional[dict]:
    if key in _cache:
        data, ts = _cache[key]
        if time.time() - ts < CACHE_TTL:
            return data
        del _cache[key]
    return None


def _cache_set(key: str, data: dict):
    _cache[key] = (data, time.time())


# ============================================================
# 工具函数
# ============================================================
DEFILLAMA_BASE = "https://api.llama.fi"

PROTOCOL_ALIASES = {
    "aave": "aave-v3", "aave v3": "aave-v3", "aavev3": "aave-v3",
    "compound": "compound-v3", "compound v3": "compound-v3", "compoundv3": "compound-v3",
    "maker": "makerdao", "makerdao": "makerdao", "sky": "makerdao",
    "lido": "lido",
    "uniswap": "uniswap-v3", "uni": "uniswap-v3",
    "curve": "curve-dex", "curve dex": "curve-dex",
    "morpho": "morpho-blue", "morpho blue": "morpho-blue",
    "eigenlayer": "eigenlayer",
}


def _resolve_name(name: str) -> str:
    lowered = name.lower().strip()
    return PROTOCOL_ALIASES.get(lowered, lowered.replace(" ", "-"))


def _extract_current_tvl(tvl_field) -> float:
    """
    从 DefiLlama tvl 字段提取当前 TVL 数值。
    tvl 字段可能是 float（列表接口）或 list（详情接口的时间序列）。
    """
    if isinstance(tvl_field, (int, float)):
        return float(tvl_field)
    if isinstance(tvl_field, list) and tvl_field:
        last = tvl_field[-1]
        if isinstance(last, dict):
            return float(last.get("totalLiquidityUSD", 0))
    return 0.0


def _parse_chain_tvls(chain_tvls: dict) -> dict:
    """
    从 chainTvls 解析借贷供需数据。

    chainTvls 结构:
      "{chain}"         → supply/deposit side (tvl 数组)
      "{chain}-borrowed" → borrow side (tvl 数组)

    返回: {chain: {supply_usd, borrow_usd, utilization, risk_level}, ...}
    """
    chains = {}

    for key, val in chain_tvls.items():
        if not isinstance(val, dict):
            continue

        # 判断是 supply 还是 borrow
        is_borrow = key.endswith("-borrowed") or key == "borrowed"
        chain_name = key.replace("-borrowed", "") if key.endswith("-borrowed") else key

        # 跳过无效链名（如 "-borrowed" 剥离后为空 或 单独的 "borrowed" 聚合条目）
        if not chain_name or chain_name == "borrowed":
            continue

        if chain_name not in chains:
            chains[chain_name] = {"supply_usd": 0.0, "borrow_usd": 0.0}

        tvl_arr = val.get("tvl", [])
        latest_tvl = 0.0
        if isinstance(tvl_arr, list) and tvl_arr:
            last = tvl_arr[-1]
            if isinstance(last, dict):
                latest_tvl = float(last.get("totalLiquidityUSD", 0))
        elif isinstance(tvl_arr, (int, float)):
            latest_tvl = float(tvl_arr)

        if is_borrow:
            chains[chain_name]["borrow_usd"] = latest_tvl
        else:
            chains[chain_name]["supply_usd"] = latest_tvl

    # 计算每链利用率
    result = {}
    for chain, data in chains.items():
        supply = data["supply_usd"]
        borrow = data["borrow_usd"]
        util = borrow / supply if supply > 0 else 0.0
        result[chain] = {
            **data,
            "utilization": round(util, 4),
            "risk_level": assess_risk(util),
        }

    return result


async def get_protocol_tvl(name: str) -> dict:
    """
    获取指定 DeFi 协议的当前 TVL 及多链分布。
    API: GET https://api.llama.fi/protocol/{slug}
    """
    slug = _resolve_name(name)
    cache_key = f"tvl:{slug}"

    cached = _cache_get(cache_key)
    if cached:
        cached["_cached"] = True
        return cached

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{DEFILLAMA_BASE}/protocol/{slug}")
            if resp.status_code == 404:
                return {
                    "success": False,
                    "error": f"未找到协议 '{name}'，请检查名称是否正确",
                }
            resp.raise_for_status()
            data = resp.json()

        # tvl 可能是时间序列数组或单值
        tvl = _extract_current_tvl(data.get("tvl", 0))

        # 链列表
        chains = data.get("chains", [])

        result = {
            "success": True,
            "name": data.get("name", slug),
            "slug": slug,
            "tvl_usd": tvl,
            "tvl_display": _format_tvl(tvl),
            "chains": chains,
            "chain_count": len(chains),
            "category": data.get("category", "Unknown"),
            "url": data.get("url", ""),
            "logo": data.get("logo", ""),
            "description": (data.get("description") or "")[:200],
            "_cached": False,
        }
        _cache_set(cache_key, result)
        return result

    except httpx.TimeoutException:
        return {"success": False, "error": "DefiLlama API 请求超时，请稍后重试"}
    except Exception as e:
        return {"success": False, "error": f"数据获取失败: {str(e)}"}


async def get_lending_data(name: str) -> dict:
    """
    获取借贷协议的供需和利用率数据。
    从 /protocol/{slug} 的 chainTvls 字段解析借贷数据（不依赖已失效的 /lends 端点）。
    """
    slug = _resolve_name(name)
    cache_key = f"lend:{slug}"

    cached = _cache_get(cache_key)
    if cached:
        cached["_cached"] = True
        return cached

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{DEFILLAMA_BASE}/protocol/{slug}")
            if resp.status_code == 404:
                return {
                    "success": False,
                    "error": f"未找到协议 '{name}'",
                }
            resp.raise_for_status()
            data = resp.json()

        chain_tvls = data.get("chainTvls", {})
        category = data.get("category", "")

        # 检查是否是借贷类协议
        is_lending = any(t in category.lower() for t in ["lending", "cdp"])

        if not chain_tvls:
            return {
                "success": True,
                "name": slug,
                "has_lending_data": False,
                "category": category,
                "message": f"'{data.get('name', slug)}' 没有链级别 TVL 分解数据",
            }

        # 解析 chainTvls 获取每链供需
        chains = _parse_chain_tvls(chain_tvls)

        if not chains:
            return {
                "success": True,
                "name": slug,
                "has_lending_data": False,
                "category": category,
                "message": f"'{data.get('name', slug)}' 暂无借贷利用率数据",
            }

        # 汇总
        total_supply = sum(c["supply_usd"] for c in chains.values())
        total_borrow = sum(c["borrow_usd"] for c in chains.values())
        total_util = total_borrow / total_supply if total_supply > 0 else 0.0

        # 按利用率排序的链详情
        chain_list = sorted(
            [
                {
                    "chain": chain,
                    "supply_usd": c["supply_usd"],
                    "supply_display": _format_tvl(c["supply_usd"]),
                    "borrow_usd": c["borrow_usd"],
                    "borrow_display": _format_tvl(c["borrow_usd"]),
                    "utilization": c["utilization"],
                    "utilization_pct": f"{c['utilization'] * 100:.1f}%",
                    "risk_level": c["risk_level"],
                }
                for chain, c in chains.items()
                if c["supply_usd"] > 0  # 过滤无供应数据的链
            ],
            key=lambda x: x["utilization"],
            reverse=True,
        )

        # 高利用率预警
        high_risk_chains = [c for c in chain_list if c["utilization"] > 0.80]

        result = {
            "success": True,
            "name": data.get("name", slug),
            "slug": slug,
            "category": category,
            "has_lending_data": True,
            "total_supply_usd": total_supply,
            "total_supply_display": _format_tvl(total_supply),
            "total_borrow_usd": total_borrow,
            "total_borrow_display": _format_tvl(total_borrow),
            "utilization": round(total_util, 4),
            "utilization_pct": f"{total_util * 100:.1f}%",
            "risk_level": assess_risk(total_util),
            "chain_count": len(chain_list),
            "high_risk_chains": high_risk_chains,
            "all_chains": chain_list[:10],  # 最多展示 10 条链
            "_cached": False,
        }
        _cache_set(cache_key, result)
        return result

    except httpx.TimeoutException:
        return {"success": False, "error": "DefiLlama API 请求超时"}
    except Exception as e:
        return {"success": False, "error": f"数据获取失败: {str(e)}"}


async def get_top_protocols(limit: int = 20) -> dict:
    """
    获取 TVL Top N 协议列表（用于仪表盘）。
    API: GET https://api.llama.fi/protocols
    """
    cache_key = f"top:{limit}"

    cached = _cache_get(cache_key)
    if cached:
        cached["_cached"] = True
        return cached

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(f"{DEFILLAMA_BASE}/protocols")
            resp.raise_for_status()
            data = resp.json()

        protocols = []
        for p in data[:limit]:
            tvl = _extract_current_tvl(p.get("tvl", 0))
            protocols.append({
                "name": p.get("name", ""),
                "slug": p.get("slug", ""),
                "tvl_usd": tvl,
                "tvl_display": _format_tvl(tvl),
                "chains": (p.get("chains", []) or [])[:5],
                "chain_count": len(p.get("chains", []) or []),
                "category": p.get("category", "Unknown"),
                "logo": p.get("logo", ""),
            })

        result = {
            "success": True,
            "total_protocols": len(data),
            "displayed": len(protocols),
            "protocols": protocols,
            "_cached": False,
        }
        _cache_set(cache_key, result)
        return result

    except httpx.TimeoutException:
        return {"success": False, "error": "DefiLlama API 请求超时"}
    except Exception as e:
        return {"success": False, "error": f"数据获取失败: {str(e)}"}


def assess_risk(utilization_rate: float) -> str:
    """
    根据借贷利用率评估清算风险等级。
    >100% 视为数据异常（新链数据不完整）。
    """
    if utilization_rate > 1.0:
        return "⚪ 数据异常"
    elif utilization_rate > 0.95:
        return "🔴 高风险"
    elif utilization_rate > 0.80:
        return "🟡 中等风险"
    elif utilization_rate > 0.60:
        return "🟢 较低风险"
    else:
        return "🟢 低风险"


def _format_tvl(tvl: float) -> str:
    """将 TVL 数值格式化为人类可读字符串"""
    if tvl is None or tvl == 0:
        return "$0"
    abs_tvl = abs(tvl)
    if abs_tvl >= 1e9:
        return f"${tvl / 1e9:.2f}B"
    elif abs_tvl >= 1e6:
        return f"${tvl / 1e6:.2f}M"
    elif abs_tvl >= 1e3:
        return f"${tvl / 1e3:.2f}K"
    else:
        return f"${tvl:.2f}"


# ============================================================
# Tool Schema（供 DeepSeek V4 Function Call 注册）
# ============================================================
TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "get_protocol_tvl",
            "description": "获取指定 DeFi 协议的当前总锁仓价值（TVL）及多链部署情况。",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "协议名称，如 'aave', 'aave-v3', 'compound-v3', 'lido', 'uniswap'"
                    }
                },
                "required": ["name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_lending_data",
            "description": "获取借贷协议的供需数据、利用率和清算风险。返回总供应量、总借贷量、利用率、各链风险等级和高风险链列表。",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "借贷协议名称，如 'aave-v3', 'compound-v3', 'morpho-blue'"
                    }
                },
                "required": ["name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_top_protocols",
            "description": "获取当前 TVL 排名前 N 的 DeFi 协议概览，用于仪表盘和横向对比。",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "返回协议数量，默认 20"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "assess_risk",
            "description": "根据借贷利用率评估清算风险等级。利用率>95%=高风险, 80-95%=中等风险, <80%=低风险。",
            "parameters": {
                "type": "object",
                "properties": {
                    "utilization_rate": {
                        "type": "number",
                        "description": "借贷利用率，如 0.72 表示 72%"
                    }
                },
                "required": ["utilization_rate"]
            }
        }
    }
]

TOOL_MAP = {
    "get_protocol_tvl": get_protocol_tvl,
    "get_lending_data": get_lending_data,
    "get_top_protocols": get_top_protocols,
    "assess_risk": lambda **kwargs: {"success": True, "result": assess_risk(kwargs["utilization_rate"])},
}
