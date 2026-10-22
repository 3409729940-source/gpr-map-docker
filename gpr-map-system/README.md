# 全球地缘政治风险（GPR）可视化地图系统

基于 Caldara & Iacoviello (2022) 地缘政治风险指数的交互式世界地图。纯静态前端（Leaflet + ECharts），
数据在 Docker 构建阶段预处理，`docker compose up -d` 后即可离线运行，无任何外部 CDN / 瓦片依赖。

- 数据范围：**2020-01 ~ 2026-09（81 个月）**
- 覆盖范围：**44 个国家 / 地区**（Iacoviello 官方 GPRC 国别指数样本）
- 访问地址：**http://localhost:8080**

---

## 一、一键部署

在项目根目录执行：

```bash
docker compose up -d
```

等待构建完成后打开 <http://localhost:8080>。

```bash
# 查看容器状态（容器名 gpr-map，端口映射 0.0.0.0:8080->80/tcp）
docker ps

# 停止并清理
docker compose down
```

> 首次构建约 10–30 秒：阶段一 `python:3.11-slim` 运行 `preprocess.py` 生成数据，
> 阶段二 `nginx:alpine` 只保留静态文件，最终镜像约 50 MB，运行时无 Python 依赖。

若 8080 被占用，修改 `docker-compose.yml` 中的 `"8080:80"` 为其他端口即可（如 `"8090:80"`）。

---

## 二、功能说明

| 模块 | 实现内容 |
| --- | --- |
| 世界地图 Choropleth | Leaflet 1.9.4 + Natural Earth 1:110m GeoJSON，按 GPRC 分 5 档着色（绿→黄→红），无数据国家灰色；支持滚轮缩放、拖拽平移、双击放大、世界循环平移 |
| 时间筛选 | 月份滑块（81 档）+ 月份下拉框 + 播放按钮（780ms/月自动推进），三者与地图、排名、KPI、趋势图、事件标记实时联动 |
| 悬浮交互 | 国家 tooltip 显示：中文名 / ISO3 / GPRC 数值 / 占报纸文章比例 / 风险等级徽章 / 全球排名 / 环比变化；移开自动消失，圆角卡片 + 阴影 + 深色箭头 |
| 风险排名 | 右侧 Top 10 排名（当月），支持按国家名、ISO3、区域搜索；点击行可加入 / 移出趋势对比 |
| 历史趋势（选做 A） | ECharts 折线图展示所选国家 2020–2026 完整序列，含当前月份参考线与高风险阈值线 |
| 多国对比（选做 B） | 最多同时选择 5 个国家并排对比，地图点击或排名行点击均可切换，chip 支持单独移除 |
| 事件标注（选做 C） | 12 个重大地缘政治事件（疫情、俄乌、巴以、红海、以伊等）叠加在地图上，仅显示当前月份及之前的事件；悬浮显示说明，点击跳转到事件月份并定位 |
| 数据导出（选做 D） | 一键导出当前月份全部国家排名：CSV（UTF-8 BOM，Excel 可直接打开）、JSON、PNG（html2canvas 2x 高清地图卡片） |
| 响应式（选做 E） | 1180px / 820px / 560px 三档断点，手机端单列布局、地图自适应，触控可缩放拖动 |
| KPI 概览 | 全球 GPR 指数及环比、覆盖国家数、高风险国家数、当月最高风险国家 |

所有国家 / 地区名称、区域、阈值、色阶均在 `data/preprocess.py` 中集中配置。

---

## 三、数据字典

### 3.1 `data/gpr_data.csv`（清洗后长表）

编码 UTF-8 with BOM，逗号分隔，共 81 × 44 = **3564 行**数据。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `month` | string | 月份，格式 `YYYY-MM`，范围 `2020-01` ~ `2026-09` |
| `iso3` | string | ISO 3166-1 alpha-3 国家 / 地区代码，如 `CHN`、`USA`、`TWN` |
| `country_en` | string | 英文名称 |
| `country_zh` | string | 中文名称 |
| `region` | string | 所属区域：亚洲 / 欧洲 / 北美洲 / 南美洲 / 非洲 / 中东 / 大洋洲 |
| `gprc` | float | 国别地缘政治风险指数，单位见 `gprc_unit`；缺失时为空字符串 |
| `gprc_unit` | string | 固定为 `% of newspaper articles`（占当月该国报纸文章的比例，%） |
| `risk_level` | string | 五档风险等级：低风险 / 较低风险 / 中等风险 / 高风险 / 极高风险；缺失时为空 |
| `risk_rank` | int | 当月 44 国中的排名，`1` 表示风险最高；缺失时为空 |
| `status` | string | 数据状态：`ok` 正常，`missing` 缺失（当前数据集全部为 `ok`） |

