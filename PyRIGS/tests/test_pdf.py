import threading
import time
from concurrent.futures import ThreadPoolExecutor

from PyRIGS import pdf


def test_renders_do_not_overlap(monkeypatch):
    running = []
    peak = []
    guard = threading.Lock()

    def fake_parse_string(rml):
        with guard:
            running.append(1)
            peak.append(len(running))
        time.sleep(0.02)
        with guard:
            running.pop()
        return rml

    monkeypatch.setattr(pdf.rml2pdf, "parseString", fake_parse_string)

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(pdf.render_rml, [f"doc {i}" for i in range(16)]))

    assert results == [f"doc {i}" for i in range(16)]
    assert max(peak) == 1
