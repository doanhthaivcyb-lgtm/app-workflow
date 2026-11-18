"""
workflow.py — Logic thuần (không có tkinter) cho app Weavy-clone v1.
Tách riêng để test headless được: topo sort, chạy tổng, chạy riêng,
engine MOCK tạo ảnh PNG thật bằng PIL, và lưu/tải JSON.

QUAN TRỌNG: Đây là bản MOCK. Model thật là Pax (Muse) trên cloud,
không phải file model cài vào máy Windows. Chạy thật = gửi workflow
JSON cho Pax trong chat Muse, Pax sẽ tạo ảnh/video thật.
Engine ở đây chỉ giả lập tại chỗ để luồng end-to-end chạy được.
"""
from __future__ import annotations

import hashlib
import json
import os
import textwrap
from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------- types
NODE_TYPES = {
    "prompt":    {"title": "Prompt",    "desc": "Nhập text / prompt đầu vào"},
    "image":     {"title": "Tạo ảnh",   "desc": "Tạo ảnh từ prompt (mock: PNG gradient)"},
    "video":     {"title": "Tạo video", "desc": "Tạo video từ prompt (mock: file mô tả + thumbnail)"},
    "remove_bg": {"title": "Xóa nền",   "desc": "Xóa nền ảnh đầu vào (mock)"},
    "upscale":   {"title": "Upscale",   "desc": "Phóng to ảnh đầu vào lên 1024x1024 (mock)"},
    "composite": {"title": "Ghép lớp",  "desc": "Ghép các ảnh đầu vào lại với nhau (mock)"},
}

STATUS_NOT_RUN = "Chưa chạy"
STATUS_RUNNING = "Đang chạy"
STATUS_DONE = "Xong"
STATUS_ERROR = "Lỗi"

# Node nào bắt buộc phải có đầu vào (dây nối từ node khác)
NEEDS_INPUT = {"remove_bg", "upscale", "composite"}
# Node nào bắt buộc phải có prompt/text
NEEDS_PROMPT = {"image", "video"}


