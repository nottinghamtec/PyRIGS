import threading

from z3c.rml import rml2pdf

# z3c.rml resets reportlab's process-wide font registry at the start of every render, so two renders running at once
# in the same process (gunicorn threads) wipe each other's fonts mid-document.
_render_lock = threading.Lock()


def render_rml(rml):
    """Render RML to a PDF buffer, one document at a time per process"""
    with _render_lock:
        return rml2pdf.parseString(rml)
