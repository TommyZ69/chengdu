import pandas as pd
import math
import json
import os

# 注意：运行此脚本需要安装 openpyxl 库：pip install openpyxl

class POIAutomationFactory:
    def __init__(self):
        # 严格锁定成都市中心五城区
        self.target_districts = ['金牛区', '青羊区', '成华区', '锦江区', '武侯区']
        self.pi = math.pi
        self.a = 6378245.0
        self.ee = 0.00669342162296594323

    def gcj02_to_wgs84(self, lng, lat):
        """火星坐标系 (GCJ-02) 转 WGS-84 算法"""
        def _transform_lat(x, y):
            ret = -100.0 + 2.0 * x + 3.0 * y + 0.2 * y * y + 0.1 * x * y + 0.2 * math.sqrt(abs(x))
            ret += (20.0 * math.sin(6.0 * x * self.pi) + 20.0 * math.sin(2.0 * x * self.pi)) * 2.0 / 3.0
            ret += (20.0 * math.sin(y * self.pi) + 40.0 * math.sin(y / 3.0 * self.pi)) * 2.0 / 3.0
            ret += (160.0 * math.sin(y / 12.0 * self.pi) + 320 * math.sin(y * self.pi / 30.0)) * 2.0 / 3.0
            return ret
        def _transform_lng(x, y):
            ret = 300.0 + x + 2.0 * y + 0.1 * x * x + 0.1 * x * y + 0.1 * math.sqrt(abs(x))
            ret += (20.0 * math.sin(6.0 * x * self.pi) + 20.0 * math.sin(2.0 * x * self.pi)) * 2.0 / 3.0
            ret += (20.0 * math.sin(x * self.pi) + 40.0 * math.sin(x / 3.0 * self.pi)) * 2.0 / 3.0
            ret += (150.0 * math.sin(x / 12.0 * self.pi) + 300.0 * math.sin(x / 30.0 * self.pi)) * 2.0 / 3.0
            return ret
        dlat = _transform_lat(lng - 105.0, lat - 35.0)
        dlng = _transform_lng(lng - 105.0, lat - 35.0)
        radlat = lat / 180.0 * self.pi
        magic = math.sin(radlat)
        magic = 1 - self.ee * magic * magic
        sqrtmagic = math.sqrt(magic)
        dlat = (dlat * 180.0) / ((self.a * (1 - self.ee)) / (magic * sqrtmagic) * self.pi)
        dlng = (dlng * 180.0) / (self.a / sqrtmagic * math.cos(radlat) * self.pi)
        return round(lng * 2 - (lng + dlng), 6), round(lat * 2 - (lat + dlat), 6)

    def is_noise_sub(self, type_str, noise_list):
        """核心逻辑：拆解 type 字符串，检查『小类』是否在剔除名单中"""
        if not noise_list or pd.isna(type_str): return False
        # 高德 type 格式: 大类;中类;小类，可能存在多个分类用 | 分隔
        for entry in str(type_str).split('|'):
            parts = entry.split(';')
            if len(parts) >= 3:
                sub_cat = parts[2] # 获取小类
                if sub_cat in noise_list: return True
        return False

    def process_task(self, filename, category_name, noise_subs=None):
        print(f"\n📂 正在处理 [{category_name}] 数据源: {filename}...")
        
        if not os.path.exists(filename):
            print(f"   ⚠️ 跳过：未在当前目录下找到文件 {filename}")
            return

        try:
            # 使用 pd.read_excel 读取原始 xlsx 文件
            df = pd.read_excel(filename)
            
            # 1. 行政区筛选
            df = df[df['district'].isin(self.target_districts)]
            
            # 2. 精准过滤『小类』
            if noise_subs:
                df = df[~df['type'].apply(lambda x: self.is_noise_sub(x, noise_subs))]
            
            # 3. 坐标系转换
            print(f"   ∟ 核心区有效数据: {len(df)} 条。正在执行 WGS84 转换...")
            df['wgs_pos'] = df.apply(lambda r: self.gcj02_to_wgs84(float(r['lng']), float(r['lat'])), axis=1)
            df['wgs_lng'] = df['wgs_pos'].apply(lambda x: x[0])
            df['wgs_lat'] = df['wgs_pos'].apply(lambda x: x[1])
            df['category'] = category_name

            # 4. 生成 GeoJSON
            features = []
            for _, row in df.iterrows():
                features.append({
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [row["wgs_lng"], row["wgs_lat"]]},
                    "properties": {
                        "name": row["name"],
                        "category": category_name,
                        "type": row["type"],
                        "address": str(row.get("address", "未知")),
                        "district": row["district"]
                    }
                })
            
            # 5. 导出文件
            output_base = f"{category_name}_wgs84"
            with open(f'{output_base}.geojson', 'w', encoding='utf-8') as f:
                json.dump({"type": "FeatureCollection", "features": features}, f, ensure_ascii=False, indent=2)
            
            df[['name', 'category', 'type', 'district', 'wgs_lng', 'wgs_lat']].to_csv(f'{output_base}.csv', index=False, encoding='utf-8-sig')
            
            print(f"   ✅ 完成！输出: {output_base}.geojson / .csv")

        except Exception as e:
            print(f"   ❌ 处理失败: {e}")

# ==========================================
# 自动化任务配置清单 (精准匹配你的 .xlsx 文件名)
# ==========================================
if __name__ == "__main__":
    factory = POIAutomationFactory()

    tasks = [
        {"filename": "商务住宅_11727.xlsx", "category": "residential", 
         "noise_subs": ['商务住宅相关', '社区中心', '商务写字楼', '宿舍', '商住两用楼宇', '别墅', '产业园区']}
    ]

    for t in tasks:
        factory.process_task(t['filename'], t['category'], t['noise_subs'])

    print("\n🎉 --- 15分钟生活圈全量数据流水线处理完毕 --- 🎉")