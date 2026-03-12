import pandas as pd
import numpy as np
import json
import os
from sklearn.cluster import DBSCAN

class SpatialCleaner:
    def __init__(self):
        # 地球半径，用于 Haversine 距离计算 (单位：公里)
        self.kms_per_radian = 6371.0088

    def clean_task(self, prefix, radius_meters):
        input_csv = f"{prefix}_wgs84.csv"
        if not os.path.exists(input_csv):
            print(f"⚠️ 跳过：未找到文件 {input_csv}")
            return

        print(f"\n🚀 正在处理 [{prefix}]，聚类半径: {radius_meters} 米...")
        try:
            # 1. 读取已经过 WGS84 转换的数据
            df = pd.read_csv(input_csv)
            original_count = len(df)
            if original_count == 0:
                print("   ⚠️ 数据为空，跳过。")
                return

            # 2. 准备 DBSCAN 聚类算法需要的弧度坐标 [lat, lng]
            coords = df[['wgs_lat', 'wgs_lng']].values
            epsilon = (radius_meters / 1000.0) / self.kms_per_radian
            
            # 3. 执行空间聚类
            db = DBSCAN(eps=epsilon, min_samples=1, algorithm='ball_tree', metric='haversine').fit(np.radians(coords))
            df['cluster_id'] = db.labels_

            # 4. 提取簇的代表点和计算权重
            cleaned_records = []
            
            # 确保 name 字段没有空值，避免长度计算报错
            df['name'] = df['name'].fillna("未知名称")
            
            for cluster_id, group in df.groupby('cluster_id'):
                # 权重：该簇包含的原始点位数量
                weight = len(group)
                
                # 找出该簇中“名称最短”的那条记录作为代表点 (总称往往最短)
                rep_idx = group['name'].str.len().idxmin()
                rep_row = group.loc[rep_idx]
                
                # 计算该簇的几何中心作为新的坐标点
                mean_lng = group['wgs_lng'].mean()
                mean_lat = group['wgs_lat'].mean()
                
                cleaned_records.append({
                    'name': rep_row['name'],
                    'category': rep_row['category'],
                    'type': rep_row['type'],
                    'district': rep_row['district'],
                    'wgs_lng': round(mean_lng, 6),
                    'wgs_lat': round(mean_lat, 6),
                    'weight': weight
                })

            cleaned_df = pd.DataFrame(cleaned_records)
            cleaned_count = len(cleaned_df)

            # 5. 导出聚类后的新 CSV
            output_base = f"{prefix}_cleaned"
            cleaned_df.to_csv(f"{output_base}.csv", index=False, encoding='utf-8-sig')

            # 6. 导出包含 weight 的新 GeoJSON
            features = []
            for _, row in cleaned_df.iterrows():
                features.append({
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [row["wgs_lng"], row["wgs_lat"]]
                    },
                    "properties": {
                        "name": row["name"],
                        "category": row["category"],
                        "type": row["type"],
                        "district": row["district"],
                        "weight": row["weight"]  # ✨ 核心：新增的权重属性
                    }
                })
            
            with open(f'{output_base}.geojson', 'w', encoding='utf-8') as f:
                json.dump({"type": "FeatureCollection", "features": features}, f, ensure_ascii=False, indent=2)

            print(f"   ✅ 完成！原始点位: {original_count} -> 聚类后独立机构: {cleaned_count} (缩减了 {original_count - cleaned_count} 个冗余点)")

        except Exception as e:
            print(f"   ❌ 处理出错: {e}")

# ==========================================
# 执行清洗任务清单（严格对齐第一个脚本的产出文件名）
# ==========================================
if __name__ == "__main__":
    cleaner = SpatialCleaner()

    tasks = [
        # 大型设施：占地面积大，采用 150 米半径
        {"prefix": "medical", "radius": 150},
        {"prefix": "government", "radius": 150},
        
        # 商业体密集区：商场内商铺紧凑，采用 50 米半径
        {"prefix": "catering", "radius": 50},
        {"prefix": "shopping", "radius": 50},
        
        # 常规设施：采用 100 米社区尺度半径
        {"prefix": "finance", "radius": 100},
        {"prefix": "edu", "radius": 100},
        {"prefix": "life", "radius": 100},
        {"prefix": "sports", "radius": 100}
    ]

    for t in tasks:
        cleaner.clean_task(t['prefix'], t['radius'])

    print("\n🎉 --- 8大类 POI 空间去重与服务赋权全部完成 --- 🎉")