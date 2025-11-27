import requests

BASE = "http://localhost:9000"

def set_blocks(blocks):
    """一次性发送 blocks 列表到 GDMC"""
    r = requests.put(BASE + "/blocks", json=blocks)
    print(r.text)


# 扫描区域
x1, x2 = 0, 120
y1, y2 = 10, 110
z1, z2 = 0, 220

def place_glass_frame():
    blocks = []

    # X 方向的四条棱
    for x in range(x1, x2):
        blocks.append({"x": x, "y": y1, "z": z1, "id": "minecraft:glass"})
        blocks.append({"x": x, "y": y1, "z": z2-1, "id": "minecraft:glass"})
        blocks.append({"x": x, "y": y2-1, "z": z1, "id": "minecraft:glass"})
        blocks.append({"x": x, "y": y2-1, "z": z2-1, "id": "minecraft:glass"})

    # Z 方向的四条棱
    for z in range(z1, z2):
        blocks.append({"x": x1,   "y": y1,   "z": z, "id": "minecraft:glass"})
        blocks.append({"x": x2-1, "y": y1,   "z": z, "id": "minecraft:glass"})
        blocks.append({"x": x1,   "y": y2-1, "z": z, "id": "minecraft:glass"})
        blocks.append({"x": x2-1, "y": y2-1, "z": z, "id": "minecraft:glass"})

    # Y 方向的四条棱（竖直）
    for y in range(y1, y2):
        blocks.append({"x": x1,   "y": y, "z": z1,   "id": "minecraft:glass"})
        blocks.append({"x": x1,   "y": y, "z": z2-1, "id": "minecraft:glass"})
        blocks.append({"x": x2-1, "y": y, "z": z1,   "id": "minecraft:glass"})
        blocks.append({"x": x2-1, "y": y, "z": z2-1, "id": "minecraft:glass"})

    set_blocks(blocks)


# 执行：生成玻璃框
place_glass_frame()
print("Glass frame generated!")
