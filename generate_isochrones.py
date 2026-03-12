import pandas as pd
import networkx as nx
from shapely.geometry import Point, MultiPoint
import json
from scipy.spatial import cKDTree
import time
import os

def generate_all_isochrones():
    start_time = time.time()

    print("1. 正在加载路网模型 (GraphML)... 这可能需要大约一分钟。")
    graph_path = "chengdu_5districts_walk.graphml"

    if not os.path.exists(graph_path):
        print(f"❌ 未找到 {graph_path}。请确认 OSM 路网文件在当前目录下。")
        return

    G = nx.read_graphml(graph_path)

    node_ids = []
    node_coords = []
    node_coord_dict = {}

    for node, data in G.nodes(data=True):
        x = float(data.get('x', data.get('lon', 0)))
        y = float(data.get('y', data.get('lat', 0)))
        node_ids.append(node)
        node_coords.append([x, y])
        node_coord_dict[node] = (x, y)

    print(f"✅ 路网加载完毕，包含 {len(node_ids)} 个交叉口节点。")
    tree = cKDTree(node_coords)

    for u, v, data in G.edges(data=True):
        try:
            length_val = data.get('length', 10.0)
            if isinstance(length_val, str) and length_val.startswith('['):
                length_val = eval(length_val)[0]
            data['length'] = float(length_val)
        except:
            data['length'] = 10.0

    print("\n2. 正在加载小区数据...")
    residential_file = "residential_wgs84.csv"
    if not os.path.exists(residential_file):
         print(f"❌ 未找到 {residential_file}。请确认文件存在。")
         return
         
    df = pd.read_csv(residential_file)
    total_points = len(df)
    distance_limit = 1080.0

    features = []
    csv_records = [] # ✨ 新增：用于存储准备写入 CSV 的数据

    print(f"\n3. 开始计算 {total_points} 个小区的 15 分钟等时圈...")

    for idx, row in df.iterrows():
        dist, idx_node = tree.query([row['wgs_lng'], row['wgs_lat']])
        start_node = node_ids[idx_node]

        lengths = nx.single_source_dijkstra_path_length(G, start_node, cutoff=distance_limit, weight='length')
        reachable_coords = [node_coord_dict[n] for n in lengths.keys()]

        if len(reachable_coords) >= 3:
            poly = MultiPoint(reachable_coords).convex_hull
        elif len(reachable_coords) > 0:
            poly = MultiPoint(reachable_coords).buffer(0.0005) 
        else:
            poly = Point(row['wgs_lng'], row['wgs_lat']).buffer(0.0005)

        # ✨ 提取属性数据
        properties = {
            "community_id": str(idx),
            "name": str(row['name']),
            "district": str(row['district']),
            "center_lng": row['wgs_lng'],
            "center_lat": row['wgs_lat'],
            "polygon_wkt": poly.wkt  # ✨ 核心：将多边形转为 WKT 纯文本格式存入 CSV
        }

        # 添加到 GeoJSON 列表
        features.append({
            "type": "Feature",
            "geometry": poly.__geo_interface__,
            "properties": properties
        })
        
        # 添加到 CSV 列表
        csv_records.append(properties)

        if (idx + 1) % 1500 == 0:
            print(f"  ∟ 已处理 {idx + 1} / {total_points} 个社区... 当前总耗时: {time.time() - start_time:.2f}秒")

    # ==========================================
    # 4. 同时导出 GeoJSON 和 CSV 文件
    # ==========================================
    print(f"\n4. 运算完成！正在导出文件...")
    
    # 导出 GeoJSON
    geojson_filename = "residential_isochrones_15min.geojson"
    with open(geojson_filename, "w", encoding="utf-8") as f:
        json.dump({"type": "FeatureCollection", "features": features}, f, ensure_ascii=False)
    
    # ✨ 导出 CSV
    csv_filename = "residential_isochrones_15min.csv"
    csv_df = pd.DataFrame(csv_records)
    csv_df.to_csv(csv_filename, index=False, encoding='utf-8-sig')

    print(f"✅ 成功生成 GeoJSON: {geojson_filename}")
    print(f"✅ 成功生成 CSV: {csv_filename}")
    print(f"⏱️ 批处理总耗时: {time.time() - start_time:.2f} 秒")

if __name__ == "__main__":
    generate_all_isochrones()