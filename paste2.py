import numpy as np
import requests
from tqdm import tqdm

# =========================================================
# 读取扫描数据（scan.py 生成的）
# =========================================================
volume = np.load("scan_volume.npy")  # shape: [NY, NZ, NX]
NY, NZ, NX = volume.shape
print("Loaded volume:", volume.shape)

# =========================================================
# 原始扫描区域（只是用来算“贴到右边”的水平位置）
# 这里是你当时扫描用的 XZ 范围：0~100
# =========================================================
SRC_X1, SRC_X2 = 0, 100
SRC_Z1, SRC_Z2 = 0, 100

# =========================================================
# 超平坦世界里你想让树“立起来的地面高度”
# 在 MC 里按 F3，看你脚下所在的 Block: x y z
# 把那个 y 填到这里，比如你截图里是 270：
# =========================================================
BASE_Y = 270  # ← 如果你在新世界想放在别的高度，就改这里

# =========================================================
# 目标区域：紧贴在原扫描区域的右侧
# =========================================================
DEST_X1 = SRC_X2          # 紧贴右侧
DEST_Z1 = SRC_Z1
DEST_Y1 = BASE_Y          # 从超平坦世界的这个高度开始放

DEST_X2 = DEST_X1 + NX
DEST_Z2 = DEST_Z1 + NZ
DEST_Y2 = DEST_Y1 + NY

# 我们只清空树要占用的这个高度带，避免全图乱清
CLEAR_Y_MIN = DEST_Y1
CLEAR_Y_MAX = DEST_Y2

# =========================================================
# Block ID → Minecraft 方块名映射
#   重点：
#   - 1 和 6 统统变成 minecraft:cherry_wood
#   - 7 是 minecraft:cherry_leaves
#   - 54 是 minecraft:red_concrete
# =========================================================
id_to_block = {
    0:  "minecraft:air",

    # ❗木头类：包括 cherry_wood 被归到的 class=1
    1:  "minecraft:cherry_wood",
    6:  "minecraft:cherry_wood",

    # 基础地形
    2:  "minecraft:grass_block",
    3:  "minecraft:stone",
    5:  "minecraft:water",

    # 叶子类
    7:  "minecraft:cherry_leaves",

    # 羊毛（如果 scan 里用到了 10~25）
    10: "minecraft:white_wool",
    11: "minecraft:orange_wool",
    12: "minecraft:magenta_wool",
    13: "minecraft:light_blue_wool",
    14: "minecraft:yellow_wool",
    15: "minecraft:lime_wool",
    16: "minecraft:pink_wool",
    17: "minecraft:gray_wool",
    18: "minecraft:light_gray_wool",
    19: "minecraft:cyan_wool",
    20: "minecraft:purple_wool",
    21: "minecraft:blue_wool",
    22: "minecraft:brown_wool",
    23: "minecraft:green_wool",
    24: "minecraft:red_wool",
    25: "minecraft:black_wool",

    # 混凝土 / 粘土 / 红色带子
    40: "minecraft:white_concrete",
    41: "minecraft:orange_concrete",
    42: "minecraft:magenta_concrete",
    43: "minecraft:light_blue_concrete",
    44: "minecraft:yellow_concrete",
    45: "minecraft:lime_concrete",
    46: "minecraft:pink_concrete",
    47: "minecraft:gray_concrete",
    48: "minecraft:light_gray_concrete",
    49: "minecraft:cyan_concrete",
    50: "minecraft:purple_concrete",
    51: "minecraft:blue_concrete",
    52: "minecraft:brown_concrete",
    53: "minecraft:clay",             # 我们在 scan 里让 clay/某些混凝土用了 53
    54: "minecraft:red_concrete",     # 红色“藤蔓/绳子”
    55: "minecraft:black_concrete",
}


def get_block_name(block_id: int) -> str:
    """从体素 id 映射到具体的 Minecraft 方块名"""
    return id_to_block.get(block_id, "minecraft:stone")


# =========================================================
# 批量方块设置 API
# =========================================================
BASE_URL = "http://127.0.0.1:9000"
BATCH_SIZE = 4096  # 每批发送数量


def set_blocks_batch(blocks):
    try:
        r = requests.put(BASE_URL + "/blocks", json=blocks, timeout=10)
        if r.status_code != 200:
            print(f"[FAIL BATCH] {r.status_code} - {r.text}")
            return False
        return True
    except Exception as e:
        print(f"[EXCEPTION] {e}")
        return False


# =========================================================
# 第 1 步：清空目标区域 X[DEST_X1,DEST_X2), Z[DEST_Z1,DEST_Z2), Y[DEST_Y1,DEST_Y2)
# =========================================================
print(
    f"🧹 正在清空区域 X[{DEST_X1},{DEST_X2}), "
    f"Z[{DEST_Z1},{DEST_Z2}), Y[{CLEAR_Y_MIN},{CLEAR_Y_MAX}) ..."
)

blocks = []
cleared = 0

for y in tqdm(range(CLEAR_Y_MIN, CLEAR_Y_MAX), desc="Clearing Y"):
    for z in range(DEST_Z1, DEST_Z2):
        for x in range(DEST_X1, DEST_X2):
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
# 第 2 步：把扫描出来的 volume 复制到目标区域
# =========================================================
print(f"🧱 开始复制扫描数据到目标区域 ({DEST_X1}, {DEST_Y1}, {DEST_Z1})...")

blocks = []
success_count = 0
fail_count = 0

for dy in tqdm(range(NY), desc="Copying Y"):
    for dz in range(NZ):
        for dx in range(NX):
            block_id = int(volume[dy, dz, dx])

            # 跳过空气
            if block_id == 0:
                continue

            block_name = get_block_name(block_id)

            x = DEST_X1 + dx
            y = DEST_Y1 + dy
            z = DEST_Z1 + dz

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
