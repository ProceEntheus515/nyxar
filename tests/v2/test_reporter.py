"""Reporter automático V2: pendiente de módulo en el repo."""

import pytest


@pytest.mark.v2
def test_reporter_modulo_pendiente():
    pytest.skip("No existe paquete reporter/ en el workspace; añadir tests cuando se implemente.")
