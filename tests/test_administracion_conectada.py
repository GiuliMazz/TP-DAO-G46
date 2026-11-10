"""Administración real: guardados, paginación, concurrencia y errores visuales."""

import asyncio
import json
import sqlite3
import threading
from types import SimpleNamespace

import pytest

from biblioteca.administracion_local import AdministracionLocal
from biblioteca.dominio.socio import EstadoSocio
from biblioteca.dominio.ejemplar import CondicionFisica, SituacionOperativa
from biblioteca.errores import ErrorPersistencia, ErrorValidacion, RegistroDuplicado
from biblioteca.interfaz.escritor_asincrono import EscritorAsincrono, EscritorOcupado
from biblioteca.interfaz.lector_asincrono import LectorAsincrono
from biblioteca.interfaz.socios_local_view import SociosLocalView
from biblioteca.interfaz.sedes_local_view import SedesLocalView
from biblioteca.interfaz.aplicacion import AplicacionHorizonte
from biblioteca.interfaz.inventario_local_view import InventarioLocalView
from biblioteca.consultas_locales import ConsultasCatalogoLocal
from herramientas.preparar_socios_demo import preparar_socios
from test_catalogo_conectado import Pagina as PaginaAplicacion, LectorControlado


class Pagina:
    def __init__(self):
        self.dialogo = None
        self.tareas = []
        self.actualizaciones = 0

    def update(self):
        self.actualizaciones += 1

    def show_dialog(self, dialogo):
        self.dialogo = dialogo

    def pop_dialog(self):
        self.dialogo = None

    def run_task(self, funcion, *args):
        tarea = asyncio.create_task(funcion(*args))
        self.tareas.append(tarea)
        return tarea


@pytest.fixture
def administracion(ruta_db, conexion):
    ruta_db.with_suffix(".db.tipo.json").write_text(json.dumps({"version": 1, "tipo": "DEMOSTRACION"}))
    return AdministracionLocal(ruta_db)


def test_socios_guardados_reabren_sin_cambios_parciales(administracion):
    a = administracion
    socio = a.ejecutar("socios", "registrar", "12.345.678", "Ana Torres", "ana@example.test")
    otro = a.ejecutar("socios", "registrar", "99", "Otro Socio", "Contacto")
    with pytest.raises(RegistroDuplicado):
        a.ejecutar("socios", "modificar", socio.id, "99", "Cambio inválido", "otro")
    with pytest.raises(ErrorValidacion):
        a.ejecutar("socios", "modificar", socio.id, "123", "", "otro")
    a.ejecutar("socios", "inhabilitar", socio.id)
    guardado = a.listar("socios", texto="12.345.678")[0]
    assert guardado.documento == "12345678" and guardado.nombre_completo == "Ana Torres"
    assert guardado.estado == EstadoSocio.INHABILITADO
    with pytest.raises(RegistroDuplicado):
        a.ejecutar("socios", "registrar", "12345678", "Duplicado", "Contacto")
    a.ejecutar("socios", "habilitar", socio.id)
    assert a.listar("socios", texto="Ana@EXAMPLE")[0].esta_habilitado()
    assert a.listar("socios", texto="Otro")[0].id == otro.id


def test_busqueda_socios_or_antes_de_paginar(administracion):
    a = administracion
    for i in range(55):
        a.ejecutar("socios", "registrar", str(i), f"Persona {i:02}", f"correo{i}@example.test")
    assert len(a.listar("socios", texto="Persona", limite=51)) == 51
    assert len(a.listar("socios", texto="Persona", desplazamiento=50)) == 5
    assert a.listar("socios", texto="54", limite=1)[0].documento == "54"
    assert a.listar("socios", texto="correo54", limite=1)[0].documento == "54"
    assert a.listar("socios", texto="Persona 54", limite=1)[0].documento == "54"
    a.ejecutar("socios", "inhabilitar", a.listar("socios", texto="correo54")[0].id)
    assert not a.listar("socios", texto="54", estado=EstadoSocio.HABILITADO)


