import streamlit as st
import pandas as pd
import requests
import pydeck as pdk  # 引入高阶地图库

# --- 1. 配置层 ---
st.set_page_config(page_title="全球地震监控中心", layout="wide")

# --- 2. 后端：数据获取与清洗 ---
@st.cache_data
def get_earthquake_data():
    url = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_day.geojson"
    try:
        response = requests.get(url, timeout=10) # 增加超时保护
        json_data = response.json()
        features = json_data['features']
        
        parsed_data = []
        for item in features:
            mag = item['properties']['mag']
            # 只处理有震级的数据
            if mag is not None:
                parsed_data.append({
                    'lat': item['geometry']['coordinates'][1],
                    'lon': item['geometry']['coordinates'][0],
                    'mag': mag,
                    'place': item['properties']['place'],
                    'time': pd.to_datetime(item['properties']['time'], unit='ms').strftime('%Y-%m-%d %H:%M'),
                    # 预计算视觉半径：震级越大，圈越大 (例如：5级=50000米，指数级增长)
                    'radius': 20000 * (1.5 ** (mag - 4)) 
                })
        return pd.DataFrame(parsed_data)
    except Exception as e:
        st.error(f"数据获取失败，请检查网络: {e}")
        return pd.DataFrame()

# --- 3. 交互层 (Sidebar) ---
st.sidebar.header("🕹️ 指挥控制台")
st.sidebar.write("数据源: USGS Live Feed")

# A. 滑块组件
min_mag = st.sidebar.slider(
    "最小震级过滤 (Minimum Magnitude)", 
    min_value=2.5, 
    max_value=8.0, 
    value=4.5,  # 默认值
    step=0.1
)

# --- 4. 逻辑层 (Processing) ---
df = get_earthquake_data()

# 数据过滤逻辑：只保留大于用户设定震级的记录
filtered_df = df[df['mag'] >= min_mag]

# --- 5. 表现层 (UI/Visualization) ---
st.title(f"🌍 全球实时地震监测中心 (>{min_mag}级)")

# 核心指标
col1, col2, col3 = st.columns(3)
col1.metric("可见地震数量", f"{len(filtered_df)} 次")
col2.metric("当前最大震级", f"{filtered_df['mag'].max() if not filtered_df.empty else 0} 级")
col3.metric("筛选阈值", f"{min_mag} 级")

# 高阶地图渲染 (PyDeck)
if not filtered_df.empty:
    # 定义地图图层
    layer = pdk.Layer(
        "ScatterplotLayer",    # 散点图层
        filtered_df,
        get_position='[lon, lat]',
        get_color='[200, 30, 0, 160]',  # 红色，带透明度 [R, G, B, Alpha]
        get_radius='radius',   # 使用我们在数据清洗时算好的半径
        pickable=True,         # 允许鼠标悬停
    )

    # 定义地图视角 (初始视角定位)
    view_state = pdk.ViewState(
        latitude=20.0,
        longitude=0.0,
        zoom=1.5,
        pitch=0        # 垂直视角
    )

    # 渲染地图
    st.pydeck_chart(pdk.Deck(
        map_style='mapbox://styles/mapbox/dark-v9', # 深色科技风格
        initial_view_state=view_state,
        layers=[layer],
        tooltip={"text": "地点: {place}\n震级: {mag}级\n时间: {time}"} # 鼠标悬停显示内容
    ))
else:
    st.warning("当前筛选条件下无数据，请调低震级阈值。")

# 原始数据表
with st.expander("📂 查看详细数据报表"):
    st.dataframe(filtered_df[['time', 'place', 'mag', 'lat', 'lon']])

# --- [V1.1 新增功能] 统计分析层 ---
st.markdown("---") # 分割线
st.subheader("📊 地震时间分布分析")

# 1. 数据预处理：将时间列转换为 datetime 对象，方便统计
# 我们的 raw data 里 'time' 是字符串，需要转一下
if not filtered_df.empty:
    filtered_df['datetime'] = pd.to_datetime(filtered_df['time'])
    
    # 2. 按“小时”进行分组统计
    # 提取小时数 (0-23)
    filtered_df['hour'] = filtered_df['datetime'].dt.hour
    
    # 统计每个小时出现的次数
    hourly_counts = filtered_df['hour'].value_counts().sort_index()
    
    # 3. 渲染柱状图 (Bar Chart)
    st.bar_chart(hourly_counts)
    
    st.caption("X轴：一天中的24小时 (0-23) | Y轴：地震发生次数")
else:
    st.info("暂无数据可供统计")