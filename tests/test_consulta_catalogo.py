"""Búsqueda única y páginas de presentación sobre servicios y SQLite reales."""

from contextlib import closing
from uuid import uuid4

import pytest

from biblioteca.dominio.clasificacion import EstadoClasificacion, TipoClasificacion
from biblioteca.dominio.ejemplar import CondicionFisica, Ejemplar
from biblioteca.errores import ErrorValidacion, RegistroNoEncontrado
from biblioteca.persistencia.base_datos import conectar, transaccion


@pytest.fixture
def red(sedes):
    return tuple(sedes.registrar(n, "Dirección ficticia", "Contacto de prueba", "9 a 18")
                 for n in ("Centro", "Norte", "Sur"))


@pytest.fixture
def libros(catalogo):
    autora = catalogo.registrar_autor("Ursula K. Le Guin")
    coautor = catalogo.registrar_autor("Coautor sintético")
    terramar = catalogo.registrar_obra("A Wizard of Earthsea", [autora.id, coautor.id])
    primera = catalogo.registrar_edicion(terramar.id, "Un mago de Terramar", portada_edicion_id=123)
    catalogo.registrar_edicion(terramar.id, "Historias de Terramar")
    otra = catalogo.registrar_obra("Another story", [coautor.id])
    segunda = catalogo.registrar_edicion(otra.id, "Alfa")
    return terramar, primera, otra, segunda


@pytest.mark.parametrize("texto", ["WIZARD", "Mago de Terramar", "Historias", "Le Guin"])
def test_busqueda_or_identifica_una_obra_y_su_edicion_preferida(catalogo, libros, texto):
    obra, edicion, _, _ = libros
    pagina = catalogo.consultar_pagina(texto=texto)
    assert pagina.total == 1
    assert len(pagina.obras) == 1
    entrada = pagina.obras[0]
    assert entrada.ficha.id == obra.id
    assert entrada.ficha.edicion_preferida_id == edicion.id
    assert entrada.ficha.titulo_mostrado == "Un mago de Terramar"
    assert entrada.ficha.cantidad_ediciones == 2
    assert entrada.ficha.autores == ("Ursula K. Le Guin", "Coautor sintético")
    assert entrada.portada_edicion_id == 123
    assert entrada.disponibles == 0


def test_busqueda_por_autor_no_intersecta_titulos_y_no_duplica(catalogo, libros):
    assert catalogo.consultar_pagina(texto="sintético").total == 2
    # El fragmento coincide simultáneamente con varias ediciones de la misma obra.
    assert catalogo.consultar_pagina(texto="Terramar").total == 1
    assert catalogo.consultar_pagina(texto="Le Guin").total == 1
    assert catalogo.consultar_pagina(texto="% OR 1=1 --").total == 0


def test_paginas_son_estables_sin_duplicar_y_total_persiste_en_pagina_vacia(catalogo):
    autor = catalogo.registrar_autor("Autor de prueba")
    esperados = []
    for i in range(5):
        obra = catalogo.registrar_obra(f"Original {i}", [autor.id])
        catalogo.registrar_edicion(obra.id, "Título coincidente")
        catalogo.registrar_edicion(obra.id, "Título coincidente alternativo")
        esperados.append(obra.id)
    paginas = [catalogo.consultar_pagina(texto="coincidente", limite=2, desplazamiento=i)
               for i in (0, 2, 4, 6)]
    assert all(p.total == 5 for p in paginas)
    assert [len(p.obras) for p in paginas] == [2, 2, 1, 0]
    assert [e.ficha.id for p in paginas for e in p.obras] == sorted(esperados, key=str)


def test_edicion_sin_metadatos_opcionales_aparece_y_borrador_no(catalogo):
    autor = catalogo.registrar_autor("Autora")
    obra = catalogo.registrar_obra("Original", [autor.id])
    assert catalogo.consultar_pagina().total == 0
    catalogo.registrar_edicion(obra.id, "Español")
    entrada = catalogo.consultar_pagina().obras[0]
    assert entrada.portada_edicion_id is None
    assert entrada.generos == ()
    assert entrada.disponibles == 0


def test_disponibilidad_local_sobre_todas_las_ediciones_antes_de_limit(
    catalogo, inventario, red, libros,
):
    obra, primera, otra, segunda = libros
    centro, norte, _ = red
    alternativa = catalogo.registrar_edicion(obra.id, "Terramar alternativa")
    inventario.registrar("DEMO-C1", primera.id, centro.id)
    inventario.registrar("DEMO-C2", alternativa.id, centro.id)
    inventario.registrar("DEMO-N1", segunda.id, norte.id)
    # Alfa se ordena primero, pero se excluye antes de LIMIT por no tener copia en Centro.
    pagina = catalogo.consultar_pagina(sede_id=centro.id, disponibles=True, limite=1)
    assert pagina.total == 1 and pagina.obras[0].ficha.id == obra.id
    assert pagina.obras[0].disponibles == 2 and pagina.sede_id == centro.id
    sin_stock = catalogo.consultar_pagina(sede_id=centro.id, disponibles=False)
    assert sin_stock.total == 1 and sin_stock.obras[0].ficha.id == otra.id
    assert sin_stock.obras[0].disponibles == 0
    todas = catalogo.consultar_pagina(sede_id=centro.id)
    assert todas.total == 2  # La sede sola cambia las cantidades; no oculta obras.
    assert sum(e.disponibles for e in catalogo.consultar_pagina().obras) == 3


