"""Casos de uso sobre SQLite temporal y fallos que deben revertirse."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from threading import Barrier
from uuid import uuid4

import pytest

from biblioteca.dominio.socio import EstadoSocio
from biblioteca.errores import (
    ErrorPersistencia, ErrorValidacion, RegistroDuplicado, RegistroNoEncontrado,
)
from biblioteca.persistencia.base_datos import conectar, migrar
from biblioteca.repositorios.sede_repository import SedeRepository
from biblioteca.repositorios.socio_repository import SocioRepository
from biblioteca.servicios.sede_service import SedeService
from biblioteca.servicios.socio_service import SocioService


def test_sede_se_conserva_despues_de_reabrir_la_base(sedes, ruta_db):
    sede = sedes.registrar("Centro", "Dirección ficticia 1", "Contacto", "9 a 18")
    sedes.dar_de_baja(sede.id)
    with closing(conectar(ruta_db)) as otra_conexion:
        leida = SedeService(SedeRepository(otra_conexion)).obtener(str(sede.id))
    assert leida.id == sede.id
    assert (leida.nombre, leida.direccion, leida.contacto, leida.horarios, leida.activa) == (
        "Centro", "Dirección ficticia 1", "Contacto", "9 a 18", False
    )


def test_socio_se_conserva_despues_de_reabrir_la_base(socios, ruta_db):
    socio = socios.registrar("00.123.456", "Ana Pérez", "Contacto")
    socios.inhabilitar(socio.id)
    with closing(conectar(ruta_db)) as otra_conexion:
        leido = SocioService(SocioRepository(otra_conexion)).obtener(str(socio.id))
    assert leido.id == socio.id
    assert (leido.documento, leido.nombre_completo, leido.contacto, leido.estado) == (
        "00123456", "Ana Pérez", "Contacto", EstadoSocio.INHABILITADO
    )


def test_nombre_de_sede_duplicado_incluso_si_esta_de_baja(sedes):
    centro = sedes.registrar("Centro", "Calle 1", "Contacto", "9 a 18")
    sedes.dar_de_baja(centro.id)
    with pytest.raises(RegistroDuplicado):
        sedes.registrar("  CENTRO  ", "Calle 2", "Otro contacto", "10 a 16")
    assert len(sedes.listar()) == 1
    assert sedes.activar(centro.id).esta_activa()
    assert sedes.activar(centro.id).id == centro.id


def test_editar_sede_excluye_a_si_misma_y_rechaza_nombre_de_otra(sedes):
    centro = sedes.registrar("Centro", "Calle 1", "Contacto", "9 a 18")
    norte = sedes.registrar("Norte", "Calle 2", "Contacto", "9 a 18")
    editada = sedes.modificar(centro.id, " CENTRO ", "Calle 3", "Nuevo contacto", "10 a 17")
    assert editada.id == centro.id
    assert editada.direccion == "Calle 3"
    with pytest.raises(RegistroDuplicado):
        sedes.modificar(norte.id, "centro", "Dato que debe revertirse", "Contacto", "8 a 20")
    assert sedes.obtener(norte.id).nombre == "Norte"
    assert sedes.obtener(norte.id).direccion == "Calle 2"


def test_actualizar_nombre_actualiza_la_clave_de_busqueda(sedes):
    sede = sedes.registrar("Centro", "Calle 1", "Contacto", "9 a 18")
    sedes.modificar(sede.id, "Norte", "Calle 1", "Contacto", "9 a 18")
    assert [s.id for s in sedes.listar(nombre="norte")] == [sede.id]
    sedes.registrar("Centro", "Calle 2", "Contacto", "9 a 18")
    with pytest.raises(RegistroDuplicado):
        sedes.registrar("norte", "Calle 3", "Contacto", "9 a 18")


def test_dni_duplicado_normalizado_incluso_si_esta_inhabilitado(socios):
    socio = socios.registrar("12.345.678", "Ana Pérez", "Contacto")
    socios.inhabilitar(socio.id)
    with pytest.raises(RegistroDuplicado):
        socios.registrar("12345678", "Otro nombre", "Otro contacto")
    assert len(socios.listar()) == 1
    assert socios.habilitar(socio.id).esta_habilitado()
    assert socios.habilitar(socio.id).id == socio.id


def test_editar_socio_excluye_a_si_mismo_y_rechaza_dni_de_otro(socios):
    ana = socios.registrar("12345678", "Ana Pérez", "Contacto")
    otro = socios.registrar("87654321", "Ana Pérez", "Otro contacto")
    modificado = socios.modificar(ana.id, "12.345.678", "Ana Gómez", "Nuevo contacto")
    assert modificado.id == ana.id
    with pytest.raises(RegistroDuplicado):
        socios.modificar(otro.id, "12-345-678", "Nombre que no debe quedar", "Contacto")
    assert socios.obtener(otro.id).nombre_completo == "Ana Pérez"
    assert socios.obtener(otro.id).documento == "87654321"
    assert socios.buscar_por_documento("12.345.678").id == ana.id
    assert socios.buscar_por_documento("11111111") is None


def test_corregir_dni_preserva_uuid_y_actualiza_busqueda(socios):
    socio = socios.registrar("12345678", "Ana Pérez", "Contacto")
    socios.modificar(socio.id, "87654321", "Ana Pérez", "Contacto")
    assert socios.buscar_por_documento("12345678") is None
    assert socios.buscar_por_documento("87.654.321").id == socio.id


def test_listado_de_sedes_tiene_orden_paginacion_y_filtros(sedes):
    sur = sedes.registrar("Sur", "Calle 1", "Contacto", "9 a 18")
    sedes.registrar("Norte", "Calle 2", "Contacto", "9 a 18")
    sedes.registrar("Centro", "Calle 3", "Contacto", "9 a 18")
    pagina1 = sedes.listar(limite=2)
    pagina2 = sedes.listar(limite=2, desplazamiento=2)
    assert [s.nombre for s in pagina1 + pagina2] == ["Centro", "Norte", "Sur"]
    assert sedes.listar(desplazamiento=20) == []
    sedes.dar_de_baja(sur.id)
    assert [s.nombre for s in sedes.listar(activa=True)] == ["Centro", "Norte"]
    assert [s.id for s in sedes.listar(activa=False, nombre=" SU ")] == [sur.id]


def test_listado_de_socios_desempata_por_id_y_filtra(socios):
    z = socios.registrar("33333333", "Zoe", "Contacto")
    a1 = socios.registrar("11111111", "Ana", "Contacto")
    a2 = socios.registrar("22222222", "Ana", "Contacto")
    paginas = [socios.listar(limite=1, desplazamiento=i)[0] for i in range(3)]
    assert [s.id for s in paginas] == sorted([a1.id, a2.id], key=str) + [z.id]
    socios.inhabilitar(a1.id)
    assert [s.id for s in socios.listar(estado=EstadoSocio.INHABILITADO)] == [a1.id]
    assert [s.id for s in socios.listar(nombre="ANA", estado=EstadoSocio.HABILITADO)] == [a2.id]


@pytest.mark.parametrize("servicio", ["sedes", "socios"])
@pytest.mark.parametrize(
    "parametros",
    [dict(limite=0), dict(limite=101), dict(limite=True), dict(limite=2.5),
     dict(desplazamiento=-1), dict(desplazamiento=False), dict(nombre=123)],
)
def test_consultas_rechazan_paginacion_y_filtros_invalidos(servicio, parametros, request):
    with pytest.raises(ErrorValidacion):
        request.getfixturevalue(servicio).listar(**parametros)


def test_filtros_de_estado_invalidos_no_se_interpretan_silenciosamente(sedes, socios):
    with pytest.raises(ErrorValidacion):
        sedes.listar(activa=1)
    with pytest.raises(ErrorValidacion):
        socios.listar(estado="HABILITADO")


@pytest.mark.parametrize("servicio", ["sedes", "socios"])
def test_ids_inexistentes_o_invalidos_no_crean_registros(servicio, request):
    caso = request.getfixturevalue(servicio)
    with pytest.raises(RegistroNoEncontrado):
        caso.obtener(uuid4())
    with pytest.raises(ErrorValidacion):
        caso.obtener("id-invalido")
    cambiar_estado = caso.activar if servicio == "sedes" else caso.habilitar
    with pytest.raises(RegistroNoEncontrado):
        cambiar_estado(uuid4())
    with pytest.raises(RegistroNoEncontrado):
        if servicio == "sedes":
            caso.modificar(uuid4(), "Centro", "Calle 1", "Contacto", "9 a 18")
        else:
            caso.modificar(uuid4(), "12345678", "Ana Pérez", "Contacto")
    assert caso.listar() == []


def test_fallo_despues_de_escribir_revierte_modificacion_de_sede(
    sedes, sede_repository, ruta_db, monkeypatch
):
    original = sedes.registrar("Centro", "Calle 1", "Contacto", "9 a 18")
    actualizar = sede_repository.actualizar

    def fallar_tras_actualizar(sede):
        actualizar(sede)
        raise ErrorPersistencia("Fallo simulado tras escribir")

    monkeypatch.setattr(sede_repository, "actualizar", fallar_tras_actualizar)
    with pytest.raises(ErrorPersistencia):
        sedes.modificar(original.id, "Norte", "Calle 2", "Otro contacto", "8 a 20")
    with closing(conectar(ruta_db)) as conexion:
        leida = SedeService(SedeRepository(conexion)).obtener(original.id)
        assert (leida.nombre, leida.direccion, leida.contacto, leida.horarios) == (
            "Centro", "Calle 1", "Contacto", "9 a 18"
        )


def test_fallo_despues_de_insertar_revierte_alta_de_socio(
    socios, socio_repository, monkeypatch
):
    agregar = socio_repository.agregar

    def fallar_tras_insertar(socio):
        agregar(socio)
        raise ErrorPersistencia("Fallo simulado tras escribir")

    monkeypatch.setattr(socio_repository, "agregar", fallar_tras_insertar)
    with pytest.raises(ErrorPersistencia):
        socios.registrar("12345678", "Ana Pérez", "Contacto")
    assert socios.listar() == []


def test_datos_con_apostrofes_y_filtros_sql_se_tratan_como_texto(sedes, socios):
    sede = sedes.registrar("Centro", "Calle 'Sur' 1", "Contacto", "9 a 18")
    socio = socios.registrar("12345678", "Ana D'Angelo", "Contacto")
    assert sedes.obtener(sede.id).direccion == "Calle 'Sur' 1"
    assert socios.listar(nombre="d'angelo")[0].id == socio.id
    assert sedes.listar(nombre="' OR 1=1 --") == []
    assert socios.listar(nombre="%") == []
    assert len(socios.listar()) == 1


def test_dos_intentos_concurrentes_no_crean_el_mismo_dni(ruta_db):
    with closing(conectar(ruta_db)) as conexion:
        migrar(conexion)
    barrera = Barrier(2)

    def intentar_alta():
        # Cada hilo abre su propia conexión; no se comparte una conexión SQLite.
        with closing(conectar(ruta_db)) as conexion:
            servicio = SocioService(SocioRepository(conexion))
            barrera.wait(timeout=5)
            try:
                servicio.registrar("12.345.678", "Socio de prueba", "Contacto")
                return "creado"
            except RegistroDuplicado:
                return "duplicado"

    with ThreadPoolExecutor(max_workers=2) as ejecutor:
        resultados = list(ejecutor.map(lambda _: intentar_alta(), range(2)))
    assert sorted(resultados) == ["creado", "duplicado"]
    with closing(conectar(ruta_db)) as conexion:
        assert len(SocioService(SocioRepository(conexion)).listar()) == 1
