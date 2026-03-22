"""Smoke: módulo de métricas y app FastAPI importables."""

from prometheus_client import generate_latest


def test_metrics_definitions_register():
    import observability.metrics as m  # noqa: F401

    m.EVENTOS_EN_COLA.labels(stream="events_raw").set(0)
    out = generate_latest()
    assert b"NYXAR_eventos_cola" in out


def test_observability_app_import():
    from observability.main import app

    assert app.title == "NYXAR Observability"
