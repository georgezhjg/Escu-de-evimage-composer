# Escu-de-evimage-composer
For technical testing purposes only. 
This project can composite PNG files unpacked by Garbro, and uses multi-threading to boost efficiency on multi-core systems.
这个项目支持对Garbro解包得到的png文件进行合成，并且在多核情况下可以多线程处理以提升效率。

以下是输入素材说明。
经过分析，ev.bin下是独立的差分文件，游戏中的每个场景对拆分进行自主选取、组合。
因此，本工程创新地使用thumb（缩略图）的文件名进行抓取和合成，可以完全复刻游戏内的场景组合，而不涉及游戏源码，实现了通用性。
使用时，需将compose++.py和缩略图素材，ev.bin内的 差分素材和.lsf文件 放入同级文件夹内。
请注意，.lsf文件是必须的，图层偏移信息在其中。
