import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
import urllib.request
import os
import matplotlib.font_manager as fm

# ==========================================
# 页面基础设置
# ==========================================
st.set_page_config(page_title="Ekman 螺旋", layout="wide")
font_url = "https://github.com/StellarCN/scp_zh/raw/master/fonts/SimHei.ttf"
font_path = "SimHei.ttf"

# 如果本地没有这个字体文件，则从网络下载
if not os.path.exists(font_path):
    try:
        urllib.request.urlretrieve(font_url, font_path)
    except Exception:
        pass # 如果下载失败，则回退到默认设置

# 强制 Matplotlib 使用下载的中文字体
if os.path.exists(font_path):
    plt.rcParams['font.sans-serif'] = [font_path]
else:
    # 备用列表
    plt.rcParams['font.sans-serif'] = ['Microsoft YaHei','WenQuanYi Micro Hei', 'Noto Sans CJK SC', 'sans-serif']

plt.rcParams['axes.unicode_minus'] = False # 正常显示负号
# plt.rcParams['font.sans-serif'] = ['Microsoft YaHei']
# plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'WenQuanYi Micro Hei', 'Noto Sans CJK SC', 'sans-serif']
# plt.rcParams['axes.unicode_minus'] = False

# st.title("让公式活起来之——无限深海Ekman 漂流理论可视化")
st.markdown(
    """
    <h1 style="font-weight: 700; margin-bottom: 20px; letter-spacing: 1px;text-align: center;">
        <span style="color: #1f77b4;">"让公式活起来"</span><span style="color: #ff7f0e;">之</span>无限深海 Ekman 漂流理论
    </h1>
    """,
    unsafe_allow_html=True
)
# ==========================================
# 侧边栏：交互式控件 (替代 ipywidgets，保持原有描述文本)
# ==========================================
# 🌟 新增：注入 CSS 增大侧边栏字号
st.markdown("""
<style>
/* 增大侧边栏整体基础字号 */
[data-testid="stSidebar"] {
    font-size: 24px !important;
}
/* 增大侧边栏标题 (可调节物理参数, 视角调节（三维流速剖面）) 的字号 */
[data-testid="stSidebar"] h2, 
[data-testid="stSidebar"] h3 {
    font-size: 30px !important;
    font-weight: bold !important;
}
</style>
""", unsafe_allow_html=True)
st.sidebar.header("可调节物理参数")

wind_speed = st.sidebar.slider("风速 (m/s)", 1.0, 25.0, 15.0, 0.5)
wind_dir = st.sidebar.slider("风向 ", 0.0, 360.0, 0.0, 5.0)
latitude = st.sidebar.slider("纬度 (°)", -80.0, 80.0, 30.0, 1.0)

# Streamlit 无原生对数滑块，使用指数滑块完美模拟 FloatLogSlider
# az_log = st.sidebar.slider("湍粘性系数 Az (m²/s) [指数 $10^x$]", -4.0, -1.0, -2.0, 0.1)
Az = st.sidebar.slider("湍粘性系数 Az (m²/s) ", 0.001, 0.1, 0.01, 0.001,format="%.3f")
# Az = 10 ** az_log

# 保持原 widget 中的范围设置 (value=50, min=10, max=100)
max_depth = st.sidebar.slider("显示深度 (m)", 10, 200, 60, 10)

st.sidebar.markdown("---")
st.sidebar.header("视角调节(三维剖面)")
elev = st.sidebar.slider("俯仰角 (°)", 0, 90, 25, 1)
azim = st.sidebar.slider("方位角 (°)", -180, 180, -60, 1)