@pytest.mark.parametrize("tipo", ["RENDIMIENTO", "DESCONOCIDA", None])
def test_bases_sin_administracion_no_se_escriben(administracion, tipo):
    ruta = administracion.base
    ruta.with_suffix(".db.tipo.json").write_text(json.dumps({"version": 1, "tipo": tipo}))
    antes = ruta.read_bytes()
    with pytest.raises(ErrorPersistencia):
        administracion.ejecutar("socios", "registrar", "1", "Nombre", "Contacto")
    assert ruta.read_bytes() == antes


def test_escritura_no_crea_ni_migra_base(tmp_path):
    ruta = tmp_path / "ausente.db"
    ruta.with_suffix(".db.tipo.json").write_text('{"version":1,"tipo":"OPERATIVA"}')
    a = AdministracionLocal(ruta)
    with pytest.raises(ErrorPersistencia):
        a.ejecutar("socios", "registrar", "1", "Nombre", "Contacto")
    assert not ruta.exists()
    with sqlite3.connect(ruta) as c:
        c.execute("PRAGMA user_version=1")
    antes = ruta.read_bytes()
    with pytest.raises(ErrorPersistencia):
        a.ejecutar("socios", "registrar", "1", "Nombre", "Contacto")
    assert ruta.read_bytes() == antes


def test_escritor_cancelado_conserva_comando_y_rechaza_otra_escritura():
    async def recorrido():
        escritor = EscritorAsincrono()
        inicio, liberar = threading.Event(), threading.Event()
        operaciones = []
        def comando():
            inicio.set()
            assert liberar.wait(3)
            operaciones.append("confirmado")
        tarea = asyncio.create_task(escritor.ejecutar(comando))
        try:
            while not inicio.is_set():
                await asyncio.sleep(0.001)
            tarea.cancel()
            with pytest.raises(asyncio.CancelledError):
                await tarea
            with pytest.raises(EscritorOcupado):
                await escritor.ejecutar(lambda: operaciones.append("intruso"))
            escritor.cerrar()
            esperando = asyncio.create_task(escritor.esperar_cierre())
            await asyncio.sleep(0)
            assert not esperando.done()
            liberar.set()
            await esperando
            assert operaciones == ["confirmado"]
        finally:
            liberar.set()
            escritor.cerrar()
            await escritor.esperar_cierre()
    asyncio.run(recorrido())


def test_formulario_error_doble_clic_y_refresco_fallido(administracion):
    async def recorrido():
        pagina, lector, escritor = Pagina(), LectorAsincrono(), EscritorAsincrono()
        vista = SociosLocalView(pagina, administracion, lector, escritor)
        vista.activa = True
        try:
            vista.abrir_formulario()
            f = vista.formulario
            f.campos["documento"].value = "DNI inválido"
            f.campos["nombre_completo"].value = "Socio de prueba"
            f.campos["contacto"].value = "prueba@example.test"
            await f.enviar()
            assert f.abierto and not f.guardar.disabled and "DNI" in f.error.value
            assert f.campos["nombre_completo"].value == "Socio de prueba"
            f.campos["documento"].value = "99887766"
            original = administracion.listar
            administracion.listar = lambda *a, **k: (_ for _ in ()).throw(ErrorPersistencia("Fallo al releer"))
            await asyncio.gather(f.enviar(), f.enviar())
            assert not f.abierto and pagina.dialogo is None
            assert vista.aviso.value == "Cambios guardados."
            assert vista.resumen.value == "No se pudo leer el listado"
            assert len(original("socios")) == 1
            administracion.listar = original
            await vista.cargar()
            assert len(vista.registros) == 1
        finally:
            lector.cerrar()
            escritor.cerrar()
            await lector.esperar_cierre()
            await escritor.esperar_cierre()
    asyncio.run(recorrido())


