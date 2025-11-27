import numpy as np
import requests
from tqdm import tqdm

# =========================================================
# 读取扫描数据
# =========================================================
volume = np.load("scan_volume.npy")  # shape: [NY, NZ, NX]
NY, NZ, NX = volume.shape

# =========================================================
# 原始扫描区域（你扫描时的设置必须一致）
# =========================================================
x1, x2 = 0, 100
y1, y2 = 10, 110
z1, z2 = 0, 100

# =========================================================
# 自动计算目标区域（扫描区域右侧）
# =========================================================
tx1 = x2          # 紧贴右侧
tz1 = z1
ty1 = y1

tx2 = tx1 + NX    # 目标区域大小与扫描区域一致
tz2 = tz1 + NZ

# 注意：高度清空我们将覆盖 0~319
CLEAR_Y_MIN = 0
CLEAR_Y_MAX = 320

# =========================================================
# Block ID → Minecraft 名称映射
# =========================================================
id_to_block = {
    0: "minecraft:air",
    1: "minecraft:stone",
    2: "minecraft:dirt",
    3: "minecraft:stone",
    5: "minecraft:water",
    6: "minecraft:oak_log",
    7: "minecraft:oak_leaves",
}

def get_block_name(block_id):
    return id_to_block.get(block_id, "minecraft:stone")


# =========================================================
# 批量方块设置 API
# =========================================================
BASE = "http://127.0.0.1:9000"
BATCH_SIZE = 4096  # 每批发送数量

def set_blocks_batch(blocks):
    try:
        r = requests.put(BASE + "/blocks", json=blocks, timeout=10)
        if r.status_code != 200:
            print(f"[FAIL BATCH] {r.status_code} - {r.text}")
            return False
        return True
    except Exception as e:
        print(f"[EXCEPTION] {e}")
        return False


# =========================================================
# 第 1 步：清空整个高度范围 (Y=0~319)
# =========================================================
print(f"🧹 正在清空区域 X[{tx1},{tx2}), Z[{tz1},{tz2}), Y[0,319] ...")

blocks = []
cleared = 0

for y in tqdm(range(CLEAR_Y_MIN, CLEAR_Y_MAX), desc="Clearing Y"):
    for z in range(tz1, tz2):
        for x in range(tx1, tx2):
            blocks.append({
                "x": x,
                "y": y,
                "z": z,
                "id": "minecraft:air",
            })

            if len(blocks) >= BATCH_SIZE:
                set_blocks_batch(blocks)
                cleared += len(blocks)
                blocks = []

# 发送剩余的
if blocks:
    set_blocks_batch(blocks)
    cleared += len(blocks)

print(f"✅ 清空完成！总计清空方块数：{cleared}")


# =========================================================
# 第 2 步：复制扫描区域到目标区域
# =========================================================
print(f"🧱 开始复制扫描数据到目标区域 ({tx1}, {ty1}, {tz1})...")

blocks = []
success_count = 0
fail_count = 0

for dy in tqdm(range(NY), desc="Copying Y"):
    for dz in range(NZ):
        for dx in range(NX):
            block_id = volume[dy, dz, dx]

            # 可以选择跳过空气（提高效率）
            if block_id == 0:
                continue

            block_name = get_block_name(block_id)

            x = tx1 + dx
            y = ty1 + dy
            z = tz1 + dz

            blocks.append({
                "x": x,
                "y": y,
                "z": z,
                "id": block_name,
            })

            if len(blocks) >= BATCH_SIZE:
                ok = set_blocks_batch(blocks)
                if ok:
                    success_count += len(blocks)
                else:
                    fail_count += len(blocks)
                blocks = []

# 发送剩余
if blocks:
    ok = set_blocks_batch(blocks)
    if ok:
        success_count += len(blocks)
    else:
        fail_count += len(blocks)

print(f"✅ 复制完成！成功 {success_count} 个，失败 {fail_count} 个方块。")