# ==========================================
# 核心物理计算与绘图逻辑 (保持原样)
# ==========================================
def plot_ekman_hodograph():
    # 1. 物理常数与边界保护
    Omega = 7.292e-5  # 地球自转角速度 (rad/s)
    rho_a = 1.2       # 空气密度 (kg/m^3)
    rho_w = 1025.0    # 海水密度 (kg/m^3)
    C_D = 1.5e-3      # 海面拖曳系数
    
    # 避免赤道 f=0 导致计算溢出
    if abs(latitude) < 5.0:
        lat_safe = 5.0 if latitude >= 0 else -5.0
    else:
        lat_safe = latitude
    ws = max(wind_speed, 0.5) # 避免风速为0
    
    phi = np.radians(lat_safe)
    f = 2 * Omega * np.sin(phi)
    sign_f = np.sign(f) # 北半球为 1，南半球为 -1
    
    # 2. 计算 Ekman 动力学参数
    tau = rho_a * C_D * ws**2           # 风应力大小
    d = np.sqrt(2 * Az / abs(f))        # Ekman 衰减深度 (m)
    V0 = tau / (rho_w * np.sqrt(abs(f) * Az))   # 表面流速大小 (m/s)
    V0 = min(V0, 2.5)  # 限制最大流速，防止图像坐标崩坏
    
    # 3. 角度转换 (罗盘方位 -> 数学极坐标)
    theta_c = np.radians(wind_dir)
    theta_m = np.pi/2 - theta_c 
    
    # 表面流速方向 (北半球偏右45°，南半球偏左45°)
    theta_0 = theta_m - sign_f * np.pi/4
    
    # 4. 生成深度剖面数据
    z = np.linspace(0, max_depth, 500)
    decay = np.exp(-z / d)
    phase = theta_0 - sign_f * z / d
    
    u = V0 * decay * np.cos(phase)
    v = V0 * decay * np.sin(phase)
    
    # 5. 3D 绘图设置
    fig_3d = plt.figure(figsize=(3.6, 3.6))
    ax = fig_3d.add_subplot(111, projection='3d')
    
    # 坐标轴范围 (保持 X 和 Y 对称，确保螺旋线不变形)
    # vel_limit = max(0.5, V0 * 1.2)
    vel_limit = V0 * 1.2
    ax.set_xlim([-vel_limit, vel_limit])
    ax.set_ylim([-vel_limit, vel_limit])
    ax.set_zlim([max_depth, 0]) # Z轴反转，0在顶部，符合海洋学深度习惯

    ax.set_xlabel('东向流速 u (m/s)', labelpad=4, fontsize=8)
    ax.set_ylabel('北向流速 v (m/s)', labelpad=4, fontsize=8)
    ax.set_zlabel('深度  (m)', labelpad=15, fontsize=8)
    ax.tick_params(axis='both', labelsize=7)
    # 绘制连续的 Ekman 螺旋线 (按深度着色)
    colors = plt.cm.viridis(np.linspace(0, 0.9, len(z)))
    for i in range(len(z)-1):
        ax.plot(u[i:i+2], v[i:i+2], z[i:i+2], color=colors[i], linewidth=1.5, alpha=0.8)
        
    # 绘制特定深度的流速矢量“辐条” (从 Z 轴指向螺旋线)
    step = max(1, len(z) // 15) # 均匀取 15 个深度层
    z_q, u_q, v_q = z[::step], u[::step], v[::step]
    ax.plot([0,0],[0,0],[0,max_depth],'b--',alpha=0.9,linewidth=1.5)
    for i in range(len(z_q)):
        ax.plot([0, u_q[i]], [0, v_q[i]], [z_q[i], z_q[i]], 'b-', alpha=0.4, linewidth=0.8)
        ax.scatter(u_q[i], v_q[i], z_q[i], c='w', s=3, depthshade=False)
        
    # 绘制海面 (Z=0) 参考圆 (修复了原代码缺失的乘号 *)
    theta_circle = np.linspace(0, 2 * np.pi, 100)
    r_circle = vel_limit * 0.95
    ax.plot(r_circle * np.cos(theta_circle), r_circle * np.sin(theta_circle), 
            np.zeros_like(theta_circle), 'gray', linestyle=':', alpha=0.5, linewidth=1)
            
    # 绘制海面风矢量 (红色箭头)
    wind_scale = (vel_limit * 0.8) / ws 
    w_u = ws * wind_scale * np.cos(theta_m)
    w_v = ws * wind_scale * np.sin(theta_m)
    
    ax.plot([0, w_u], [0, w_v], [0, 0], 'r-', linewidth=1)
    ax.scatter(w_u, w_v, 0, c='red', s=80, marker='.', depthshade=False, label='Wind Direction')
    ax.text(w_u * 1.1, w_v * 1.1, 0, f'风\n{ws}m/s', color='red', fontsize=8, ha='center') # 修复了原代码缺失的乘号 *
    
    # 标题
    hemisphere = '北半球 (向右偏转)' if sign_f > 0 else '南半球 (向左偏转)'
    title = f'Ekman 螺旋三维流速剖面'
    ax.set_title(title, fontsize=10, pad=5, fontweight='bold')
    
    # 🌟 核心修改：使用传入的 elev 和 azim 参数设置视角
    ax.view_init(elev=elev, azim=azim)
    plt.tight_layout()
    plt.tight_layout(pad=0.5)
    # ==========================================
    # 6. 2D 水平投影图设置 (俯视图)
    # ==========================================
    fig_2d = plt.figure(figsize=(3.6, 3.6))
    ax_2d = fig_2d.add_subplot(111)
    
    # 绘制轨迹线 (灰色背景线)
    ax_2d.plot(u, v, color='lightgray', linestyle='-', linewidth=1, zorder=1)
    
    # 绘制按深度着色的散点，以体现深度变化
    sc = ax_2d.scatter(u, v, c=z, cmap='viridis', s=5, edgecolor='none', zorder=2)
    
    # 添加颜色条 (Colorbar)
    cbar = plt.colorbar(sc, ax=ax_2d, pad=0.02,fraction=0.046)
    cbar.set_label('深度 (m)', rotation=270, labelpad=15, fontsize=8)
    cbar.ax.tick_params(labelsize=7)
    # 绘制特定深度的流速矢量“辐条”
    for i in range(len(z_q)):
        ax_2d.plot([0, u_q[i]], [0, v_q[i]], 'b-', alpha=0.4, linewidth=0.8, zorder=3)
        ax_2d.scatter(u_q[i], v_q[i], c='w', s=8, marker='.', zorder=4)
        
    # 绘制海面 (Z=0) 参考圆
    ax_2d.plot(r_circle * np.cos(theta_circle), r_circle * np.sin(theta_circle), 
               'gray', linestyle=':', alpha=0.5, zorder=1, linewidth=1)
            
    # 绘制海面风矢量 (红色箭头)
    ax_2d.plot([0, w_u], [0, w_v], 'r-', linewidth=1, zorder=5)
    ax_2d.scatter(w_u, w_v, c='red', s=80, marker='.', zorder=6)
    ax_2d.text(w_u*0.8-0.05 , w_v*0.8 , f'风\n{ws}m/s', color='red', fontsize=8, ha='right', va='bottom', zorder=6)
    
    # 坐标轴设置
    ax_2d.set_xlim([-vel_limit, vel_limit])
    ax_2d.set_ylim([-vel_limit, vel_limit])
    ax_2d.set_xlabel('东向流速 u (m/s)', fontsize=8)
    ax_2d.set_ylabel('北向流速 v (m/s)', fontsize=8)
    ax_2d.set_title('Ekman 螺线 (水平投影俯视图)\n', fontsize=10, fontweight='bold', pad=5)
    ax_2d.grid(True, linestyle=':', alpha=0.6)
    ax_2d.set_aspect('equal', adjustable='box') # 保持 X Y 比例 1:1，防止螺旋线变形
    ax_2d.tick_params(axis='both', labelsize=7)
    plt.tight_layout()
    plt.tight_layout(pad=0.5)

    return fig_3d, fig_2d, f, d, V0, tau, sign_f	
	
#   return fig, f, d, V0, tau, sign_f

# 执行绘图函数
# fig, f, d, V0, tau, sign_f = plot_ekman_hodograph()
fig_3d, fig_2d, f, d, V0, tau, sign_f = plot_ekman_hodograph()


hemisphere_str = "北半球 (向右偏转 45°)" if sign_f > 0 else "南半球 (向左偏转 45°)"

st.markdown("---")
st.markdown("### 🌊 当前 Ekman 流场物理参数")
# 创建两列布局
col1, col2 = st.columns(2)

with col1:
    # 使用 #### 进一步增大参数行的字号，rf"" 确保 \tau 等反斜杠正确传递给 LaTeX 引擎
    f_mantissa, f_exp = f"{f:.2e}".split('e')
    f_latex = "${} \\times 10^{{{}}}$".format(f_mantissa, int(f_exp))
    st.markdown(f"#### 科氏参数 ($f$): {f_latex} 1/s")
    #st.markdown(rf"#### 科氏参数 ($f$): `{f:.2e}` 1/s")
    st.markdown(rf"#### 表层流速大小 ($V_0$): `{V0:.4f}` m/s")

with col2:
    st.markdown(rf"#### Ekman 深度（摩擦深度） ($D_0$): `{d*np.pi:.2f}` m")
    st.markdown(rf"#### 海面风应力 ($\tau$): `{tau:.4f}` N/m²")

# 偏转效应单独占一行，同样使用较大字号
st.markdown(rf"#### 偏转效应: {hemisphere_str}")

# 添加一条分隔线，使页面更整洁
st.markdown("---")

# 渲染图表
#col1, col2 = st.columns(2)

#with col1:
#    st.pyplot(fig_3d)

#with col2:
#    st.pyplot(fig_2d)
#st.pyplot(fig_3d)
#st.markdown("---") # 添加分隔线
#st.pyplot(fig_2d)

st.markdown("""
<style>
/* 强制主内容区的列容器使用 flex 布局，并使内部元素靠底部对齐 */
.main div[data-testid="column"] {
    display: flex !important;
    flex-direction: column !important;
    justify-content: flex-start !important;
}
.block-container {
    padding-top: 2.5rem !important;
    padding-bottom: 1rem !important;
}
</style>
""", unsafe_allow_html=True)

# 使用 st.columns 将两个图水平并列排列
col1, col2 = st.columns(2)

with col1:
    st.pyplot(fig_3d, use_container_width=False)

with col2:
    st.pyplot(fig_2d, use_container_width=False)