def test_sedes_guardan_horarios_baja_y_unicidad(administracion):
    a = administracion
    sede = a.ejecutar("sedes", "registrar", "Centro", "Dirección", "Contacto", "9 a 18")
    a.ejecutar("sedes", "modificar", sede.id, "Central", "Otra dirección", "Otro contacto", "10 a 19")
    a.ejecutar("sedes", "dar_de_baja", sede.id)
    with pytest.raises(RegistroDuplicado):
        a.ejecutar("sedes", "registrar", " CENTRAL ", "Dirección", "Contacto", "9 a 18")
    assert not a.listar("sedes", activa=True)
    guardada = a.listar("sedes", activa=False)[0]
    assert guardada.id == sede.id and guardada.horarios == "10 a 19"
    a.ejecutar("sedes", "activar", sede.id)
    assert a.listar("sedes", activa=True)[0].id == sede.id


def test_configuracion_conserva_uuid_y_catalogo_independiente(administracion):
    async def recorrido():
        a = administracion
        centro = a.ejecutar("sedes", "registrar", "Centro", "Dirección", "Contacto", "9 a 18")
        norte = a.ejecutar("sedes", "registrar", "Norte", "Dirección", "Contacto", "9 a 18")
        app = AplicacionHorizonte(PaginaAplicacion(), consultas=ConsultasCatalogoLocal(a.base))
        try:
            await app._inicializar()
            app.sede = str(centro.id)
            app.catalogo.sede.value = str(norte.id)
            a.ejecutar("sedes", "modificar", centro.id, "Central", "Dirección", "Contacto", "9 a 18")
            await app._al_guardar("sedes")
            assert app.sede == str(centro.id)
            assert app.selector_sede.options[0].text == "Central"
            assert app.catalogo.sede.value == str(norte.id)
            a.ejecutar("sedes", "dar_de_baja", centro.id)
            await app._al_guardar("sedes")
            assert app.sede == str(norte.id)
            assert app.catalogo.sede.value == str(norte.id)
            assert {"Socios", "Sedes", "Ejemplares"} <= app.vistas.keys()
        finally:
            await app._desconectar()
            await app.lector.esperar_cierre()
            await app.escritor.esperar_cierre()
    asyncio.run(recorrido())


def test_formulario_sede_usa_servicio_y_persiste(administracion):
    async def recorrido():
        page, lector, escritor = Pagina(), LectorAsincrono(), EscritorAsincrono()
        vista = SedesLocalView(page, administracion, lector, escritor)
        vista.activa = True
        try:
            vista.abrir_formulario()
            f = vista.formulario
            for nombre, valor in {"nombre": "Sur", "direccion": "Dirección ficticia",
                                  "contacto": "sur@example.test", "horarios": "9 a 18"}.items():
                f.campos[nombre].value = valor
            await f.enviar()
            assert vista.registros[0].nombre == "Sur" and page.dialogo is None
        finally:
            lector.cerrar()
            escritor.cerrar()
            await lector.esperar_cierre()
            await escritor.esperar_cierre()
    asyncio.run(recorrido())


def test_inventario_alta_explicita_y_rechazo_sede_inactiva(administracion, catalogo):
    a = administracion
    autor = catalogo.registrar_autor("Autor de prueba")
    obra = catalogo.registrar_obra("Obra original", [autor.id])
    edicion = catalogo.registrar_edicion(obra.id, "Edición española")
    sede = a.ejecutar("sedes", "registrar", "Centro", "Dirección", "Contacto", "9 a 18")
    copia = a.ejecutar("inventario", "registrar", "test-1", str(edicion.id), str(sede.id))
    assert copia.sede_actual_id == copia.sede_propietaria_id == sede.id
    assert copia.codigo_inventario == "TEST-1"
    assert a.listar("inventario", obra_id=obra.id)[0].id == copia.id
    assert a.consultar_pagina(texto="española", sede_id=sede.id, disponibles=True).total == 1
    with pytest.raises(RegistroDuplicado):
        a.ejecutar("inventario", "registrar", "TEST-1", edicion.id, sede.id)
    a.ejecutar("sedes", "dar_de_baja", sede.id)
    with pytest.raises(ErrorValidacion, match="baja"):
        a.ejecutar("inventario", "registrar", "TEST-2", edicion.id, sede.id)
    assert len(a.listar("inventario", obra_id=obra.id)) == 1
    assert a.consultar_pagina(texto="española", sede_id=sede.id, disponibles=True).total == 0