**关于 GPRC 的说明**：`GPRC_<ISO3>` 是 Iacoviello 官方国别指数，表示“该国报纸中提到地缘政治风险的文章占比（%）”，
量纲不是 0–100 的标准化分数，常见取值在 0–5 之间。全球指数 `GPR` 为另一列（1985–2019 均值 = 100），
前端 KPI 中的“全球 GPR 指数”使用该序列，不参与地图着色。

**五档阈值与配色**（左闭右开，与地图图例一致）：

| 档位 | GPRC 区间 | 风险等级 | 颜色 |
| --- | --- | --- | --- |
| 1 | `< 0.05` | 低风险 | `#2b9348` 深绿 |
| 2 | `0.05 – 0.15` | 较低风险 | `#8ac926` 黄绿 |
| 3 | `0.15 – 0.35` | 中等风险 | `#ffd166` 浅黄 |
| 4 | `0.35 – 1.00` | 高风险 | `#f77f00` 橙色 |
| 5 | `≥ 1.00` | 极高风险 | `#c1121f` 深红 |

**灰色国家**：地图上灰色代表该国不在 Iacoviello 44 国 GPRC 样本内（如阿尔及利亚、伊朗等），
并非数据缺失；tooltip 会明确提示“暂无 GPR 数据 / 不在 44 国 GPRC 样本中”。

### 3.2 `data/gpr_monthly.json`（前端数据）

```text
{
  "meta":      { title, source, downloaded, data_last_update, first_month, last_month,
                 months[81], units, thresholds[4], colors[5], risk_levels[5],
                 range_labels[5], country_count, missing_values, note },
  "global":    { name_zh, name_en, values: { "YYYY-MM": number|null } },
  "countries": { "CHN": { name_en, name_zh, region,
                          values: { "YYYY-MM": number|null } }, ... },
  "events":    [ { date, title, lat, lon, desc }, ... ]
}
```

### 3.3 `data/world.geojson`

FeatureCollection，共 177 个国家 / 地区边界，坐标精度压缩至小数点后 3 位（约 199 KB，远小于 1 MB 要求）。

| 属性 | 说明 |
| --- | --- |
| `iso3` | ISO3 代码，用于与 GPRC 数据关联（优先 `ISO_A3`，回退 `ISO_A3_EH` / `ADM0_A3`） |
| `name_en` | 英文国名 |
| `name_zh` | 中文国名 |

### 3.4 原始数据

- `data/gpr_data.xlsx` / `data/gpr_data.xls`：Iacoviello 官网 `data_gpr_export.xls` 原始文件（1521 行 × 115 列，
  含 `GPR`、`GPRT`、`GPRA`、`GPRH` 及 44 个 `GPRC_<ISO3>` 列），保留完整历史以便复核。
- `data/gpr_raw.csv`：从官方文件导出的 2020-01 ~ 2026-09 子集，是 `preprocess.py` 的直接输入。

---

## 四、数据处理流程

```text
data_gpr_export.xls （官网原始文件，更新至 2026-10-01）
        │  导出 2020-01 ~ 2026-09 子集（pandas，本地一次性执行）
        ▼
data/gpr_raw.csv
        │  preprocess.py（纯标准库，Docker 构建阶段自动执行）
        ├── 月份补齐：缺失月份以 null 填充
        ├── 缺失值处理：""、NA、NaN、Inf 统一转为 null，并标记 status=missing
        ├── 风险分级：按 4 个阈值映射到 5 档等级
        ├── 月度排名：每月按 GPRC 降序生成 1~44 名
        ├── 边界精简：Natural Earth 1:110m → 仅保留 iso3/name_en/name_zh，坐标保留 3 位小数
        ▼
data/gpr_data.csv + data/gpr_monthly.json + data/world.geojson
```

本地重新生成（仅在需要从 xls 重建时使用，需 `pip install -r requirements.txt`）：

```bash
python data/preprocess.py --raw data/gpr_raw.csv --geojson data/world_raw.geojson --outdir data
```

输出校验：

```text
[OK] 月份范围: 2020-01 ~ 2026-09（81 个月）
[OK] 国家/地区: 44，缺失值: 0
[OK] gpr_data.csv / gpr_monthly.json / world.geojson（177 个国家边界）
```

---

## 五、目录结构

