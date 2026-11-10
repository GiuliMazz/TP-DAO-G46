"""Comportamiento propio del ejemplar, sin base de datos ni servicios."""

from uuid import uuid4

import pytest

from biblioteca.dominio.ejemplar import CondicionFisica, Ejemplar, SituacionOperativa
from biblioteca.errores import ErrorValidacion


def crear_ejemplar(**datos):
    propietaria = uuid4()
    return Ejemplar("HZ-0001", uuid4(), propietaria,
                     sede_actual_id=propietaria, **datos)


def test_codigo_normalizado_conserva_ceros_y_datos_estables():
    sede, edicion = uuid4(), uuid4()
    ejemplar = Ejemplar("  hz-00001  ", edicion, sede, sede_actual_id=sede)
    identidad = ejemplar.id
    assert ejemplar.codigo_inventario == "HZ-00001"
    ejemplar.registrar_condicion(CondicionFisica.DANIADO)
    assert not ejemplar.esta_disponible()
    ejemplar.registrar_condicion(CondicionFisica.APTO)
    assert ejemplar.esta_disponible()
    ejemplar.dar_de_baja()
    ejemplar.dar_de_baja()
    ejemplar.registrar_condicion(CondicionFisica.APTO)
    assert ejemplar.id == identidad
    assert ejemplar.edicion_id == edicion
    assert ejemplar.sede_propietaria_id == ejemplar.sede_actual_id == sede
    assert ejemplar.situacion_operativa is SituacionOperativa.BAJA
    assert not ejemplar.esta_disponible()


@pytest.mark.parametrize("codigo", ["", " ", "HZ 001", "HZ\n001", "HZ\t001", "HZ\x00001", 123, None])
def test_codigo_obligatorio_sin_espacios_internos_o_controles(codigo):
    with pytest.raises(ErrorValidacion):
        Ejemplar(codigo, uuid4(), uuid4(), sede_actual_id=None)


@pytest.mark.parametrize(("condicion", "situacion", "ubicacion", "disponible"), [
    (CondicionFisica.APTO, SituacionOperativa.LIBRE, "propietaria", True),
    (CondicionFisica.DANIADO, SituacionOperativa.LIBRE, "propietaria", False),
    (CondicionFisica.DESTRUIDO, SituacionOperativa.LIBRE, "propietaria", False),
    (CondicionFisica.APTO, SituacionOperativa.BAJA, "propietaria", False),
    (CondicionFisica.APTO, SituacionOperativa.LIBRE, "otra", False),
    (CondicionFisica.APTO, SituacionOperativa.LIBRE, None, False),
])
def test_disponibilidad_propia_no_se_deduce_solo_de_estar_libre(condicion, situacion, ubicacion, disponible):
    propietaria = uuid4()
    actual = propietaria if ubicacion == "propietaria" else uuid4() if ubicacion == "otra" else None
    ejemplar = Ejemplar("HZ-1", uuid4(), propietaria, sede_actual_id=actual,
                        condicion_fisica=condicion, situacion_operativa=situacion)
    assert ejemplar.esta_disponible() is disponible


def test_destruccion_no_se_revierte_mediante_cambio_ordinario():
    ejemplar = crear_ejemplar()
    ejemplar.registrar_condicion(CondicionFisica.DESTRUIDO)
    ejemplar.registrar_condicion(CondicionFisica.DESTRUIDO)
    for condicion in (CondicionFisica.APTO, CondicionFisica.DANIADO, "APTO", None):
        with pytest.raises(ErrorValidacion):
            ejemplar.registrar_condicion(condicion)
        assert ejemplar.condicion_fisica is CondicionFisica.DESTRUIDO
        assert not ejemplar.esta_disponible()


def test_identidad_edicion_propietaria_y_ubicacion_son_solo_lectura():
    ejemplar = crear_ejemplar()
    for campo in ("id", "codigo_inventario", "edicion_id", "sede_propietaria_id", "sede_actual_id",
                  "condicion_fisica", "situacion_operativa"):
        with pytest.raises(AttributeError):
            setattr(ejemplar, campo, "otro valor")


@pytest.mark.parametrize("datos", [dict(condicion_fisica="APTO"), dict(situacion_operativa="LIBRE"),
                                    dict(id="inválido")])
def test_estados_e_identidades_invalidos_no_se_interpretan_silenciosamente(datos):
    with pytest.raises(ErrorValidacion):
        crear_ejemplar(**datos)
