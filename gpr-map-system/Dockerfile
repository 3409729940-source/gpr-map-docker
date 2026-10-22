# ---------- 第一阶段：构建期完成数据预处理（无需运行时 Python） ----------
FROM python:3.11-slim AS builder

WORKDIR /build

# 预处理脚本只依赖 Python 标准库，因此无需 pip install，构建可离线完成
COPY data/preprocess.py data/gpr_raw.csv data/world_raw.geojson ./

RUN python preprocess.py --raw gpr_raw.csv --geojson world_raw.geojson --outdir out

# ---------- 第二阶段：nginx 静态服务 ----------
FROM nginx:alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY html/ /usr/share/nginx/html/
COPY --from=builder /build/out/ /usr/share/nginx/html/data/

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget -q --spider http://localhost/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