def test_formulario_inventario_muestra_edicion_y_sedes_activas(administracion, catalogo):
    async def recorrido():
        a = administracion
        autor = catalogo.registrar_autor("Autora")
        obra = catalogo.registrar_obra("Original", [autor.id])
        edicion = catalogo.registrar_edicion(obra.id, "Edición española")
        centro = a.ejecutar("sedes", "registrar", "Centro", "Dirección", "Contacto", "9 a 18")
        sur = a.ejecutar("sedes", "registrar", "Sur", "Dirección", "Contacto", "9 a 18")
        a.ejecutar("sedes", "dar_de_baja", sur.id)
        page, lector, escritor = Pagina(), LectorAsincrono(), EscritorAsincrono()
        vista = InventarioLocalView(page, a, lector, escritor)
        vista.configurar(obra.id, "Título español", [edicion], a.listar("sedes"))
        vista.activa = True
        try:
            vista.abrir_formulario()
            f = vista.formulario
            assert f.campos["sede_id"].value == str(centro.id)
            assert len(f.campos["sede_id"].options) == 1
            assert f.campos["edicion_id"].value == str(edicion.id)
            f.campos["codigo_inventario"].value = "TEST-99"
            await f.enviar()
            assert len(vista.registros) == 1 and vista.registros[0].codigo_inventario == "TEST-99"
        finally:
            lector.cerrar()
            escritor.cerrar()
            await lector.esperar_cierre()
            await escritor.esperar_cierre()
    asyncio.run(recorrido())


def test_semilla_explicita_repetible_conserva_cambios_humanos(administracion):
    a = administracion
    assert a.listar("socios") == []
    assert preparar_socios(a.base)["creados"] == 8
    socio = a.listar("socios", texto="90000001")[0]
    a.ejecutar("socios", "modificar", socio.id, "11", "Editado manualmente", "otro@example.test")
    a.ejecutar("socios", "inhabilitar", socio.id)
    assert preparar_socios(a.base)["creados"] == 0
    guardado = a.listar("socios", texto="11")[0]
    assert guardado.id == socio.id and guardado.nombre_completo == "Editado manualmente"
    assert not guardado.esta_habilitado()
    assert len(a.listar("socios")) == 8


@pytest.mark.parametrize("tipo", ["OPERATIVA", "RENDIMIENTO"])
def test_semilla_rechaza_otras_bases_sin_escribir(administracion, tipo):
    a = administracion
    a.base.with_suffix(".db.tipo.json").write_text(json.dumps({"version": 1, "tipo": tipo}))
    antes = a.base.read_bytes()
    with pytest.raises(ErrorValidacion):
        preparar_socios(a.base)
    assert a.base.read_bytes() == antes


def test_semilla_no_adopta_dni_preexistente(administracion):
    administracion.ejecutar("socios", "registrar", "90000004", "Socio anterior", "Contacto")
    with pytest.raises(ErrorValidacion, match="conflicto"):
        preparar_socios(administracion.base)
    assert len(administracion.listar("socios")) == 1


