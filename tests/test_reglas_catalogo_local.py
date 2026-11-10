"""Correspondencias conservadoras y precedencia de revisión bibliográfica."""

from biblioteca.dominio.clasificacion import EstadoClasificacion as Estado, TipoClasificacion as Tipo
from herramientas.auditar_catalogo_local import cobertura


def test_reglas_locales_aplican_texto_completo_y_separan_tipos(catalogo, clasificaciones):
    autor = catalogo.registrar_autor("Autora")
    obra = catalogo.registrar_obra("Obra", [autor.id])
    reglas = clasificaciones.preparar_reglas_catalogo_local()
    clasificaciones.procesar_materias(obra.id, ["Fiction, science fiction, general", "Magic", "Young adult fiction"], reglas)
    aprobadas = clasificaciones.listar(obra.id, estado=Estado.APROBADO)
    assert {(c.termino.tipo, c.termino.nombre) for c in aprobadas} == {
        (Tipo.GENERO, "Ciencia ficción"), (Tipo.ETIQUETA, "Magia"), (Tipo.PUBLICO, "Juvenil")}
    otra = catalogo.registrar_obra("Otra", [autor.id])
    clasificaciones.procesar_materias(otra.id, ["Fantasy", "Science", "History", "Biography", "Fiction about Magic"], reglas)
    assert [(c.termino.tipo, c.termino.nombre) for c in clasificaciones.listar(otra.id)] == [(Tipo.ETIQUETA, "Ciencia")]


def test_descriptores_dudosos_quedan_propuestos_sin_inferir_adultos(catalogo, clasificaciones):
    autor = catalogo.registrar_autor("Autora")
    obra = catalogo.registrar_obra("Estudios", [autor.id])
    reglas = clasificaciones.preparar_reglas_catalogo_local()
    clasificaciones.procesar_materias(obra.id, ["Science fiction", "Juvenile literature"], reglas)
    assert not clasificaciones.listar(obra.id, estado=Estado.APROBADO)
    assert {c.termino.nombre for c in clasificaciones.listar(obra.id, estado=Estado.PROPUESTO)} == {"Ciencia ficción", "Juvenil"}


def test_repetir_reglas_preserva_rechazo_humano_y_conteos_por_obra(catalogo, clasificaciones, conexion):
    autor = catalogo.registrar_autor("Autora")
    obra = catalogo.registrar_obra("Historia", [autor.id])
    reglas = clasificaciones.preparar_reglas_catalogo_local()
    clasificaciones.procesar_materias(obra.id, ["Historical fiction", "Fiction, historical, general"], reglas)
    assert cobertura(conexion)["tipos"]["GENERO"]["APROBADO"] == 1  # dos evidencias, una obra
    termino = clasificaciones.listar(obra.id)[0].termino
    clasificaciones.revisar(obra.id, termino.id, Estado.RECHAZADO, "Revisión bibliográfica")
    repetidas = clasificaciones.preparar_reglas_catalogo_local()
    assert [(r.id, r.version) for r in repetidas] == [(r.id, r.version) for r in reglas]
    clasificaciones.procesar_materias(obra.id, (), repetidas)
    assert clasificaciones.obtener(obra.id, termino.id).decision.estado is Estado.RECHAZADO
    assert cobertura(conexion)["tipos"]["GENERO"]["APROBADO"] == 0
