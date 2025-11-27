import requests
import numpy as np
from tqdm import tqdm
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
import pyvista as pv

BASE = "http://127.0.0.1:9000"
session = requests.Session()

# -----------------------------
# 方块颜色
# -----------------------------
colors = [
    (0, 0, 0, 0),              # 0 air（透明）
    (0.75, 0.75, 0.75, 1),     # 1 unknown
    (0.58, 0.44, 0.28, 1),     # 2 dirt / grass
    (0.53, 0.53, 0.53, 1),     # 3 stone
    (0.25, 0.8, 0.25, 1),      # 4 unused
    (0.24, 0.45, 0.85, 0.85),  # 5 water ✔ 新增水体真实颜色
    (0.50, 0.32, 0.13, 1),     # 6 log
    (0.20, 0.55, 0.20, 1),     # 7 leaves
]

cmap = ListedColormap(colors)

# -----------------------------
# 扫描区域
# -----------------------------
x1, x2 = 0, 100
y1, y2 = 10, 110
z1, z2 = 0, 100

NX = x2 - x1
NY = y2 - y1
NZ = z2 - z1


def normalize(name):
    if "[" in name:
        name = name.split("[")[0]
    return name


def classify(name):
    if name in ("minecraft:air", "minecraft:cave_air", "minecraft:void_air"):
        return 0

    if name in ("minecraft:dirt", "minecraft:coarse_dirt", "minecraft:grass_block"):
        return 2

    if name in ("minecraft:stone", "minecraft:cobblestone"):
        return 3

    if name in ("minecraft:water", "minecraft:flowing_water"):
        return 5  # ✔ 水体编号 = 5（对应颜色 LUT）

    if name.startswith("minecraft:oak_log") or name.endswith("_log"):
        return 6

    if name.endswith("_leaves"):
        return 7

    return 1


# 将线性返回的 N 个方块转成 3D 数组
def list_to_3d(block_list, dx, dy, dz):
    arr = [[[None for _ in range(dx)] for _ in range(dz)] for _ in range(dy)]
    for i, block in enumerate(block_list):
        ix = i // (dy * dz)
        iy = (i // dz) % dy
        iz = i % dz
        arr[iy][iz][ix] = block["id"]
    return arr


def get_cube(x, y, z, dx=16, dy=16, dz=16):
    url = f"{BASE}/blocks?x={x}&y={y}&z={z}&dx={dx}&dy={dy}&dz={dz}"
    try:
        raw = session.get(url, timeout=1).json()
        return list_to_3d(raw, dx, dy, dz)
    except:
        return list_to_3d([{"id": "minecraft:air"}] * (dx * dy * dz), dx, dy, dz)


# -----------------------------
# 扫描 3D 区域
# -----------------------------
volume = np.zeros((NY, NZ, NX), dtype=int)

print("Scanning...")

for Y in tqdm(range(y1, y2, 16)):
    for Z in range(z1, z2, 16):
        for X in range(x1, x2, 16):

            cube = get_cube(X, Y, Z, 16, 16, 16)

            for dy in range(16):
                for dz in range(16):
                    for dx in range(16):
                        yy = Y + dy
                        zz = Z + dz
                        xx = X + dx
                        if xx >= x2 or yy >= y2 or zz >= z2:
                            continue

                        name = normalize(cube[dy][dz][dx])
                        volume[yy - y1, zz - z1, xx - x1] = classify(name)

print("3D scan complete!")

import vtk
from vtkmodules.util import numpy_support

# -----------------------------
# Minecraft: NY × NZ × NX  →  PyVista: NX × NY × NZ
# -----------------------------
voxels = volume.transpose(2, 0, 1).astype(np.uint8)
NX, NY, NZ = voxels.shape

# -----------------------------
# 创建 ImageData
# -----------------------------
grid = pv.ImageData()
grid.dimensions = (NX + 1, NY + 1, NZ + 1)
grid.spacing = (1, 1, 1)
grid.origin = (0, 0, 0)

# -----------------------------
# 写入 cell_data
# -----------------------------
vtk_data = numpy_support.numpy_to_vtk(
    voxels.ravel(order="F"),
    deep=True,
    array_type=vtk.VTK_UNSIGNED_CHAR
)
vtk_data.SetName("block")
grid.cell_data["block"] = vtk_data

# -----------------------------
# 删除空气 (block == 0)
# -----------------------------
solid = grid.threshold(0.5, scalars="block")
scalar_name = "block"

print("=== Available cell_data arrays ===")
print(solid.cell_data.keys())

# -----------------------------
# 定义哪些 block 是半透明
# -----------------------------
TRANSPARENT = {5, 8, 15}   # 水、冰、玻璃等的 block-id

# -----------------------------
# 创建 LUT（颜色 + 自定义透明度）
# -----------------------------
lut = vtk.vtkLookupTable()
lut.SetNumberOfTableValues(len(colors))
lut.Build()

for block_id, c in enumerate(colors):
    r, g, b, _ = c  # 颜色来自你的 colors 列表

    if block_id == 0:
        a = 0.0             # 空气完全透明
    elif block_id in TRANSPARENT:
        a = 0.35            # 半透明
    else:
        a = 1.0             # 不透明

    lut.SetTableValue(block_id, r, g, b, a)

# -----------------------------
# Mapper 绑定 LUT
# -----------------------------
mapper = vtk.vtkDataSetMapper()
mapper.SetInputData(solid)
mapper.SetLookupTable(lut)
mapper.SetScalarRange(0, len(colors) - 1)
mapper.SetColorModeToMapScalars()
mapper.ScalarVisibilityOn()
mapper.SetScalarModeToUseCellData()

# -----------------------------
# Actor
# -----------------------------
# -----------------------------
# Actor
# -----------------------------
actor = vtk.vtkActor()
actor.SetMapper(mapper)

# 透明属性（旧版本 VTK 支持）
prop = actor.GetProperty()
prop.SetOpacity(1.0)                 # 默认不透明
prop.SetBackfaceCulling(0)
prop.SetFrontfaceCulling(0)
prop.SetInterpolationToFlat()

# -----------------------------
# PyVista Plotter
# -----------------------------
plotter = pv.Plotter()

# 启用透明渲染（Depth Peeling）
renderer = plotter.renderer
renderer.SetUseDepthPeeling(True)
renderer.SetMaximumNumberOfPeels(100)
renderer.SetOcclusionRatio(0.1)

# 加入 actor
plotter.add_actor(actor)

# 背景与视角
plotter.set_background("white")
plotter.view_isometric()

# 显示
plotter.show()
# 保存数据为 NumPy 文件
np.save("scan_volume.npy", volume)

# 或保存为 PyVista 网格（去掉空气）
solid.save("scan_solid.vti")

print("Scan data saved to 'scan_volume.npy' and 'scan_solid.vti'")
