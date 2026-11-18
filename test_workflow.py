"""Test nhỏ cho workflow.py — chạy: python test_workflow.py
Không cần GUI, không cần display.
"""
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from workflow import Workflow, create_sample_workflow, run_all, run_single  # noqa: E402

passed = failed = 0


def check(name, cond, extra=""):
    global passed, failed
    if cond:
        passed += 1
        print(f"PASS: {name}")
    else:
        failed += 1
        print(f"FAIL: {name} {extra}")


def test_topo():
    wf = Workflow()
    a = wf.add_node("prompt", "A")
    b = wf.add_node("image", "B")
    c = wf.add_node("upscale")
    wf.add_edge(a.id, b.id)
    wf.add_edge(b.id, c.id)
    order = wf.topo_sort()
    check("topo: Prompt -> Anh -> Upscale đúng thứ tự",
          order == [a.id, b.id, c.id], str(order))
    # node độc lập vẫn có trong topo
    d = wf.add_node("prompt", "D")
    check("topo: node độc lập vẫn được xếp", d.id in wf.topo_sort())
    # vòng lặp bị chặn khi nối dây
    try:
        wf.add_edge(c.id, a.id)
        check("topo: nối dây tạo vòng lặp bị chặn", False)
    except ValueError:
        check("topo: nối dây tạo vòng lặp bị chặn", True)


def test_run_single():
    with tempfile.TemporaryDirectory() as td:
        wf = Workflow()
        img = wf.add_node("image", "mèo trắng trên bãi biển")
        res = run_single(wf, img.id, td)
        check("chạy riêng: Tạo ảnh OK", res.ok and Path(res.output_path).exists(), res.message)
        check("chạy riêng: file PNG được tạo",
              Path(res.output_path).suffix == ".png" and Path(res.output_path).stat().st_size > 0)
        # chạy riêng node cần đầu vào khi chưa có đầu vào -> lỗi rõ
        up = wf.add_node("upscale")
        res2 = run_single(wf, up.id, td)
        check("chạy riêng: Upscale không có dây nối -> lỗi rõ", not res2.ok and "cần nối" in res2.message,
              res2.message)
        # prompt trống -> lỗi rõ
        empty = wf.add_node("image", "")
        res3 = run_single(wf, empty.id, td)
        check("chạy riêng: Tạo ảnh prompt trống -> lỗi rõ", not res3.ok, res3.message)


def test_run_all_sample():
    with tempfile.TemporaryDirectory() as td:
        wf = create_sample_workflow()
        results, logs, stopped = run_all(wf, td, stop_on_error=True)
        check("chạy tổng: mẫu Prompt->Anh->Upscale xong hết",
              len(results) == 3 and all(r.ok for r in results) and not stopped,
              str([r.message for r in results]))
        pngs = list(Path(td).glob("*.png"))
        check("chạy tổng: có ít nhất 2 file PNG output (ảnh + upscale)", len(pngs) >= 2,
              str([p.name for p in pngs]))
        check("chạy tổng: log ghi thứ tự topo", any("topo" in l for l in logs))


def test_run_all_stops_on_error():
    with tempfile.TemporaryDirectory() as td:
        wf = Workflow()
        ok_node = wf.add_node("prompt", "hello")
        bad = wf.add_node("image", "")  # prompt trống -> lỗi
        after = wf.add_node("image", "sẽ không chạy")
        wf.add_edge(ok_node.id, bad.id)
        wf.add_edge(bad.id, after.id)
        results, logs, stopped = run_all(wf, td, stop_on_error=True)
        check("chạy tổng: dừng ngay khi gặp lỗi (stop_on_error=True)",
              stopped and len(results) == 2 and not results[-1].ok,
              str([r.message for r in results]))
        check("chạy tổng: node sau node lỗi chưa chạy",
              wf.nodes[after.id].status == "Chưa chạy", wf.nodes[after.id].status)
        check("chạy tổng: log báo dừng tại node lỗi", any("DỪNG" in l for l in logs))


def test_video_and_save_load():
    with tempfile.TemporaryDirectory() as td:
        wf = Workflow()
        v = wf.add_node("video", "sóng biển vỗ bờ")
        res = run_single(wf, v.id, td)
        check("chạy riêng: Tạo video mock tạo file mô tả .txt",
              res.ok and Path(res.output_path).suffix == ".txt", res.message)
        p = Path(td) / "wf.json"
        wf.save(p)
        wf2 = Workflow.load(p)
        check("lưu/tải JSON: giữ đủ node và dây nối",
              len(wf2.nodes) == len(wf.nodes) and len(wf2.edges) == len(wf.edges))
        data = json.loads(p.read_text(encoding="utf-8"))
        check("lưu JSON: có trường version/app", data.get("version") == 1)


def test_composite_and_remove_bg():
    with tempfile.TemporaryDirectory() as td:
        wf = Workflow()
        a = wf.add_node("image", "ảnh một")
        b = wf.add_node("image", "ảnh hai")
        comp = wf.add_node("composite")
        wf.add_edge(a.id, comp.id)
        wf.add_edge(b.id, comp.id)
        results, _, stopped = run_all(wf, td)
        check("chạy tổng: Ghép lớp 2 ảnh OK",
              all(r.ok for r in results) and not stopped, str([r.message for r in results]))
        check("ghép lớp: file ghep.png tồn tại",
              any("ghep" in r.output_path for r in results if r.output_path))


if __name__ == "__main__":
    test_topo()
    test_run_single()
    test_run_all_sample()
    test_run_all_stops_on_error()
    test_video_and_save_load()
    test_composite_and_remove_bg()
    print(f"\nKết quả: {passed} PASS, {failed} FAIL")
    sys.exit(1 if failed else 0)
