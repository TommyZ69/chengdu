import geopandas as gpd
from sqlalchemy import create_engine
import os

def import_data_to_postgis():
    # 1. 配置数据库连接 (请根据你的实际情况修改用户名和密码)
    # 格式: postgresql://用户名:密码@主机地址:端口/数据库名
    engine = create_engine('postgresql://postgres:postgres@localhost:5432/chengdu_gis')
    print("🔌 数据库连接已建立...")

    # ==========================================
    # 任务 A：合并并导入 9 类点要素 (urban_all_points)
    # ==========================================
    print("\n📦 正在处理城市全量点要素...")
    point_files = [
        "residential_wgs84.geojson", "medical_wgs84.geojson", 
        "catering_wgs84.geojson", "edu_wgs84.geojson", 
        "finance_wgs84.geojson", "government_wgs84.geojson", 
        "life_wgs84.geojson", "shopping_wgs84.geojson", "sports_wgs84.geojson"
    ]
    
    gdfs = []
    for file in point_files:
        if os.path.exists(file):
            print(f"  ∟ 读取 {file}...")
            gdf = gpd.read_file(file)
            # 重命名 type 为 sub_type 以防止 SQL 关键字冲突
            if 'type' in gdf.columns:
                gdf = gdf.rename(columns={'type': 'sub_type'})
            gdfs.append(gdf)
        else:
            print(f"  ⚠️ 未找到文件 {file}，已跳过。")

    if gdfs:
        # 将所有 GeoDataFrame 上下拼接成一个大表
        merged_points = pd.concat(gdfs, ignore_index=True)
        # 写入 PostGIS
        # if_exists='replace' 表示如果表存在则覆盖重建
        merged_points.to_postgis(
            name='urban_all_points', 
            con=engine, 
            if_exists='replace', 
            index=True, 
            index_label='id'
        )
        print("✅ 城市全量点要素表 (urban_all_points) 导入完成！")

    # ==========================================
    # 任务 B：导入 15 分钟等时圈面要素 (isochrones_15min)
    # ==========================================
    print("\n🕸️ 正在处理 15 分钟等时圈面要素...")
    iso_file = "residential_isochrones_15min.geojson"
    if os.path.exists(iso_file):
        iso_gdf = gpd.read_file(iso_file)
        iso_gdf.to_postgis(
            name='isochrones_15min', 
            con=engine, 
            if_exists='replace', 
            index=True, 
            index_label='id'
        )
        print("✅ 等时圈多边形表 (isochrones_15min) 导入完成！")

    # ==========================================
    # 任务 C：导入底层步行路网线要素 (road_network_edges)
    # ==========================================
    print("\n🛣️ 正在处理底层步行路网线要素...")
    road_file = "chengdu_5districts_walk.gpkg"
    if os.path.exists(road_file):
        # GPKG 可能包含多个图层，指定读取 edges 图层
        road_gdf = gpd.read_file(road_file, layer='edges')
        road_gdf.to_postgis(
            name='road_network_edges', 
            con=engine, 
            if_exists='replace', 
            index=True, 
            index_label='id'
        )
        print("✅ 步行路网表 (road_network_edges) 导入完成！")

    print("\n🎉 所有空间资产已成功迁移至 PostGIS 数据库！")

if __name__ == "__main__":
    import pandas as pd # 需要补一个 pandas 导入用于 concat
    import_data_to_postgis()