```text
gpr-map-system/
├── README.md
├── Dockerfile                         # 多阶段构建：Python 预处理 + nginx 静态服务
├── docker-compose.yml                 # 一键部署，8080:80
├── .dockerignore
├── nginx.conf                         # gzip、GeoJSON MIME、静态资源缓存
├── requirements.txt                   # 仅本地重建原始数据时需要
├── data/
│   ├── gpr_data.xlsx                  # 官方原始数据（Excel 版）
│   ├── gpr_data.xls                   # 官方原始数据（官网下载原文件）
│   ├── gpr_raw.csv                    # 2020–2026 原始子集（预处理输入）
│   ├── preprocess.py                  # 预处理脚本（仅标准库）
│   ├── gpr_data.csv                   # 清洗后长表
│   ├── gpr_monthly.json               # 前端可视化数据
│   ├── world_raw.geojson              # Natural Earth 原始边界
│   └── world.geojson                  # 精简后边界（177 国，199 KB）
├── html/
│   ├── index.html                     # 单文件地图页面（结构 + 样式 + 逻辑）
│   └── assets/
│       ├── leaflet/                   # Leaflet 1.9.4（本地化）
│       ├── echarts/echarts.min.js     # ECharts 5.5.1
│       └── html2canvas.min.js         # PNG 导出
└── screenshots/                       # localhost 部署实拍截图
    ├── 01-initial-overview.png
    ├── 02-hover-tooltip.png
    ├── 03-month-2020-03.png
    ├── 04-month-2024-08.png
    ├── 05-zoom-region.png
    ├── 07-mobile-responsive.png
    ├── 08-no-data-country.png
    ├── 09-event-tooltip.png
    └── 10-trend-compare.png
```

---

## 六、截图说明

所有截图均在 `http://localhost:8080` 部署环境下用浏览器实拍，分辨率 ≥ 1280×720：

| 文件 | 内容 |
| --- | --- |
| `01-initial-overview.png` | 首次打开首页的完整概览（默认月份 2026-09） |
| `02-hover-tooltip.png` | 悬浮中国，tooltip 显示 1.19%、极高风险、全球第 5、环比 +0.17pp |
| `03-month-2020-03.png` | 时间筛选到 2020-03（疫情初期） |
| `04-month-2024-08.png` | 时间筛选到 2024-08，与 03 形成对比 |
| `05-zoom-region.png` | 缩放到欧洲区域（2022-02 俄乌冲突月） |
| `07-mobile-responsive.png` | 430×932 手机端响应式布局 |
| `08-no-data-country.png` | 阿尔及利亚灰色无数据 + tooltip 说明 |
| `09-event-tooltip.png` | 事件标记 tooltip（2025-06 以伊军事冲突升级） |
| `10-trend-compare.png` | 中 / 美 / 俄 / 以 / 英 五国趋势对比 |

> `06-docker-ps.png` 为可选的 `docker ps` 终端截图（需在装有 Docker 的机器上执行后补拍），
> 编号 06 已预留，不影响其余截图连续性。

---

## 七、数据来源与引用

- GPR Index（Caldara & Iacoviello, 2022）：<https://www.matteoiacoviello.com/gpr.htm>
  - Caldara, Dario, and Matteo Iacoviello. "Measuring Geopolitical Risk."
    *American Economic Review* 112, no. 4 (2022): 1194–1225.
  - 下载日期：2026-10-22；官方数据最后更新：2026-10-01
- 国家边界：Natural Earth 1:110m Admin 0 Countries（GeoJSON）
- 前端库：Leaflet 1.9.4、Apache ECharts 5.5.1、html2canvas 1.4.1，均已本地化到 `html/assets/`

---

## 八、实现要点

1. **构建期预处理**：`Dockerfile` 使用 `python:3.11-slim` 作为 builder 运行 `preprocess.py`，nginx 阶段只拷贝产物，
   避免运行时安装 pandas / Python，镜像更小、启动更快。
2. **纯离线**：不使用在线瓦片底图，国家边界以 GeoJSON 直接渲染；Leaflet / ECharts / html2canvas 全部本地引用，
   断网或内网环境同样可用。
3. **数据与视图解耦**：`preprocess.py` 统一产出长表、前端 JSON 与精简边界；`index.html` 只负责加载与渲染，
   替换数据无需改动前端逻辑。
4. **交互一致性**：滑块、下拉、播放、事件跳转都调用同一个 `setMonth()`，地图、排名、KPI、趋势线、事件过滤同步更新。
5. **可访问性**：控件带 `aria-label`，风险不仅用颜色区分（tooltip 同时给出等级文字与数值），色阶采用绿→黄→红渐进。
