"""Invariantes y comportamiento de entidades, sin SQLite."""

from uuid import UUID

import pytest

from biblioteca.dominio.sede import Sede
from biblioteca.dominio.socio import EstadoSocio, Socio
from biblioteca.errores import ErrorValidacion


def test_sede_normaliza_datos_y_conserva_identidad_al_cambiar_estado():
    sede = Sede("  Centro  ", "Av.  Siempre   Viva 1", "  0351  1234567 ", "Lunes\na viernes")
    identidad = sede.id
    assert isinstance(identidad, UUID)
    assert sede.nombre == "Centro"
    assert sede.direccion == "Av. Siempre Viva 1"
    assert sede.contacto == "0351 1234567"
    assert sede.horarios == "Lunes a viernes"
    assert sede.esta_activa()
    sede.dar_de_baja()
    sede.dar_de_baja()
    assert not sede.esta_activa()
    sede.activar()
    sede.activar()
    assert sede.id == identidad
    assert sede.esta_activa()


@pytest.mark.parametrize("campo", ["nombre", "direccion", "contacto", "horarios"])
@pytest.mark.parametrize("valor", [" \t\n", None, 123])
def test_sede_rechaza_datos_obligatorios_invalidos(campo, valor):
    datos = dict(nombre="Centro", direccion="Calle 1", contacto="Teléfono", horarios="9 a 18")
    datos[campo] = valor
    with pytest.raises(ErrorValidacion):
        Sede(**datos)


def test_actualizacion_invalida_no_modifica_parcialmente_una_sede():
    sede = Sede("Centro", "Calle 1", "Teléfono", "9 a 18")
    with pytest.raises(ErrorValidacion):
        sede.actualizar_datos("Norte", "Calle 2", "Otro contacto", " ")
    assert (sede.nombre, sede.direccion, sede.contacto, sede.horarios) == (
        "Centro", "Calle 1", "Teléfono", "9 a 18"
    )


@pytest.mark.parametrize(
    ("entrada", "esperado"),
    [("12.345.678", "12345678"), (" 12-345-678 ", "12345678"),
     ("00.123.456", "00123456"), ("12345678", "12345678")],
)
def test_socio_normaliza_dni_sin_perder_ceros(entrada, esperado):
    socio = Socio(entrada, "  Ana   Pérez ", " contacto ")
    assert socio.documento == esperado
    assert socio.nombre_completo == "Ana Pérez"
    assert socio.contacto == "contacto"
    assert socio.esta_habilitado()


@pytest.mark.parametrize(
    "documento",
    ["", " ", "---", "A1234567", "12/345/678", "+12345678", "-12345678",
     ".12345678", "12345678-",
     "1e7", "١٢٣٤", "１２３４", 12345678, None, True],
)
def test_socio_rechaza_documentos_que_no_representan_un_dni(documento):
    with pytest.raises(ErrorValidacion):
        Socio(documento, "Ana Pérez", "Teléfono")


@pytest.mark.parametrize("campo", ["nombre_completo", "contacto"])
def test_socio_rechaza_campos_obligatorios_vacios(campo):
    datos = dict(documento="12345678", nombre_completo="Ana Pérez", contacto="Teléfono")
    datos[campo] = " "
    with pytest.raises(ErrorValidacion):
        Socio(**datos)


def test_actualizacion_invalida_no_modifica_parcialmente_un_socio():
    socio = Socio("12345678", "Ana Pérez", "Contacto")
    with pytest.raises(ErrorValidacion):
        socio.actualizar_datos("87654321", "Otro nombre", " ")
    assert (socio.documento, socio.nombre_completo, socio.contacto) == (
        "12345678", "Ana Pérez", "Contacto"
    )


def test_inhabilitar_y_habilitar_son_idempotentes_y_conservan_identidad():
    socio = Socio("12345678", "Ana Pérez", "Contacto")
    identidad = socio.id
    socio.inhabilitar()
    socio.inhabilitar()
    assert socio.estado is EstadoSocio.INHABILITADO
    assert not socio.esta_habilitado()
    socio.habilitar()
    socio.habilitar()
    assert socio.esta_habilitado()
    assert socio.id == identidad
    socio.actualizar_datos("87654321", "Ana Gómez", "Otro contacto")
    assert socio.id == identidad


def test_identidad_y_estado_no_se_modifican_por_asignacion_publica():
    sede = Sede("Centro", "Calle 1", "Contacto", "9 a 18")
    socio = Socio("12345678", "Ana Pérez", "Contacto")
    for entidad, campo, valor in [(sede, "id", UUID(int=1)), (sede, "activa", False),
                                  (socio, "documento", "87654321"),
                                  (socio, "estado", EstadoSocio.INHABILITADO)]:
        with pytest.raises(AttributeError):
            setattr(entidad, campo, valor)


def test_no_se_aceptan_estados_ni_identidades_invalidos():
    with pytest.raises(ErrorValidacion):
        Sede("Centro", "Calle 1", "Contacto", "9 a 18", activa=1)
    with pytest.raises(ErrorValidacion):
        Socio("12345678", "Ana Pérez", "Contacto", estado="HABILITADO")
    with pytest.raises(ErrorValidacion):
        Socio("12345678", "Ana Pérez", "Contacto", id="no-es-uuid")
