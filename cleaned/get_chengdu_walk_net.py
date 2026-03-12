import osmnx as ox

def download_chengdu_walk_network():
    # 1. 基础配置
    # 开启控制台日志输出，让你能看到实时的下载进度
    ox.settings.log_console = True
    ox.settings.use_cache = True

    # 2. 精确定义研究区：成都中心五城区
    # 加上完整的行政区划层级，帮助 OSM 精确定位
    places = [
        '金牛区, 成都市, 四川省, 中国',
        '青羊区, 成都市, 四川省, 中国',
        '成华区, 成都市, 四川省, 中国',
        '锦江区, 成都市, 四川省, 中国',
        '武侯区, 成都市, 四川省, 中国'
    ]

    print("🚀 正在向 OpenStreetMap 请求成都五城区边界并下载步行路网...")
    print("⏳ 数据量较大，可能需要 3 到 10 分钟（取决于网络），控制台会滚动输出日志，请耐心等待...")
    
    try:
        # 3. 核心抓取逻辑：network_type='walk' 是 15分钟生活圈的灵魂
        # 它会自动剔除高速公路、封闭主干道，只保留允许人走的人行道、小区路、步行街等
        G = ox.graph_from_place(places, network_type='walk')
        
        print(f"\n✅ 下载并构建网络成功！")
        print(f"   ∟ 包含路口/节点 (Nodes) 数量: {len(G.nodes)}")
        print(f"   ∟ 包含路段 (Edges) 数量: {len(G.edges)}")

        # 4. 导出为 GeoPackage 格式 (极力推荐！单文件同时包含点线图层)
        gpkg_path = 'chengdu_5districts_walk.gpkg'
        # 将图结构转化为 GeoDataFrame 进行导出 (OSMnx 2.0+ 标准做法)
        nodes, edges = ox.graph_to_gdfs(G)
        # 很多 OSM 属性是列表格式，转存 GPKG 前需要将其转为字符串以防报错
        edges = edges.applymap(lambda x: str(x) if isinstance(x, list) else x)
        nodes = nodes.applymap(lambda x: str(x) if isinstance(x, list) else x)
        
        nodes.to_file(gpkg_path, layer='nodes', driver='GPKG')
        edges.to_file(gpkg_path, layer='edges', driver='GPKG')
        print(f"   💾 已保存 GIS 格式: {gpkg_path} (可以直接拖入 QGIS)")

        # 5. 导出为 GraphML 格式 (保存网络拓扑结构，后续 Python 计算等时圈直接读取最快)
        graphml_path = 'chengdu_5districts_walk.graphml'
        ox.save_graphml(G, filepath=graphml_path)
        print(f"   💾 已保存图结构格式: {graphml_path}")

    except Exception as e:
        print(f"\n❌ 获取失败，错误原因: {e}")
        print("💡 提示：OSM 服务器在国外，如果提示 Timeout 或 Max retries exceeded，请检查网络或开启代理工具后重试。")

if __name__ == "__main__":
    download_chengdu_walk_network()