def test_listado_descarta_respuestas_obsoletas_y_al_salir(administracion):
    async def recorrido():
        a = administracion
        primero = a.ejecutar("socios", "registrar", "1", "Ana", "Contacto")
        segundo = a.ejecutar("socios", "registrar", "2", "Bruno", "Contacto")
        page, lector = Pagina(), LectorControlado()
        vista = SociosLocalView(page, a, lector, None)
        vista.activa = True
        vieja = asyncio.create_task(vista.cargar())
        await asyncio.sleep(0)
        vista.busqueda.value = "Bruno"
        nueva = asyncio.create_task(vista.cargar(reiniciar=True))
        await asyncio.sleep(0)
        assert lector.peticiones[1][3]["texto"] == "Bruno"
        lector.peticiones[1][0].set_result([segundo])
        await nueva
        lector.peticiones[0][0].set_result([primero])
        await vieja
        assert [s.id for s in vista.registros] == [segundo.id]
        ultima = asyncio.create_task(vista.cargar())
        await asyncio.sleep(0)
        vista.activar(False)
        actualizaciones = page.actualizaciones
        lector.peticiones[2][0].set_result([primero])
        await ultima
        assert page.actualizaciones == actualizaciones
        assert [s.id for s in vista.registros] == [segundo.id]
    asyncio.run(recorrido())


def test_reconexion_espera_guardado_y_descarta_formulario_anterior(administracion):
    async def recorrido():
        app = AplicacionHorizonte(PaginaAplicacion(), consultas=ConsultasCatalogoLocal(administracion.base))
        inicio, liberar = threading.Event(), threading.Event()
        await app._inicializar()
        app.socios.abrir_formulario()
        formulario = app.socios.formulario
        anterior = app.escritor
        def comando():
            inicio.set()
            assert liberar.wait(3)
            return administracion.ejecutar("socios", "registrar", "123", "Socio persistente", "Contacto")
        guardado = asyncio.create_task(anterior.ejecutar(comando))
        try:
            while not inicio.is_set():
                await asyncio.sleep(0.001)
            await app._desconectar()
            reconexion = asyncio.create_task(app._reconectar())
            await asyncio.sleep(0)
            assert app._cerrada and app.escritor is anterior and not reconexion.done()
            liberar.set()
            await guardado
            await reconexion
            assert not app._cerrada and app.escritor is not anterior
            assert app.socios.formulario is None and not formulario.dialogo.open
            assert administracion.listar("socios")[0].nombre_completo == "Socio persistente"
        finally:
            liberar.set()
            await guardado
            await app._desconectar()
            await app.lector.esperar_cierre()
            await app.escritor.esperar_cierre()
    asyncio.run(recorrido())


def test_rendimiento_no_habilita_formularios(administracion):
    async def recorrido():
        a = administracion
        a.base.with_suffix(".db.tipo.json").write_text('{"version":1,"tipo":"RENDIMIENTO"}')
        app = AplicacionHorizonte(PaginaAplicacion(), consultas=ConsultasCatalogoLocal(a.base))
        try:
            await app._inicializar()
            assert app.socios is None and app.catalogo.al_inventario is None
            assert "Socios" not in app.vistas and "Sedes" not in app.vistas
        finally:
            await app._desconectar()
            await app.lector.esperar_cierre()
            await app.escritor.esperar_cierre()
    asyncio.run(recorrido())


