# Minecraft 扫描 & 粘贴工具（基于 GDPC）

本项目提供一组简单脚本，用于在 Minecraft 中：

- **显示并围出一个扫描区域（玻璃围挡）**
- **扫描该区域内的方块并保存为地图文件 `scan_volume.npy`**
- **在指定坐标内将扫描出的结构粘贴出来**

适合用于复制建筑、备份结构或进行结构编辑实验。

---

## 环境依赖

- Python 3.x
- [GDPC](https://github.com/nilsgawlik/gdpc)  
- `numpy`

安装示例：

```bash
pip install gdpc numpy
