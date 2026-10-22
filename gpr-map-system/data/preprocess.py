#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GPR 数据预处理脚本（仅使用 Python 标准库，可在 Docker 构建阶段直接运行）

输入：
    gpr_raw.csv         由 Iacoviello 官方 data_gpr_export.xls 导出的 2020-2026 原始数据
    world_raw.geojson   Natural Earth 1:110m 国家边界

输出：
    gpr_data.csv        清洗后的长表（含缺失标记与风险等级）
    gpr_monthly.json    前端可视化数据（国家序列、全球序列、阈值、事件）
    world.geojson       精简后的国家边界（ISO_A3 + 中英文名）

用法：
    python preprocess.py
    python preprocess.py --raw gpr_raw.csv --geojson world_raw.geojson --outdir .
"""

import argparse
import csv
import json
import math
import os
from collections import OrderedDict

# ---------------------------------------------------------------------------
# 配置
# ---------------------------------------------------------------------------
# 官方数据最后更新于 2026-10-01，最新完整月份为 2026-09
START_MONTH = "2020-01"
END_MONTH = "2026-09"

# 5 档阈值（单位：GPRC，占报纸文章比例 %）；左闭右开
THRESHOLDS = [0.05, 0.15, 0.35, 1.00]
COLORS = ["#2b9348", "#8ac926", "#ffd166", "#f77f00", "#c1121f"]
RISK_LEVELS = ["低风险", "较低风险", "中等风险", "高风险", "极高风险"]
RANGE_LABELS = ["< 0.05", "0.05 – 0.15", "0.15 – 0.35", "0.35 – 1.00", "≥ 1.00"]

# 44 个 GPRC 国家/地区：ISO3 -> (英文名, 中文名, 区域)
COUNTRY_META = OrderedDict([
    ("ARG", ("Argentina", "阿根廷", "南美洲")),
    ("AUS", ("Australia", "澳大利亚", "大洋洲")),
    ("BEL", ("Belgium", "比利时", "欧洲")),
    ("BRA", ("Brazil", "巴西", "南美洲")),
    ("CAN", ("Canada", "加拿大", "北美洲")),
    ("CHE", ("Switzerland", "瑞士", "欧洲")),
    ("CHL", ("Chile", "智利", "南美洲")),
    ("CHN", ("China", "中国", "亚洲")),
    ("COL", ("Colombia", "哥伦比亚", "南美洲")),
    ("DEU", ("Germany", "德国", "欧洲")),
    ("DNK", ("Denmark", "丹麦", "欧洲")),
    ("EGY", ("Egypt", "埃及", "非洲")),
    ("ESP", ("Spain", "西班牙", "欧洲")),
    ("FIN", ("Finland", "芬兰", "欧洲")),
    ("FRA", ("France", "法国", "欧洲")),
    ("GBR", ("United Kingdom", "英国", "欧洲")),
    ("HKG", ("Hong Kong, China", "中国香港", "亚洲")),
    ("HUN", ("Hungary", "匈牙利", "欧洲")),
    ("IDN", ("Indonesia", "印度尼西亚", "亚洲")),
    ("IND", ("India", "印度", "亚洲")),
    ("ISR", ("Israel", "以色列", "中东")),
    ("ITA", ("Italy", "意大利", "欧洲")),
    ("JPN", ("Japan", "日本", "亚洲")),
    ("KOR", ("South Korea", "韩国", "亚洲")),
    ("MEX", ("Mexico", "墨西哥", "北美洲")),
    ("MYS", ("Malaysia", "马来西亚", "亚洲")),
    ("NLD", ("Netherlands", "荷兰", "欧洲")),
    ("NOR", ("Norway", "挪威", "欧洲")),
    ("PER", ("Peru", "秘鲁", "南美洲")),
    ("PHL", ("Philippines", "菲律宾", "亚洲")),
    ("POL", ("Poland", "波兰", "欧洲")),
    ("PRT", ("Portugal", "葡萄牙", "欧洲")),
    ("RUS", ("Russia", "俄罗斯", "欧洲")),
    ("SAU", ("Saudi Arabia", "沙特阿拉伯", "中东")),
    ("SWE", ("Sweden", "瑞典", "欧洲")),
    ("THA", ("Thailand", "泰国", "亚洲")),
    ("TUN", ("Tunisia", "突尼斯", "非洲")),
    ("TUR", ("Turkey", "土耳其", "中东")),
    ("TWN", ("Taiwan, China", "中国台湾", "亚洲")),
    ("UKR", ("Ukraine", "乌克兰", "欧洲")),
    ("USA", ("United States", "美国", "北美洲")),
    ("VEN", ("Venezuela", "委内瑞拉", "南美洲")),
    ("VNM", ("Vietnam", "越南", "亚洲")),
    ("ZAF", ("South Africa", "南非", "非洲")),
])

# 重大地缘政治事件（人工整理，用于地图标注）
EVENTS = [
    ("2020-01", "新冠疫情全球蔓延", 30.59, 114.30,
     "新冠疫情暴发并迅速扩散至全球，冲击供应链、人员流动与国际合作，成为 2020 年全球风险的主要来源。"),
    ("2020-05", "中印加勒万河谷冲突", 35.20, 78.50,
     "中印两国边防部队在加勒万河谷发生肢体冲突，边境紧张局势显著升级。"),
    ("2020-11", "美国总统大选与权力交接", 38.90, -77.04,
     "美国总统选举引发政治极化与权力交接争议，加剧政策不确定性。"),
    ("2021-02", "缅甸军事政变", 19.75, 96.10,
     "缅甸军方扣押民选政府领导人并接管政权，国内冲突与地区不确定性上升。"),
    ("2021-08", "阿富汗塔利班接管喀布尔", 34.53, 69.17,
     "美军撤离后塔利班迅速接管喀布尔，阿富汗政局剧变并引发人道主义危机。"),
    ("2022-02", "俄乌冲突全面爆发", 50.45, 30.52,
     "俄罗斯对乌克兰发起特别军事行动，欧洲安全格局重塑，能源与粮食市场剧烈波动。"),
    ("2022-08", "台海局势紧张", 25.03, 121.56,
     "美国众议院议长访台引发台海局势紧张，区域军事活动与外交博弈升级。"),
    ("2023-04", "苏丹内战爆发", 15.50, 32.55,
     "苏丹武装部队与快速支援部队爆发内战，首都喀土穆陷入冲突。"),
    ("2023-10", "巴以新一轮冲突", 31.50, 34.47,
     "哈马斯袭击以色列后以色列对加沙发动大规模军事行动，中东局势急剧升温。"),
    ("2024-01", "红海航运危机", 12.60, 43.30,
     "胡塞武装袭击红海商船，主要航运公司绕行好望角，全球供应链承压。"),
    ("2024-04", "伊朗与以色列直接冲突", 35.70, 51.40,
     "伊朗向以色列发射无人机与导弹，双方首次发生大规模直接军事对抗。"),
    ("2025-06", "以伊军事冲突升级", 31.77, 35.21,
     "以色列与伊朗爆发持续军事冲突，中东地缘风险与国际油价显著波动。"),
]


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------
def month_range(start, end):
    """生成 YYYY-MM 月份序列（含首尾）。"""
    y0, m0 = map(int, start.split("-"))
    y1, m1 = map(int, end.split("-"))
    months = []
    y, m = y0, m0
    while (y, m) <= (y1, m1):
        months.append("%04d-%02d" % (y, m))
        m += 1
        if m == 13:
            y, m = y + 1, 1
    return months


def to_float(value):
    if value is None:
        return None
    text = str(value).strip()
    if text == "" or text.lower() in ("na", "nan", "null", "none", "."):
        return None
    try:
        value = float(text)
    except ValueError:
        return None
    if math.isnan(value) or math.isinf(value):
        return None
    return value


def risk_index(value):
    if value is None:
        return None
    for i, threshold in enumerate(THRESHOLDS):
        if value < threshold:
            return i
    return len(THRESHOLDS)


def risk_level(value):
    idx = risk_index(value)
    return None if idx is None else RISK_LEVELS[idx]


def round_coords(obj, digits=3):
    """递归压缩 GeoJSON 坐标精度。"""
    if isinstance(obj, (list, tuple)):
        return [round_coords(x, digits) for x in obj]
    if isinstance(obj, float):
        return round(obj, digits)
    return obj


def compact_geojson(src_path, dst_path):
    with open(src_path, "r", encoding="utf-8") as fh:
        data = json.load(fh)

    features = []
    for feature in data.get("features", []):
        props = feature.get("properties") or {}
        geometry = feature.get("geometry")
        if not geometry:
            continue
        iso = props.get("ISO_A3")
        if not iso or iso in ("-99", "-99.0"):
            iso = props.get("ISO_A3_EH")
        if not iso or iso in ("-99", "-99.0"):
            iso = props.get("ADM0_A3")
        if not iso:
            continue
        name_en = props.get("NAME_EN") or props.get("NAME") or iso
        name_zh = props.get("NAME_ZH") or name_en
        features.append({
            "type": "Feature",
            "properties": {
                "iso3": iso,
                "name_en": name_en,
                "name_zh": name_zh,
            },
            "geometry": {
                "type": geometry.get("type"),
                "coordinates": round_coords(geometry.get("coordinates")),
            },
        })

    output = {"type": "FeatureCollection", "features": features}
    with open(dst_path, "w", encoding="utf-8") as fh:
        json.dump(output, fh, ensure_ascii=False, separators=(",", ":"))
    return len(features)


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------
def build(raw_path, geojson_path, outdir):
    months = month_range(START_MONTH, END_MONTH)
    month_set = set(months)

    with open(raw_path, "r", encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))

    # 原始列：month, GPR, GPRC_ARG ...
    raw = {}
    global_series = {}
    for row in rows:
        month = (row.get("month") or "").strip()[:7]
        if month not in month_set:
            continue
        global_series[month] = to_float(row.get("GPR"))
        values = {}
        for iso in COUNTRY_META:
            values[iso] = to_float(row.get("GPRC_" + iso))
        raw[month] = values

    # 补全缺失月份
    for month in months:
        raw.setdefault(month, {iso: None for iso in COUNTRY_META})
        global_series.setdefault(month, None)

    # 每月排名
    ranks = {}
    for month in months:
        valid = [(iso, raw[month][iso]) for iso in COUNTRY_META if raw[month][iso] is not None]
        valid.sort(key=lambda item: item[1], reverse=True)
        ranks[month] = {iso: i + 1 for i, (iso, _) in enumerate(valid)}

    # 1) 长表 CSV（含缺失标记）
    os.makedirs(outdir, exist_ok=True)
    csv_path = os.path.join(outdir, "gpr_data.csv")
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow([
            "month", "iso3", "country_en", "country_zh", "region",
            "gprc", "gprc_unit", "risk_level", "risk_rank", "status",
        ])
        for month in months:
            for iso, (name_en, name_zh, region) in COUNTRY_META.items():
                value = raw[month][iso]
                writer.writerow([
                    month, iso, name_en, name_zh, region,
                    "" if value is None else round(value, 4),
                    "% of newspaper articles",
                    risk_level(value) or "",
                    "" if value is None else ranks[month].get(iso, ""),
                    "ok" if value is not None else "missing",
                ])

    # 2) 前端 JSON
    countries = OrderedDict()
    missing_count = 0
    for iso, (name_en, name_zh, region) in COUNTRY_META.items():
        values = OrderedDict()
        for month in months:
            value = raw[month][iso]
            if value is None:
                missing_count += 1
                values[month] = None
            else:
                values[month] = round(value, 3)
        countries[iso] = {
            "name_en": name_en,
            "name_zh": name_zh,
            "region": region,
            "values": values,
        }

    events = []
    for date, title, lat, lon, desc in EVENTS:
        if date in month_set:
            events.append({
                "date": date, "title": title, "lat": lat, "lon": lon, "desc": desc,
            })

    payload = {
        "meta": {
            "title": "全球地缘政治风险（GPR）地图",
            "subtitle": "Caldara & Iacoviello (2022) GPR Index · 国别指数 GPRC",
            "source": "Caldara, Dario and Matteo Iacoviello (2022), Measuring Geopolitical Risk, AER 112(4)",
            "source_url": "https://www.matteoiacoviello.com/gpr.htm",
            "downloaded": "2026-10-22",
            "data_last_update": "2026-10-01",
            "first_month": START_MONTH,
            "last_month": months[-1],
            "months": months,
            "units": {"gprc": "% of newspaper articles", "gpr": "index (1985-2019 = 100)"},
            "thresholds": THRESHOLDS,
            "colors": COLORS,
            "risk_levels": RISK_LEVELS,
            "range_labels": RANGE_LABELS,
            "country_count": len(COUNTRY_META),
            "missing_values": missing_count,
            "note": "GPRC 为 Iacoviello 官方国别指数原始值（占报纸文章比例，%），非 0-100 标准化指数。",
        },
        "global": {"name_zh": "全球", "name_en": "Global", "values": global_series},
        "countries": countries,
        "events": events,
    }
    json_path = os.path.join(outdir, "gpr_monthly.json")
    with open(json_path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, separators=(",", ":"))

    # 3) 精简 GeoJSON
    geo_out = os.path.join(outdir, "world.geojson")
    feature_count = compact_geojson(geojson_path, geo_out)

    print("[OK] 月份范围: %s ~ %s（%d 个月）" % (months[0], months[-1], len(months)))
    print("[OK] 国家/地区: %d，缺失值: %d" % (len(COUNTRY_META), missing_count))
    print("[OK] 输出: %s" % csv_path)
    print("[OK] 输出: %s" % json_path)
    print("[OK] 输出: %s（%d 个国家边界）" % (geo_out, feature_count))


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    parser = argparse.ArgumentParser(description="GPR 数据预处理")
    parser.add_argument("--raw", default=os.path.join(here, "gpr_raw.csv"))
    parser.add_argument("--geojson", default=os.path.join(here, "world_raw.geojson"))
    parser.add_argument("--outdir", default=here)
    args = parser.parse_args()
    build(args.raw, args.geojson, args.outdir)


if __name__ == "__main__":
    main()
