import geopandas as gpd

# 加载生成的结果
gdf = gpd.read_file("residential_isochrones_15min.geojson")

# 1. 检查数据量
print(f"总计生成的等时圈数量: {len(gdf)}")

# 2. 抽样检查面积 (WGS84 需转为投影坐标系算面积，单位：平方米)
# 3857 是 Web 墨卡托投影
sample = gdf.sample(5).to_crs(epsg=3857)
sample['area_sqm'] = sample.area

print("\n抽样小区面积检查 (单位: 平方米):")
for idx, row in sample.iterrows():
    # 理论上 1km 半径的圆面积约为 3.14e6，步行网络等时圈通常在 0.5e6 - 2.5e6 之间
    print(f"小区: {row['name']}, 面积: {row['area_sqm']:.2f}")