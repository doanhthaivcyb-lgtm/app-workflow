"""
weavy_app.py — App desktop v1 giống Figma Weave / Weavy (bản MOCK).
Giao diện tiếng Việt, CustomTkinter, dark theme, chạy trên Windows.

ĐIỂM QUAN TRỌNG NHẤT:
- 1 nút "▶ Chạy tổng" ở thanh trên cùng: chạy toàn bộ workflow theo
  thứ tự topo dựa trên dây nối. DỪNG NGAY khi một node lỗi và báo rõ
  node nào lỗi, các node sau chưa chạy (lựa chọn đã chốt, xem README).
- MỖI node đều có nút "Chạy" riêng: chỉ chạy node đó, không chạy cả workflow.

Model thật là Pax (Muse) trên cloud, KHÔNG phải file model trong máy.
Bản này chạy MOCK tại chỗ: tạo ảnh PNG thật bằng PIL, video chỉ tạo
file mô tả + thumbnail. Chạy thật = gửi workflow JSON cho Pax trong
chat Muse (xem README.md).
"""
from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from workflow import (
    NODE_TYPES, STATUS_DONE, STATUS_ERROR, STATUS_RUNNING,
    Workflow, create_sample_workflow, run_all, run_single,
)

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "outputs"

NODE_W, NODE_H = 230, 195
STATUS_COLOR = {"Chưa chạy": "gray", "Đang chạy": "#E8A317", "Xong": "#2ECC71", "Lỗi": "#E74C3C"}

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class WeavyApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Weavy Clone v1 — MOCK (Model thật: Pax)")
        self.geometry("1100x720")
        self.workflow = Workflow()
        self.widgets: dict[str, ctk.CTkFrame] = {}
        self.windows: dict[str, int] = {}   # node_id -> canvas window id
        self.textboxes: dict[str, ctk.CTkTextbox] = {}
        self.status_labels: dict[str, ctk.CTkLabel] = {}
        self.pending_from: str | None = None

        self._build_topbar()
        self._build_canvas()
        self._build_log()
        self.log("App đã mở. Đây là BẢN MOCK — chạy thật bằng Pax, xem README.md.")
        self.log("Cách nối dây: bấm nút 'Ra ●' của node trước, rồi bấm '● Vào' của node sau.")
        self.load_sample(silent=True)

    # ---------------------------------------------------------------- UI
    def _build_topbar(self):
        top = ctk.CTkFrame(self, height=96)
        top.pack(fill="x", padx=8, pady=(8, 4))
        ctk.CTkLabel(top, text="Weavy Clone v1 — Node Canvas (MOCK)",
                     font=ctk.CTkFont(size=17, weight="bold")).pack(anchor="w", padx=10, pady=(6, 0))
        ctk.CTkLabel(top, text="⚠ BẢN MOCK: tạo ảnh PNG giả lập tại chỗ. Chạy thật = gửi workflow JSON cho Pax trong chat Muse.",
                     text_color="#E8A317", font=ctk.CTkFont(size=12)).pack(anchor="w", padx=10)

        row = ctk.CTkFrame(top, fg_color="transparent")
        row.pack(fill="x", padx=8, pady=6)
        self.add_menu = ctk.CTkOptionMenu(row, values=[NODE_TYPES[k]["title"] for k in NODE_TYPES])
        self.add_menu.pack(side="left", padx=4)
        ctk.CTkButton(row, text="+ Thêm node", width=100, command=self.on_add_node).pack(side="left", padx=4)
        # NÚT CHẠY TỔNG — nút chính, nổi bật
        ctk.CTkButton(row, text="▶  CHẠY TỔNG", width=140, height=36,
                      fg_color="#1E8449", hover_color="#27AE60",
                      font=ctk.CTkFont(size=14, weight="bold"),
                      command=self.on_run_all).pack(side="left", padx=8)
        ctk.CTkButton(row, text="Lưu workflow", width=110, command=self.on_save).pack(side="left", padx=4)
        ctk.CTkButton(row, text="Tải workflow", width=110, command=self.on_load).pack(side="left", padx=4)
        ctk.CTkButton(row, text="Workflow mẫu", width=120, command=lambda: self.load_sample()).pack(side="left", padx=4)
        ctk.CTkButton(row, text="Xóa canvas", width=100, fg_color="#922B21", hover_color="#C0392B",
                      command=self.on_clear).pack(side="left", padx=4)

    def _build_canvas(self):
        frame = ctk.CTkFrame(self)
        frame.pack(fill="both", expand=True, padx=8, pady=4)
        self.canvas = tk.Canvas(frame, bg="#1a1a22", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        ctk.CTkLabel(frame, text="Kéo tiêu đề node để di chuyển. Nút 'Chạy' trên mỗi node = chạy riêng node đó.",
                     text_color="gray").pack(anchor="w", padx=6)

    def _build_log(self):
        frame = ctk.CTkFrame(self, height=150)
        frame.pack(fill="x", padx=8, pady=(4, 8))
        ctk.CTkLabel(frame, text="Nhật ký chạy:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=8, pady=(4, 0))
        self.log_box = ctk.CTkTextbox(frame, height=110)
        self.log_box.pack(fill="x", padx=8, pady=4)

    def log(self, msg: str):
        self.log_box.insert("end", msg + "\n")
        self.log_box.see("end")
        self.update_idletasks()

    # ------------------------------------------------------------- nodes
    def on_add_node(self):
        title = self.add_menu.get()
        node_type = next(k for k, v in NODE_TYPES.items() if v["title"] == title)
        import random
        x = 40 + random.randint(0, 500)
        y = 40 + random.randint(0, 200)
        node = self.workflow.add_node(node_type, x=x, y=y)
        self._create_node_widget(node)
        self.draw_lines()
        self.log(f"Đã thêm node: {node.title} ({node.id})")

    def _create_node_widget(self, node):
        fr = ctk.CTkFrame(self.canvas, width=NODE_W, height=NODE_H, corner_radius=10,
                          border_width=2, border_color="#3a3a4a")
        header = ctk.CTkLabel(fr, text=f"{node.title}  •  {node.id}",
                              font=ctk.CTkFont(size=13, weight="bold"))
        header.pack(fill="x", padx=8, pady=(6, 0))
        header.bind("<Button-1>", lambda e, nid=node.id: self._drag_start(e, nid))
        header.bind("<B1-Motion>", lambda e, nid=node.id: self._drag_move(e, nid))

        status = ctk.CTkLabel(fr, text=f"Trạng thái: {node.status}", text_color=STATUS_COLOR[node.status])
        status.pack(anchor="w", padx=8)
        self.status_labels[node.id] = status

        tb = ctk.CTkTextbox(fr, height=55)
        tb.pack(fill="x", padx=8, pady=4)
        if node.prompt:
            tb.insert("1.0", node.prompt)
        elif node.type == "prompt":
            tb.insert("1.0", "Nhập prompt ở đây...")
        self.textboxes[node.id] = tb

        row = ctk.CTkFrame(fr, fg_color="transparent")
        row.pack(fill="x", padx=6, pady=4)
        ctk.CTkButton(row, text="● Vào", width=52, command=lambda nid=node.id: self.on_in_clicked(nid)).pack(side="left", padx=2)
        ctk.CTkButton(row, text="Chạy", width=58, fg_color="#1E8449",
                      command=lambda nid=node.id: self.on_run_single(nid)).pack(side="left", padx=2)
        ctk.CTkButton(row, text="Ra ●", width=52, command=lambda nid=node.id: self.on_out_clicked(nid)).pack(side="left", padx=2)
        ctk.CTkButton(row, text="✕", width=32, fg_color="#922B21",
                      command=lambda nid=node.id: self.on_delete_node(nid)).pack(side="left", padx=2)

        win = self.canvas.create_window(node.x, node.y, window=fr, anchor="nw",
                                        width=NODE_W, height=NODE_H)
        self.widgets[node.id] = fr
        self.windows[node.id] = win

    def _drag_start(self, event, node_id):
        self._drag_offset = (event.x, event.y)

    def _drag_move(self, event, node_id):
        node = self.workflow.nodes[node_id]
        dx, dy = self._drag_offset
        node.x = max(0, self.canvas.canvasx(event.x) - dx) if False else node.x
        # Tọa độ cửa sổ canvas: dùng vị trí chuột tuyệt đối trên canvas
        cx = self.canvas.winfo_pointerx() - self.canvas.winfo_rootx()
        cy = self.canvas.winfo_pointery() - self.canvas.winfo_rooty()
        node.x, node.y = max(0, cx - dx), max(0, cy - dy)
        self.canvas.coords(self.windows[node_id], node.x, node.y)
        self.draw_lines()

    def draw_lines(self):
        self.canvas.delete("wire")
        for a, b in self.workflow.edges:
            if a not in self.workflow.nodes or b not in self.workflow.nodes:
                continue
            na, nb = self.workflow.nodes[a], self.workflow.nodes[b]
            x1, y1 = na.x + NODE_W, na.y + NODE_H // 2
            x2, y2 = nb.x, nb.y + NODE_H // 2
            mx = (x1 + x2) // 2
            self.canvas.create_line(x1, y1, mx, y1, mx, y2, x2, y2,
                                    fill="#4da3ff", width=2, arrow=tk.LAST, tags="wire")
        self.canvas.tag_lower("wire")

    # -------------------------------------------------------- nối dây
    def on_out_clicked(self, node_id):
        self.pending_from = node_id
        node = self.workflow.nodes[node_id]
        self.log(f"Đã chọn cổng Ra của '{node.title}'. Giờ bấm '● Vào' của node đích để nối dây (bấm lại 'Ra ●' để hủy).")

    def on_in_clicked(self, node_id):
        if not self.pending_from:
            self.log("Chưa chọn cổng Ra. Bấm 'Ra ●' của node trước, rồi mới bấm '● Vào' ở đây.")
            return
        if self.pending_from == node_id:
            self.log("Không nối một node với chính nó.")
            self.pending_from = None
            return
        try:
            self.workflow.add_edge(self.pending_from, node_id)
            src = self.workflow.nodes[self.pending_from].title
            dst = self.workflow.nodes[node_id].title
            self.log(f"Đã nối dây: {src} -> {dst}")
        except ValueError as exc:
            self.log(f"Không nối được dây: {exc}")
            messagebox.showwarning("Không nối được dây", str(exc))
        self.pending_from = None
        self.draw_lines()

    def on_delete_node(self, node_id):
        node = self.workflow.nodes[node_id]
        self.canvas.delete(self.windows[node_id])
        self.widgets[node_id].destroy()
        del self.widgets[node_id], self.windows[node_id]
        del self.textboxes[node_id], self.status_labels[node_id]
        self.workflow.remove_node(node_id)
        self.draw_lines()
        self.log(f"Đã xóa node: {node.title}")

    # -------------------------------------------------------- chạy
    def _sync_prompts(self):
        for nid, tb in self.textboxes.items():
            if nid in self.workflow.nodes:
                self.workflow.nodes[nid].prompt = tb.get("1.0", "end").strip()

    def _refresh_status(self, node_id):
        node = self.workflow.nodes[node_id]
        lbl = self.status_labels.get(node_id)
        if lbl:
            lbl.configure(text=f"Trạng thái: {node.status}",
                          text_color=STATUS_COLOR.get(node.status, "gray"))

    def on_run_single(self, node_id):
        """Nút 'Chạy' riêng trên mỗi node — chỉ chạy node đó."""
        self._sync_prompts()
        node = self.workflow.nodes[node_id]
        self.log(f"— Chạy riêng node '{node.title}' ({node.id})...")
        res = run_single(self.workflow, node_id, OUTPUT_DIR)
        self._refresh_status(node_id)
        self.log(("OK: " if res.ok else "LỖI: ") + res.message)
        if res.ok and res.output_path:
            self.log(f"    Output: {res.output_path}")
        if not res.ok:
            messagebox.showerror("Node lỗi", res.message)

    def on_run_all(self):
        """Nút 'Chạy tổng' — chạy toàn bộ workflow theo thứ tự topo,
        dừng ngay khi một node lỗi."""
        self._sync_prompts()
        if not self.workflow.nodes:
            messagebox.showinfo("Chạy tổng", "Canvas đang trống, chưa có node nào.")
            return
        try:
            order = self.workflow.topo_sort()
        except ValueError as exc:
            self.log(f"LỖI chạy tổng: {exc}")
            messagebox.showerror("Chạy tổng", str(exc))
            return
        self.log(f"▶ Chạy tổng: {len(order)} node, thứ tự: {[self.workflow.nodes[i].title for i in order]}")
        results, logs, stopped = run_all(self.workflow, OUTPUT_DIR, stop_on_error=True)
        for line in logs[1:]:
            self.log(line)
        for node_id in self.workflow.nodes:
            self._refresh_status(node_id)
        if stopped:
            bad = next((r for r in results if not r.ok), None)
            messagebox.showerror("Chạy tổng dừng lại",
                                 f"Node lỗi: {bad.message if bad else 'không rõ'}\n"
                                 "Các node sau chưa chạy. Sửa node lỗi rồi bấm 'Chạy tổng' lại, "
                                 "hoặc bấm 'Chạy' riêng từng node sau.")
        else:
            messagebox.showinfo("Chạy tổng xong", f"Hoàn tất {len(results)} node. File ở thư mục outputs/.")

    # --------------------------------------------------- lưu / tải / xóa
    def on_save(self):
        self._sync_prompts()
        path = filedialog.asksaveasfilename(defaultextension=".json",
                                            filetypes=[("Workflow JSON", "*.json")],
                                            initialfile="workflow.json")
        if path:
            self.workflow.save(path)
            self.log(f"Đã lưu workflow: {path}")

    def on_load(self):
        path = filedialog.askopenfilename(filetypes=[("Workflow JSON", "*.json")])
        if not path:
            return
        try:
            wf = Workflow.load(path)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Tải workflow", f"File lỗi: {exc}")
            return
        self._rebuild_from_workflow(wf)
        self.log(f"Đã tải workflow: {path} ({len(wf.nodes)} node, {len(wf.edges)} dây)")

    def load_sample(self, silent=False):
        self._rebuild_from_workflow(create_sample_workflow())
        if not silent:
            self.log("Đã tải workflow mẫu: Prompt -> Tạo ảnh -> Upscale. Bấm 'Chạy tổng' để thử.")

    def _rebuild_from_workflow(self, wf):
        for nid in list(self.widgets):
            self.canvas.delete(self.windows[nid])
            self.widgets[nid].destroy()
        self.widgets.clear(); self.windows.clear()
        self.textboxes.clear(); self.status_labels.clear()
        self.workflow = wf
        self.pending_from = None
        for node in wf.nodes.values():
            self._create_node_widget(node)
        self.draw_lines()

    def on_clear(self):
        if not messagebox.askyesno("Xóa canvas", "Xóa toàn bộ node và dây nối trên canvas?"):
            return
        self._rebuild_from_workflow(Workflow())
        self.log("Đã xóa canvas.")


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    app = WeavyApp()
    app.mainloop()


if __name__ == "__main__":
    main()