def test_mantenimiento_inventario_desde_formulario_y_catalogo(administracion, catalogo):
    async def recorrido():
        a = administracion
        autor = catalogo.registrar_autor("Autora de mantenimiento")
        obra = catalogo.registrar_obra("Original de mantenimiento", [autor.id])
        edicion = catalogo.registrar_edicion(obra.id, "Edición de mantenimiento")
        sede = a.ejecutar("sedes", "registrar", "Centro", "Dirección", "Contacto", "9 a 18")
        copia = a.ejecutar("inventario", "registrar", "MANT-01", edicion.id, sede.id)
        app = AplicacionHorizonte(PaginaAplicacion(), consultas=ConsultasCatalogoLocal(a.base))
        try:
            await app._inicializar()
            vista = app.inventario
            vista.configurar(obra.id, edicion.titulo, [edicion], [sede])
            vista.activa = True
            for condicion, disponibles in ((CondicionFisica.DANIADO, 0), (CondicionFisica.APTO, 1)):
                vista.abrir_condicion(a.listar("inventario")[0])
                vista.formulario.campos["condicion"].value = condicion.value
                await asyncio.gather(vista.formulario.enviar(), vista.formulario.enviar())
                assert vista.registros[0].condicion_fisica is condicion
                app.catalogo._activa = True
                await app.catalogo.cargar()
                assert app.catalogo._pagina_resultado.obras[0].disponibles == disponibles
                ficha = a.ficha(obra.id)
                assert ficha.existencias[0].disponibles == disponibles
            # Cancelar el diálogo no ejecuta la baja.
            vista.confirmar("Baja", "Confirmar baja", "dar_de_baja", copia.id)
            vista.formulario.cerrar()
            assert a.listar("inventario")[0].situacion_operativa is SituacionOperativa.LIBRE
            vista.confirmar("Baja", "Confirmar baja", "dar_de_baja", copia.id)
            await vista.formulario.enviar()
            assert vista.registros[0].situacion_operativa is SituacionOperativa.BAJA
            vista.abrir_condicion(vista.registros[0])
            vista.formulario.campos["condicion"].value = CondicionFisica.APTO.value
            await vista.formulario.enviar()
            await app.catalogo.cargar()
            assert app.catalogo._pagina_resultado.obras[0].disponibles == 0
            leido = a.listar("inventario")[0]
            assert leido.id == copia.id and leido.codigo_inventario == copia.codigo_inventario
            assert leido.sede_propietaria_id == leido.sede_actual_id == sede.id
            assert a.ficha(obra.id).existencias[0].total_propios == 1
            assert catalogo.obtener_edicion(edicion.id).titulo == "Edición de mantenimiento"
        finally:
            await app._desconectar()
            await app.lector.esperar_cierre()
            await app.escritor.esperar_cierre()
    asyncio.run(recorrido())


def test_condicion_destruida_no_se_recupera_con_formulario_obsoleto(administracion, catalogo):
    async def recorrido():
        a = administracion
        autor = catalogo.registrar_autor("Autora")
        obra = catalogo.registrar_obra("Original", [autor.id])
        edicion = catalogo.registrar_edicion(obra.id, "Español")
        sede = a.ejecutar("sedes", "registrar", "Centro", "Dirección", "Contacto", "9 a 18")
        copia = a.ejecutar("inventario", "registrar", "MANT-02", edicion.id, sede.id)
        page, lector, escritor = Pagina(), LectorAsincrono(), EscritorAsincrono()
        vista = InventarioLocalView(page, a, lector, escritor)
        vista.configurar(obra.id, "Español", [edicion], [sede])
        vista.activa = True
        try:
            vista.abrir_condicion(copia)
            a.ejecutar("inventario", "registrar_condicion", copia.id, CondicionFisica.DESTRUIDO)
            await vista.formulario.enviar()
            assert vista.formulario.abierto and "destruido" in vista.formulario.error.value
            assert not vista.formulario.guardar.disabled
            assert a.listar("inventario")[0].condicion_fisica is CondicionFisica.DESTRUIDO
            assert a.consultar_pagina().obras[0].disponibles == 0
        finally:
            lector.cerrar()
            escritor.cerrar()
            await lector.esperar_cierre()
            await escritor.esperar_cierre()
    asyncio.run(recorrido())


@pytest.mark.parametrize("accion,datos", [("registrar_condicion", {"condicion": CondicionFisica.DANIADO}),
                                         ("dar_de_baja", {})])
def test_mantenimiento_no_escribe_en_rendimiento(administracion, accion, datos):
    from uuid import uuid4
    a = administracion
    a.base.with_suffix(".db.tipo.json").write_text('{"version":1,"tipo":"RENDIMIENTO"}')
    antes = a.base.read_bytes()
    with pytest.raises(ErrorPersistencia):
        a.ejecutar("inventario", accion, uuid4(), **datos)
    assert a.base.read_bytes() == antes