@dataclass
class Node:
    id: str
    type: str
    title: str = ""
    prompt: str = ""
    x: int = 40
    y: int = 40
    status: str = STATUS_NOT_RUN
    output_path: str = ""
    error: str = ""

    def __post_init__(self):
        if not self.title:
            self.title = NODE_TYPES.get(self.type, {}).get("title", self.type)

    def to_dict(self) -> dict:
        return {
            "id": self.id, "type": self.type, "title": self.title,
            "prompt": self.prompt, "x": self.x, "y": self.y,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Node":
        return cls(
            id=d["id"], type=d["type"], title=d.get("title", ""),
            prompt=d.get("prompt", ""), x=int(d.get("x", 40)), y=int(d.get("y", 40)),
        )


@dataclass
class RunResult:
    node_id: str
    ok: bool
    message: str
    output_path: str = ""


class Workflow:
    """Một workflow = các node + các dây nối (edge) có hướng."""

    def __init__(self):
        self.nodes: dict[str, Node] = {}
        self.edges: list[tuple[str, str]] = []  # (from_id, to_id): to phụ thuộc from
        self._counter = 0

    # ---------------------------------------------------------- nodes
    def add_node(self, node_type: str, prompt: str = "", x: int = 40, y: int = 40) -> Node:
        if node_type not in NODE_TYPES:
            raise ValueError(f"Loại node không hợp lệ: {node_type}")
        self._counter += 1
        node_id = f"node_{self._counter}"
        node = Node(id=node_id, type=node_type, prompt=prompt, x=x, y=y)
        self.nodes[node_id] = node
        return node

    def remove_node(self, node_id: str) -> None:
        self.nodes.pop(node_id, None)
        self.edges = [e for e in self.edges if node_id not in e]

    def predecessors(self, node_id: str) -> list[Node]:
        return [self.nodes[a] for (a, b) in self.edges if b == node_id and a in self.nodes]

    def successors(self, node_id: str) -> list[Node]:
        return [self.nodes[b] for (a, b) in self.edges if a == node_id and b in self.nodes]

    # ---------------------------------------------------------- edges
    def add_edge(self, from_id: str, to_id: str) -> None:
        if from_id == to_id:
            raise ValueError("Không nối một node với chính nó.")
        if from_id not in self.nodes or to_id not in self.nodes:
            raise ValueError("Node đầu hoặc cuối dây không tồn tại.")
        if (from_id, to_id) in self.edges:
            raise ValueError("Dây nối này đã tồn tại.")
        self.edges.append((from_id, to_id))
        try:
            self.topo_sort()
        except ValueError:
            self.edges.pop()
            raise ValueError("Nối dây này sẽ tạo vòng lặp — đã hủy.")

    def remove_edge(self, from_id: str, to_id: str) -> None:
        self.edges = [e for e in self.edges if e != (from_id, to_id)]

    # ------------------------------------------------------- topo sort
    def topo_sort(self) -> list[str]:
        """Kahn. Trả về thứ tự node: node không phụ thuộc ai chạy trước.
        Raise ValueError nếu có vòng lặp."""
        indeg = {nid: 0 for nid in self.nodes}
        adj: dict[str, list[str]] = {nid: [] for nid in self.nodes}
        for a, b in self.edges:
            adj[a].append(b)
            indeg[b] += 1
        queue = [nid for nid, d in indeg.items() if d == 0]
        order: list[str] = []
        while queue:
            nid = queue.pop(0)
            order.append(nid)
            for nxt in adj[nid]:
                indeg[nxt] -= 1
                if indeg[nxt] == 0:
                    queue.append(nxt)
        if len(order) != len(self.nodes):
            raise ValueError("Workflow có vòng lặp, không sắp xếp topo được.")
        return order

    # ------------------------------------------------------------ save
    def to_dict(self) -> dict:
        return {
            "version": 1,
            "app": "weavy-clone-mock-v1",
            "nodes": [n.to_dict() for n in self.nodes.values()],
            "edges": [{"from": a, "to": b} for a, b in self.edges],
        }

    def save(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "Workflow":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        wf = cls()
        for nd in data.get("nodes", []):
            node = Node.from_dict(nd)
            wf.nodes[node.id] = node
            try:
                num = int(node.id.split("_")[-1])
                wf._counter = max(wf._counter, num)
            except ValueError:
                pass
        for e in data.get("edges", []):
            if e["from"] in wf.nodes and e["to"] in wf.nodes:
                wf.edges.append((e["from"], e["to"]))
        return wf


# ---------------------------------------------------------------- mock
def _gradient_png(path: Path, prompt: str, size=(512, 512), label: str = "MOCK") -> Path:
    """Tạo PNG thật: gradient theo hash của prompt + ghi prompt lên ảnh."""
    from PIL import Image, ImageDraw, ImageFont
    h = int(hashlib.md5(prompt.encode("utf-8")).hexdigest()[:6], 16)
    r, g, b = (h >> 16) & 255, (h >> 8) & 255, h & 255
    img = Image.new("RGB", size, (r, g, b))
    draw = ImageDraw.Draw(img)
    w, hh = size
    for y in range(hh):
        t = y / max(hh - 1, 1)
        draw.line([(0, y), (w, y)], fill=(
            int(r + (255 - r) * t * 0.4), int(g + (255 - g) * t * 0.4),
            int(b + (255 - b) * t * 0.4)))
    try:
        font = ImageFont.truetype("arial.ttf", 20)
        small = ImageFont.truetype("arial.ttf", 14)
    except Exception:
        font = ImageFont.load_default()
        small = font
    draw.text((16, 16), f"[{label}] MOCK — Pax chưa chạy thật", fill=(255, 255, 255), font=small)
    lines = textwrap.wrap(prompt or "(không có prompt)", width=32)
    y = 60
    for line in lines[:10]:
        draw.text((16, y), line, fill=(255, 255, 255), font=font)
        y += 28
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path)
    return path


def run_node(wf: Workflow, node: Node, output_dir: str | Path) -> RunResult:
    """Chạy MOCK một node duy nhất. Không tự chạy node phụ thuộc."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    node.status = STATUS_RUNNING
    node.error = ""

    try:
        # --- kiểm tra đầu vào bắt buộc
        preds = wf.predecessors(node.id)
        if node.type in NEEDS_INPUT:
            if not preds:
                raise RuntimeError(
                    f"Node '{node.title}' cần nối dây từ node trước (ví dụ Tạo ảnh). "
                    "Bấm cổng Out của node trước, rồi bấm cổng In của node này.")
            ready = [p for p in preds if p.status == STATUS_DONE and p.output_path
                     and Path(p.output_path).exists() and p.output_path.endswith(".png")]
            if not ready:
                names = ", ".join(p.title for p in preds)
                raise RuntimeError(
                    f"Node đầu vào ({names}) chưa chạy xong hoặc chưa có ảnh PNG. "
                    "Hãy bấm 'Chạy' riêng cho node đầu vào trước, hoặc dùng 'Chạy tổng'.")

        if node.type in NEEDS_PROMPT and not node.prompt.strip():
            raise RuntimeError(f"Node '{node.title}' chưa có prompt. Nhập prompt rồi chạy lại.")

        # --- thực thi theo loại
        if node.type == "prompt":
            node.output_path = ""
            return _done(node, f"Prompt đã nhận: {node.prompt.strip()[:80]}")

        if node.type == "image":
            p = out / f"{node.id}_anh.png"
            _gradient_png(p, node.prompt, size=(512, 512), label="ANH")
            node.output_path = str(p)
            return _done(node, f"Đã tạo ảnh mock: {p.name}", str(p))

        if node.type == "video":
            thumb = out / f"{node.id}_video_thumb.png"
            _gradient_png(thumb, node.prompt, size=(512, 512), label="VIDEO")
            desc = out / f"{node.id}_video.txt"
            desc.write_text(
                "MOCK VIDEO — chưa phải video thật.\n"
                f"Prompt: {node.prompt}\nThời lượng giả lập: 10 giây\n"
                "Chạy thật bằng Pax: gửi workflow này cho Pax trong chat Muse, "
                "Pax sẽ tạo video thật (tối đa 6 clip ~10 giây/lần).\n"
                f"Thumbnail: {thumb.name}\n", encoding="utf-8")
            node.output_path = str(desc)
            return _done(node, f"Đã tạo mô tả video mock: {desc.name} (+ thumbnail)", str(desc))

        if node.type == "remove_bg":
            src = Path(wf.predecessors(node.id)[0].output_path)
            # mock: mở ảnh gốc, vẽ khung trắng + ghi chú, lưu bản mới
            from PIL import Image, ImageDraw
            img = Image.open(src).convert("RGB")
            d = ImageDraw.Draw(img)
            d.rectangle([8, 8, img.width - 8, 40], fill=(255, 255, 255))
            d.text((14, 16), "Da xoa nen (MOCK)", fill=(0, 0, 0))
            p = out / f"{node.id}_xoanen.png"
            img.save(p)
            node.output_path = str(p)
            return _done(node, f"Đã xóa nền (mock): {p.name}", str(p))

        if node.type == "upscale":
            src = Path(_first_png_pred(wf, node))
            from PIL import Image
            img = Image.open(src).convert("RGB").resize((1024, 1024), Image.LANCZOS)
            p = out / f"{node.id}_upscale.png"
            img.save(p)
            node.output_path = str(p)
            return _done(node, f"Đã upscale lên 1024x1024 (mock): {p.name}", str(p))

        if node.type == "composite":
            from PIL import Image
            imgs = []
            for pred in wf.predecessors(node.id):
                if pred.output_path.endswith(".png") and Path(pred.output_path).exists():
                    imgs.append(Image.open(pred.output_path).convert("RGB"))
            if not imgs:
                raise RuntimeError("Không có ảnh đầu vào nào để ghép.")
            h = max(i.height for i in imgs)
            total_w = sum(i.width for i in imgs)
            canvas = Image.new("RGB", (total_w, h), (20, 20, 30))
            x = 0
            for i in imgs:
                canvas.paste(i, (x, 0))
                x += i.width
            p = out / f"{node.id}_ghep.png"
            canvas.save(p)
            node.output_path = str(p)
            return _done(node, f"Đã ghép {len(imgs)} ảnh (mock): {p.name}", str(p))

        raise RuntimeError(f"Loại node chưa hỗ trợ: {node.type}")

    except Exception as exc:  # noqa: BLE001 - báo lỗi rõ cho người dùng
        node.status = STATUS_ERROR
        node.error = str(exc)
        return RunResult(node.id, False, f"LOI {node.title}: {exc}")


def _done(node: Node, message: str, output_path: str = "") -> RunResult:
    node.status = STATUS_DONE
    node.output_path = output_path
    return RunResult(node.id, True, message, output_path)


def _first_png_pred(wf: Workflow, node: Node) -> str:
    for pred in wf.predecessors(node.id):
        if pred.output_path.endswith(".png") and Path(pred.output_path).exists():
            return pred.output_path
    raise RuntimeError("Node đầu vào chưa có ảnh PNG để xử lý.")


def run_all(wf: Workflow, output_dir: str | Path, stop_on_error: bool = True):
    """Chạy tổng: theo thứ tự topo. LỰA CHỌN ĐÃ CHỐT: dừng ngay khi
    một node lỗi (stop_on_error=True mặc định) và báo rõ node nào lỗi,
    các node sau chưa chạy. Muốn chạy tiếp thì sửa node lỗi rồi bấm
    'Chạy tổng' lại (các node đã Xong sẽ chạy lại từ đầu — bản v1 chưa
    có cache bỏ qua node đã xong) hoặc bấm 'Chạy' riêng từng node sau.
    Trả về (results, logs, stopped_early)."""
    order = wf.topo_sort()
    logs: list[str] = [f"Chạy tổng: thứ tự topo = {[wf.nodes[i].title for i in order]}"]
    results: list[RunResult] = []
    stopped_early = False
    for nid in order:
        node = wf.nodes[nid]
        res = run_node(wf, node, output_dir)
        results.append(res)
        logs.append(("OK  " if res.ok else "LOI ") + res.message)
        if not res.ok and stop_on_error:
            logs.append(f"DỪNG chạy tổng tại node '{node.title}' (lỗi). Các node sau chưa chạy.")
            stopped_early = True
            break
    if not stopped_early:
        logs.append("Chạy tổng hoàn tất: tất cả node đều Xong.")
    return results, logs, stopped_early


def run_single(wf: Workflow, node_id: str, output_dir: str | Path) -> RunResult:
    """Chạy riêng chỉ một node, không chạy node khác."""
    if node_id not in wf.nodes:
        raise ValueError(f"Không có node {node_id}")
    return run_node(wf, wf.nodes[node_id], output_dir)


def create_sample_workflow() -> Workflow:
    """Workflow mẫu: Prompt -> Tạo ảnh -> Upscale."""
    wf = Workflow()
    p = wf.add_node("prompt", prompt="Hoàng hôn trên biển, phong cách anime Nhật Bản", x=40, y=60)
    img = wf.add_node("image", prompt="Hoàng hôn trên biển, phong cách anime Nhật Bản", x=320, y=60)
    up = wf.add_node("upscale", prompt="", x=600, y=60)
    wf.add_edge(p.id, img.id)
    wf.add_edge(img.id, up.id)
    return wf
