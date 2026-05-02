import struct
import os
import re
from PIL import Image
import numpy as np

IMG_EXT = ".png"

BLOCK_SIZE = 0xA4
HEADER_SIZE = 0x1C

EXPORT_DIR = "export"

# ==================================================
# mode=3：正片叠底（去白底）
# ==================================================
def apply_multiply(canvas, overlay, pos):
    x, y = pos
    canvas = canvas.convert("RGBA")
    overlay = overlay.convert("RGB")

    cw, ch = canvas.size
    ow, oh = overlay.size

    w = min(ow, cw - x)
    h = min(oh, ch - y)
    if w <= 0 or h <= 0:
        return canvas

    base_np = np.array(canvas, dtype=np.float32)
    over_np = np.array(overlay, dtype=np.float32)[:h, :w]

    region = base_np[y:y+h, x:x+w]
    region[..., :3] = region[..., :3] * over_np / 255.0

    base_np[y:y+h, x:x+w] = region
    return Image.fromarray(base_np.astype(np.uint8))

# ==================================================
# 读取 LSF（保持不改）
# ==================================================
def read_lsf(path):
    with open(path, "rb") as f:
        data = f.read()

    if data[:4] != b"LSF\x00":
        raise ValueError("Not LSF")

    layers = []
    off = HEADER_SIZE

    while off + BLOCK_SIZE <= len(data):
        name = data[off:off + 32].split(b"\0")[0].decode("ascii", errors="ignore")
        if not name:
            off += BLOCK_SIZE
            continue

        left, top, right, bottom = struct.unpack_from("<4I", data, off + 0x80)

        index   = data[off + 0x98]
        state   = data[off + 0x99]
        mode    = data[off + 0x9A]
        opacity = data[off + 0x9B]

        layers.append({
            "name": name,
            "index": index,
            "state": state,
            "mode": mode,
            "opacity": opacity,
            "offset": off,
            "left": left,
            "top": top,
            "right": right,
            "bottom": bottom,
        })

        off += BLOCK_SIZE

    return layers

# ==================================================
# thumb → state 修正
# ==================================================
def normalize_state(index, state):
    if index == 0 and state == 1:
        return 0
    return state

# ==================================================
# 解析 thumb（通用版）
# ==================================================
THUMB_RE = re.compile(r"^(EV_[A-Z]\d+)@(.+)\.png$", re.IGNORECASE)

def parse_thumb(name):
    m = THUMB_RE.match(name)
    if not m:
        return None

    base = m.group(1)
    state_part = m.group(2)

    # 提取所有数字，按顺序
    states = [int(x) for x in re.findall(r"\d+", state_part)]

    return {
        "lsf": base + ".lsf",
        "states": states
    }

# ==================================================
# 主流程
# ==================================================
def process_thumb(thumb):
    info = parse_thumb(thumb)
    if not info:
        return

    lsf_path = info["lsf"]
    if not os.path.exists(lsf_path):
        print(f"[跳过] 找不到 {lsf_path}")
        return

    print(f"\n========== 处理 {thumb} ==========")

    entries = read_lsf(lsf_path)

    groups = {}
    for e in entries:
        groups.setdefault(e["index"], []).append(e)

    index_seq = sorted(i for i in groups if i != 255)
    state_seq = info["states"]

    if len(state_seq) < len(index_seq):
        print(f"⚠ {thumb}: thumb state 数量少于 index 数量")

    base_entry = next(e for e in entries if e["index"] == 0 and e["state"] == 0)
    canvas = Image.open(base_entry["name"] + IMG_EXT).convert("RGBA")

    for idx, raw_state in zip(index_seq, state_seq):
        state = normalize_state(idx, raw_state)

        targets = [e for e in groups[idx] if e["state"] == state]
        if not targets:
            continue

        for t in targets:
            print(
                f"{thumb}: 渲染 {t['name']} "
                f"(index={idx}, state={state}, mode={t['mode']})"
            )

            img = Image.open(t["name"] + IMG_EXT)

            if t["mode"] == 0:
                img = img.convert("RGBA")
                canvas.alpha_composite(img, (t["left"], t["top"]))
            elif t["mode"] == 3:
                canvas = apply_multiply(canvas, img, (t["left"], t["top"]))

    out_name = os.path.splitext(thumb)[0] + "_COMPOSE.png"
    out_path = os.path.join(EXPORT_DIR, out_name)

    canvas.save(out_path)
    print(f"{thumb}: 输出完成 → {out_path}")
from multiprocessing import Pool, cpu_count

def main():
    cwd = os.getcwd()

    export_path = os.path.join(cwd, EXPORT_DIR)
    os.makedirs(export_path, exist_ok=True)   # ← 新增

    thumbs = [f for f in os.listdir(cwd) if f.lower().endswith(".png")]
    thumbs = [t for t in thumbs if parse_thumb(t)]

    if not thumbs:
        print("未找到可处理的 thumb")
        return

    with Pool(processes=cpu_count()) as pool:
        pool.map(process_thumb, thumbs)

# ==================================================
if __name__ == "__main__":
    main()