def test_ajena_danada_baja_sin_ubicacion_e_inactiva_no_son_disponibles(
    catalogo, inventario, ejemplar_repository, conexion, red, libros, sedes,
):
    obra, edicion, _, _ = libros
    centro, norte, sur = red
    ajena = Ejemplar("DEMO-AJENA", edicion.id, centro.id, sede_actual_id=norte.id)
    sin_ubicacion = Ejemplar("DEMO-SIN-UBICACION", edicion.id, centro.id, sede_actual_id=None)
    with transaccion(conexion):
        ejemplar_repository.agregar(ajena)
        ejemplar_repository.agregar(sin_ubicacion)
    inventario.registrar("DEMO-DANADA", edicion.id, centro.id, condicion_fisica=CondicionFisica.DANIADO)
    baja = inventario.registrar("DEMO-BAJA", edicion.id, centro.id)
    inventario.dar_de_baja(baja.id)
    inventario.registrar("DEMO-INACTIVA", edicion.id, sur.id)
    sedes.dar_de_baja(sur.id)
    assert catalogo.consultar_pagina(texto="Terramar", disponibles=True).total == 0
    assert catalogo.consultar_pagina(texto="Terramar").obras[0].disponibles == 0
    for sede in red:
        pagina = catalogo.consultar_pagina(texto="Terramar", sede_id=sede.id, disponibles=False)
        assert pagina.total == 1 and pagina.obras[0].disponibles == 0
    resumen = {d.sede_id: d for d in inventario.consultar_disponibilidad(obra.id)}
    assert resumen[norte.id].total_ubicados == 1
    assert resumen[norte.id].total_propios == 0
    assert resumen[norte.id].disponibles == 0


def test_genero_solo_aprobado_y_vocabularios_separados(catalogo, clasificaciones, libros):
    obra, _, _, _ = libros
    fantasia = clasificaciones.registrar_termino(TipoClasificacion.GENERO, "Fantasía")
    magia = clasificaciones.registrar_termino(TipoClasificacion.ETIQUETA, "Magia")
    for termino in (fantasia, magia):
        clasificaciones.proponer(obra.id, termino.id, "Dato sintético para prueba")
    assert catalogo.consultar_pagina(genero_id=fantasia.id).total == 0
    clasificaciones.revisar(obra.id, fantasia.id, EstadoClasificacion.APROBADO, "Verificación de prueba")
    clasificaciones.revisar(obra.id, magia.id, EstadoClasificacion.APROBADO, "Verificación de prueba")
    pagina = catalogo.consultar_pagina(genero_id=fantasia.id)
    assert pagina.total == 1 and pagina.obras[0].generos == ("Fantasía",)
    assert catalogo.consultar_pagina(genero_id=magia.id).total == 0
    clasificaciones.revisar(obra.id, fantasia.id, EstadoClasificacion.RECHAZADO, "Corrección de prueba")
    assert catalogo.consultar_pagina(genero_id=fantasia.id).total == 0


def test_consultas_de_pagina_son_acotadas_y_no_por_tarjeta(catalogo, conexion, libros, red):
    consultas = []
    conexion.set_trace_callback(consultas.append)
    try:
        pagina = catalogo.consultar_pagina(sede_id=red[0].id)
    finally:
        conexion.set_trace_callback(None)
    assert len(pagina.obras) == 2
    assert len([s for s in consultas if s.startswith("SELECT")]) == 6
    assert "BEGIN" in consultas and "ROLLBACK" in consultas
    assert not conexion.in_transaction


@pytest.mark.parametrize("filtros", [dict(texto=123), dict(disponibles=1), dict(disponibles="sí"),
    dict(sede_id="Centro"), dict(genero_id="Fantasía"), dict(limite=True), dict(limite=0),
    dict(limite=101), dict(desplazamiento=-1)])
def test_filtros_invalidos_no_dejan_transaccion_abierta(catalogo, conexion, filtros):
    with pytest.raises(ErrorValidacion):
        catalogo.consultar_pagina(**filtros)
    assert not conexion.in_transaction


def test_sede_desconocida_se_informa(catalogo):
    with pytest.raises(RegistroNoEncontrado, match="sede"):
        catalogo.consultar_pagina(sede_id=uuid4())


def test_lectura_no_confirma_ni_revierte_transaccion_del_llamador(catalogo, conexion, libros):
    with transaccion(conexion):
        conexion.execute("UPDATE obra SET descripcion_original = 'Cambio pendiente' WHERE id = ?",
                         (str(libros[0].id),))
        catalogo.consultar_pagina()
        assert conexion.in_transaction
        with pytest.raises(ErrorValidacion):
            catalogo.consultar_pagina(limite=0)
        assert conexion.in_transaction
    assert catalogo.obtener_obra(libros[0].id).descripcion_original == "Cambio pendiente"


def test_total_y_pagina_comparten_instantanea_con_un_escritor_concurrente(
    catalogo, conexion, ruta_db, libros, monkeypatch,
):
    import biblioteca.repositorios.obra_repository as modulo
    conexion.execute("PRAGMA journal_mode = WAL")
    ejecutar_real = modulo.ejecutar
    escrito = False
    def ejecutar_y_modificar(c, sql, parametros=()):
        nonlocal escrito
        cursor = ejecutar_real(c, sql, parametros)
        if sql.startswith("SELECT COUNT(*) FROM obra") and not escrito:
            escrito = True
            with closing(conectar(ruta_db)) as otra:
                with transaccion(otra):
                    otra.execute("UPDATE edicion SET titulo_normalizado = 'cambiado', titulo = 'Cambiado'")
        return cursor
    monkeypatch.setattr(modulo, "ejecutar", ejecutar_y_modificar)
    pagina = catalogo.consultar_pagina(texto="Terramar")
    assert escrito and pagina.total == 1 and len(pagina.obras) == 1
    assert pagina.obras[0].ficha.titulo_mostrado == "Un mago de Terramar"
    assert catalogo.consultar_pagina(texto="Terramar").total == 0
