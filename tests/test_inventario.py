"""Inventario explícito, consultas por sede y fallos transaccionales."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from threading import Barrier
from types import SimpleNamespace
from uuid import uuid4

import pytest

from biblioteca.dominio.ejemplar import CondicionFisica, Ejemplar, SituacionOperativa
from biblioteca.errores import ErrorPersistencia, ErrorValidacion, RegistroDuplicado, RegistroNoEncontrado
from biblioteca.persistencia.base_datos import conectar, transaccion
from biblioteca.repositorios.edicion_repository import EdicionRepository
from biblioteca.repositorios.ejemplar_repository import EjemplarRepository
from biblioteca.repositorios.obra_repository import ObraRepository
from biblioteca.repositorios.sede_repository import SedeRepository
from biblioteca.servicios.inventario_service import InventarioService


@pytest.fixture
def contexto(sedes, catalogo):
    centro = sedes.registrar("Centro", "Calle ficticia 1", "Contacto", "9 a 18")
    norte = sedes.registrar("Norte", "Calle ficticia 2", "Contacto", "9 a 18")
    sur = sedes.registrar("Sur", "Calle ficticia 3", "Contacto", "9 a 18")
    a = catalogo.registrar_autor("Autora de prueba")
    b = catalogo.registrar_autor("Coautor de prueba")
    obra = catalogo.registrar_obra("Original de prueba", [a.id, b.id])
    edicion = catalogo.registrar_edicion(obra.id, "Título español")
    segunda = catalogo.registrar_edicion(obra.id, "Otra edición española")
    return SimpleNamespace(centro=centro, norte=norte, sur=sur, obra=obra,
                           edicion=edicion, segunda=segunda)


def test_alta_explicita_y_relectura_preservan_todos_los_datos(inventario, contexto, ruta_db):
    ejemplar = inventario.registrar("  hz-0001 ", contexto.edicion.id, contexto.centro.id)
    assert ejemplar.sede_actual_id == ejemplar.sede_propietaria_id == contexto.centro.id
    assert inventario.buscar_por_codigo("hz-0001").id == ejemplar.id
    inventario.registrar_condicion(ejemplar.id, CondicionFisica.DANIADO)
    inventario.dar_de_baja(ejemplar.id)
    with closing(conectar(ruta_db)) as conexion:
        repo = EjemplarRepository(conexion)
        leido = repo.obtener(ejemplar.id)
        assert (leido.id, leido.codigo_inventario, leido.edicion_id, leido.sede_propietaria_id,
                leido.sede_actual_id, leido.condicion_fisica, leido.situacion_operativa) == (
            ejemplar.id, "HZ-0001", contexto.edicion.id, contexto.centro.id, contexto.centro.id,
            CondicionFisica.DANIADO, SituacionOperativa.BAJA)


def test_varias_copias_no_duplican_obra_ni_edicion(inventario, contexto, catalogo):
    primero = inventario.registrar("HZ-1", contexto.edicion.id, contexto.centro.id)
    segundo = inventario.registrar("HZ-2", contexto.edicion.id, contexto.norte.id)
    assert primero.id != segundo.id
    assert primero.edicion_id == segundo.edicion_id
    assert len(catalogo.listar_obras()) == 1
    assert catalogo.obtener_detalle(contexto.obra.id).cantidad_ediciones == 2
    assert len(inventario.listar(obra_id=contexto.obra.id)) == 2


def test_codigo_es_unico_en_toda_la_red_incluso_en_baja(inventario, contexto):
    primero = inventario.registrar("HZ-0001", contexto.edicion.id, contexto.centro.id)
    inventario.dar_de_baja(primero.id)
    with pytest.raises(RegistroDuplicado):
        inventario.registrar(" hz-0001 ", contexto.segunda.id, contexto.norte.id)
    assert len(inventario.listar()) == 1
    assert inventario.obtener(primero.id).situacion_operativa is SituacionOperativa.BAJA


def test_alta_rechaza_sede_inactiva_y_relaciones_inexistentes(inventario, contexto, sedes):
    sedes.dar_de_baja(contexto.centro.id)
    with pytest.raises(ErrorValidacion, match="sede dada de baja"):
        inventario.registrar("HZ-1", contexto.edicion.id, contexto.centro.id)
    with pytest.raises(RegistroNoEncontrado):
        inventario.registrar("HZ-1", uuid4(), contexto.norte.id)
    with pytest.raises(RegistroNoEncontrado):
        inventario.registrar("HZ-1", contexto.edicion.id, uuid4())
    assert inventario.listar() == []


def test_consulta_incluye_cero_copias_sin_inventarlas(inventario, contexto):
    filas = inventario.consultar_disponibilidad(contexto.obra.id)
    assert [fila.nombre_sede for fila in filas] == ["Centro", "Norte", "Sur"]
    assert all((fila.total_propios, fila.total_ubicados, fila.disponibles) == (0, 0, 0)
               for fila in filas)
    assert inventario.listar() == []


def test_conteos_agregan_ediciones_sin_multiplicar_por_autores(inventario, contexto):
    inventario.registrar("C-1", contexto.edicion.id, contexto.centro.id)
    inventario.registrar("C-2", contexto.edicion.id, contexto.centro.id,
                          condicion_fisica=CondicionFisica.DANIADO)
    inventario.registrar("C-3", contexto.segunda.id, contexto.centro.id)
    baja = inventario.registrar("C-4", contexto.edicion.id, contexto.centro.id)
    inventario.dar_de_baja(baja.id)
    inventario.registrar("N-1", contexto.edicion.id, contexto.norte.id)
    filas = {fila.nombre_sede: fila for fila in inventario.consultar_disponibilidad(contexto.obra.id)}
    centro, norte, sur = filas["Centro"], filas["Norte"], filas["Sur"]
    assert (centro.total_propios, centro.total_ubicados, centro.bajas_ubicadas, centro.disponibles) == (4, 4, 1, 2)
    assert (norte.total_propios, norte.total_ubicados, norte.disponibles) == (1, 1, 1)
    assert (sur.total_propios, sur.total_ubicados, sur.disponibles) == (0, 0, 0)


def test_inactivar_sede_actualiza_disponibilidad_sin_modificar_copias(inventario, contexto, sedes):
    ejemplar = inventario.registrar("HZ-1", contexto.edicion.id, contexto.centro.id)
    assert ejemplar.esta_disponible()
    sedes.dar_de_baja(contexto.centro.id)
    resumen = inventario.consultar_disponibilidad(contexto.obra.id, sede_id=contexto.centro.id)[0]
    assert not resumen.sede_activa
    assert (resumen.total_propios, resumen.total_ubicados, resumen.disponibles) == (1, 1, 0)
    assert inventario.listar(solo_disponibles=True) == []
    assert inventario.obtener(ejemplar.id).esta_disponible()
    # Estado local de copia y disponibilidad ofrecida por la red son diferentes.
    sedes.activar(contexto.centro.id)
    assert inventario.listar(solo_disponibles=True)[0].id == ejemplar.id


def test_otra_ubicacion_no_transfiere_propiedad_ni_libera_para_nuevo_prestamo(
    inventario, contexto, conexion
):
    ejemplar = inventario.registrar("HZ-1", contexto.edicion.id, contexto.centro.id)
    # Simulación de una ubicación temporal: no es una API de traslado ni un remito.
    with transaccion(conexion):
        conexion.execute("UPDATE ejemplar SET sede_actual_id = ? WHERE id = ?",
                         (str(contexto.norte.id), str(ejemplar.id)))
    leido = inventario.obtener(ejemplar.id)
    assert leido.sede_propietaria_id == contexto.centro.id
    assert leido.sede_actual_id == contexto.norte.id
    assert not leido.esta_disponible()
    assert inventario.listar(solo_disponibles=True) == []
    assert inventario.listar(sede_actual_id=contexto.norte.id)[0].id == ejemplar.id
    filas = {fila.nombre_sede: fila for fila in inventario.consultar_disponibilidad(contexto.obra.id)}
    assert (filas["Centro"].total_propios, filas["Centro"].total_ubicados) == (1, 0)
    assert (filas["Norte"].total_propios, filas["Norte"].total_ubicados) == (0, 1)
    assert filas["Norte"].disponibles == 0


def test_ubicacion_nula_no_se_reinventa_como_propietaria(
    contexto, conexion, ejemplar_repository, inventario
):
    ejemplar = Ejemplar("HZ-1", contexto.edicion.id, contexto.centro.id, sede_actual_id=None)
    with transaccion(conexion):
        ejemplar_repository.agregar(ejemplar)
    leido = inventario.obtener(ejemplar.id)
    assert leido.sede_actual_id is None
    assert not leido.esta_disponible()
    resumen = inventario.consultar_disponibilidad(contexto.obra.id, sede_id=contexto.centro.id)[0]
    assert (resumen.total_propios, resumen.total_ubicados, resumen.disponibles) == (1, 0, 0)


def test_cambiar_condicion_y_baja_no_reactivan_material_destruido_o_retirado(inventario, contexto):
    ejemplar = inventario.registrar("HZ-1", contexto.edicion.id, contexto.centro.id)
    inventario.registrar_condicion(ejemplar.id, CondicionFisica.DANIADO)
    assert inventario.listar(solo_disponibles=True) == []
    inventario.registrar_condicion(ejemplar.id, CondicionFisica.APTO)
    assert len(inventario.listar(solo_disponibles=True)) == 1
    inventario.dar_de_baja(ejemplar.id)
    inventario.dar_de_baja(ejemplar.id)
    inventario.registrar_condicion(ejemplar.id, CondicionFisica.APTO)
    assert inventario.listar(solo_disponibles=True) == []
    inventario.registrar_condicion(ejemplar.id, CondicionFisica.DESTRUIDO)
    with pytest.raises(ErrorValidacion):
        inventario.registrar_condicion(ejemplar.id, CondicionFisica.APTO)
    assert inventario.obtener(ejemplar.id).condicion_fisica is CondicionFisica.DESTRUIDO


def test_listados_filtran_antes_de_paginar_y_respetan_edicion_sede_y_condicion(inventario, contexto):
    inventario.registrar("HZ-01", contexto.edicion.id, contexto.centro.id,
                          condicion_fisica=CondicionFisica.DANIADO)
    baja = inventario.registrar("HZ-02", contexto.edicion.id, contexto.centro.id)
    inventario.dar_de_baja(baja.id)
    a = inventario.registrar("HZ-03", contexto.edicion.id, contexto.centro.id)
    b = inventario.registrar("HZ-04", contexto.segunda.id, contexto.norte.id)
    assert inventario.listar(solo_disponibles=True, limite=1)[0].id == a.id
    assert inventario.listar(solo_disponibles=True, limite=1, desplazamiento=1)[0].id == b.id
    assert inventario.listar(desplazamiento=99) == []
    assert len(inventario.listar(edicion_id=contexto.edicion.id)) == 3
    assert len(inventario.listar(obra_id=contexto.obra.id)) == 4
    assert inventario.listar(sede_propietaria_id=contexto.norte.id)[0].id == b.id
    assert inventario.listar(sede_actual_id=contexto.centro.id, solo_disponibles=True)[0].id == a.id
    assert inventario.listar(situacion_operativa=SituacionOperativa.BAJA)[0].id == baja.id
    assert len(inventario.listar(condicion_fisica=CondicionFisica.DANIADO)) == 1


def test_disponibilidad_por_sede_es_paginada_e_identifica_faltantes(inventario, contexto):
    assert inventario.consultar_disponibilidad(contexto.obra.id, limite=1)[0].nombre_sede == "Centro"
    assert inventario.consultar_disponibilidad(contexto.obra.id, limite=1, desplazamiento=1)[0].nombre_sede == "Norte"
    assert inventario.consultar_disponibilidad(contexto.obra.id, desplazamiento=20) == []
    with pytest.raises(RegistroNoEncontrado):
        inventario.consultar_disponibilidad(uuid4())
    with pytest.raises(RegistroNoEncontrado):
        inventario.consultar_disponibilidad(contexto.obra.id, sede_id=uuid4())


@pytest.mark.parametrize("parametros", [dict(limite=0), dict(limite=101), dict(limite=True),
                                        dict(desplazamiento=-1), dict(solo_disponibles=1),
                                        dict(condicion_fisica="APTO"), dict(situacion_operativa="LIBRE"),
                                        dict(sede_actual_id="inválida"), dict(obra_id="inválida")])
def test_filtros_invalidos_no_se_interpretan_silenciosamente(inventario, parametros):
    with pytest.raises(ErrorValidacion):
        inventario.listar(**parametros)


def test_id_codigo_y_cambios_de_inexistentes_no_crean_copias(inventario):
    with pytest.raises(RegistroNoEncontrado):
        inventario.obtener(uuid4())
    with pytest.raises(ErrorValidacion):
        inventario.obtener("inválido")
    with pytest.raises(RegistroNoEncontrado):
        inventario.dar_de_baja(uuid4())
    with pytest.raises(RegistroNoEncontrado):
        inventario.registrar_condicion(uuid4(), CondicionFisica.DANIADO)
    assert inventario.buscar_por_codigo("HZ-0001") is None
    assert inventario.listar() == []


def test_fallo_tras_insertar_revierte_el_alta(inventario, contexto, ejemplar_repository, monkeypatch):
    agregar = ejemplar_repository.agregar

    def fallar(ejemplar):
        agregar(ejemplar)
        raise ErrorPersistencia("Fallo simulado después de insertar")

    monkeypatch.setattr(ejemplar_repository, "agregar", fallar)
    with pytest.raises(ErrorPersistencia):
        inventario.registrar("HZ-1", contexto.edicion.id, contexto.centro.id)
    assert inventario.listar() == []


@pytest.mark.parametrize("accion", ["condicion", "baja"])
def test_fallo_tras_actualizar_revierte_condicion_o_baja(
    inventario, contexto, ejemplar_repository, monkeypatch, accion
):
    original = inventario.registrar("HZ-1", contexto.edicion.id, contexto.centro.id)
    actualizar = ejemplar_repository.actualizar

    def fallar(ejemplar):
        actualizar(ejemplar)
        raise ErrorPersistencia("Fallo simulado después de actualizar")

    monkeypatch.setattr(ejemplar_repository, "actualizar", fallar)
    with pytest.raises(ErrorPersistencia):
        if accion == "baja":
            inventario.dar_de_baja(original.id)
        else:
            inventario.registrar_condicion(original.id, CondicionFisica.DANIADO)
    leido = inventario.obtener(original.id)
    assert leido.condicion_fisica is CondicionFisica.APTO
    assert leido.situacion_operativa is SituacionOperativa.LIBRE


def test_unique_respalda_codigo_y_repositorios_no_confirman_parcialmente(
    inventario, contexto, conexion, ejemplar_repository
):
    with pytest.raises(RegistroDuplicado):
        with transaccion(conexion):
            for codigo in ("HZ-1", "hz-1"):
                ejemplar_repository.agregar(Ejemplar(codigo, contexto.edicion.id, contexto.centro.id,
                                                     sede_actual_id=contexto.centro.id))
    assert inventario.listar() == []


@pytest.mark.parametrize("referencia", ["edicion", "propietaria", "actual"])
def test_claves_foraneas_impiden_referencias_inexistentes(
    contexto, conexion, ejemplar_repository, referencia
):
    ejemplar = Ejemplar("HZ-1", uuid4() if referencia == "edicion" else contexto.edicion.id,
                        uuid4() if referencia == "propietaria" else contexto.centro.id,
                        sede_actual_id=uuid4() if referencia == "actual" else contexto.centro.id)
    with pytest.raises(ErrorPersistencia):
        with transaccion(conexion):
            ejemplar_repository.agregar(ejemplar)
    assert ejemplar_repository.listar() == []


def test_actualizar_no_cambia_identidad_propiedad_ni_ubicacion(
    inventario, contexto, conexion, ejemplar_repository
):
    original = inventario.registrar("HZ-1", contexto.edicion.id, contexto.centro.id)
    alterado = Ejemplar("HZ-1", contexto.edicion.id, contexto.norte.id, id=original.id,
                        sede_actual_id=contexto.norte.id, condicion_fisica=CondicionFisica.DANIADO)
    with pytest.raises(RegistroNoEncontrado):
        with transaccion(conexion):
            ejemplar_repository.actualizar(alterado)
    assert inventario.obtener(original.id).sede_propietaria_id == contexto.centro.id
    assert inventario.obtener(original.id).condicion_fisica is CondicionFisica.APTO


def test_servicio_exige_conexion_compartida(conexion):
    with closing(conectar(":memory:")) as otra:
        with pytest.raises(ErrorValidacion, match="misma conexión"):
            InventarioService(EjemplarRepository(conexion), EdicionRepository(otra),
                               SedeRepository(conexion), ObraRepository(conexion))


def test_dos_altas_concurrentes_con_mismo_codigo_no_crean_duplicados(ruta_db, contexto):
    barrera = Barrier(2)

    def intentar():
        with closing(conectar(ruta_db)) as conexion:
            servicio = InventarioService(EjemplarRepository(conexion), EdicionRepository(conexion),
                                         SedeRepository(conexion), ObraRepository(conexion))
            barrera.wait(timeout=5)
            try:
                servicio.registrar(" hz-0001 ", contexto.edicion.id, contexto.centro.id)
                return "creado"
            except RegistroDuplicado:
                return "duplicado"

    with ThreadPoolExecutor(max_workers=2) as ejecutor:
        resultados = list(ejecutor.map(lambda _: intentar(), range(2)))
    assert sorted(resultados) == ["creado", "duplicado"]
    with closing(conectar(ruta_db)) as conexion:
        assert len(EjemplarRepository(conexion).listar()) == 1


def test_obra_sin_autores_no_admite_altas_ni_ofrece_copias(inventario, contexto, conexion):
    original = inventario.registrar("HZ-1", contexto.edicion.id, contexto.centro.id)
    with transaccion(conexion):
        conexion.execute("DELETE FROM obra_autor WHERE obra_id = ?", (str(contexto.obra.id),))
    with pytest.raises(ErrorValidacion, match="autores identificados"):
        inventario.registrar("HZ-2", contexto.edicion.id, contexto.centro.id)
    assert inventario.obtener(original.id).id == original.id
    assert inventario.listar(solo_disponibles=True) == []
    assert sum(f.disponibles for f in inventario.consultar_disponibilidad(contexto.obra.id)) == 0


@pytest.mark.parametrize("parametros", [dict(limite=0), dict(limite=101), dict(limite=True),
                                        dict(desplazamiento=-1), dict(sede_id="inválida")])
def test_resumen_de_disponibilidad_rechaza_parametros_invalidos(inventario, contexto, parametros):
    with pytest.raises(ErrorValidacion):
        inventario.consultar_disponibilidad(contexto.obra.id, **parametros)
