#!/usr/bin/env python3
"""Etapa 1: prepara localmente candidatos de Open Library para el TP.

No realiza conexiones a internet. Importa los JSON del extractor exploratorio,
conserva el origen y genera una base relacional en estado PENDIENTE.

Uso:
    python3 preparar_catalogo.py --entrada catalogo_exploratorio.json --salida salida_v3
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import re
import sqlite3
from collections import Counter
from pathlib import Path

WORK = re.compile(r'^OL\d+W$')
EDITION = re.compile(r'^OL\d+M$')
AUTHOR = re.compile(r'^OL\d+A$')

SCHEMA = '''
PRAGMA foreign_keys=ON;
CREATE TABLE obra (
    id_openlibrary TEXT PRIMARY KEY,
    titulo_original TEXT NOT NULL,
    descripcion_original TEXT,
    anio_primera_publicacion INTEGER,
    portada_obra_id INTEGER,
    categoria_busqueda TEXT,
    fuente TEXT NOT NULL DEFAULT 'Open Library'
);
CREATE TABLE edicion (
    id_openlibrary TEXT PRIMARY KEY,
    obra_id TEXT NOT NULL REFERENCES obra(id_openlibrary),
    titulo TEXT NOT NULL,
    idioma TEXT NOT NULL DEFAULT 'spa' CHECK (idioma='spa'),
    isbn_13 TEXT,
    isbn_10 TEXT,
    editorial TEXT,
    anio_publicacion INTEGER,
    numero_paginas INTEGER,
    portada_edicion_id INTEGER,
    descripcion_es TEXT,
    idioma_verificado INTEGER NOT NULL DEFAULT 0 CHECK (idioma_verificado IN (0,1)),
    estado_validacion TEXT NOT NULL DEFAULT 'PENDIENTE'
        CHECK (estado_validacion IN ('PENDIENTE','ENRIQUECIDA','VALIDADA','RECHAZADA')),
    fecha_validacion TEXT,
    fuente_detalle TEXT,
    fuente TEXT NOT NULL DEFAULT 'Open Library',
    CHECK (estado_validacion != 'VALIDADA' OR (isbn_13 IS NOT NULL OR isbn_10 IS NOT NULL)
           AND portada_edicion_id IS NOT NULL AND idioma_verificado=1)
);
CREATE TABLE autor (
    id_openlibrary TEXT PRIMARY KEY,
    nombre TEXT NOT NULL
);
CREATE TABLE obra_autor (
    obra_id TEXT NOT NULL REFERENCES obra(id_openlibrary),
    autor_id TEXT NOT NULL REFERENCES autor(id_openlibrary),
    PRIMARY KEY (obra_id, autor_id)
);
CREATE TABLE genero (id INTEGER PRIMARY KEY, nombre TEXT NOT NULL UNIQUE);
CREATE TABLE obra_genero (
    obra_id TEXT NOT NULL REFERENCES obra(id_openlibrary),
    genero_id INTEGER NOT NULL REFERENCES genero(id),
    estado TEXT NOT NULL DEFAULT 'PROPUESTO' CHECK (estado IN ('PROPUESTO','APROBADO','RECHAZADO')),
    metodo TEXT NOT NULL DEFAULT 'reglas_exploratorias',
    PRIMARY KEY (obra_id, genero_id)
);
CREATE TABLE etiqueta (id INTEGER PRIMARY KEY, nombre TEXT NOT NULL UNIQUE);
CREATE TABLE obra_etiqueta (
    obra_id TEXT NOT NULL REFERENCES obra(id_openlibrary),
    etiqueta_id INTEGER NOT NULL REFERENCES etiqueta(id),
    estado TEXT NOT NULL DEFAULT 'PROPUESTO' CHECK (estado IN ('PROPUESTO','APROBADO','RECHAZADO')),
    metodo TEXT NOT NULL DEFAULT 'reglas_exploratorias',
    PRIMARY KEY (obra_id, etiqueta_id)
);
CREATE TABLE materia_original (id INTEGER PRIMARY KEY, texto TEXT NOT NULL UNIQUE);
CREATE TABLE obra_materia_original (
    obra_id TEXT NOT NULL REFERENCES obra(id_openlibrary),
    materia_id INTEGER NOT NULL REFERENCES materia_original(id),
    PRIMARY KEY (obra_id, materia_id)
);
CREATE INDEX ix_edicion_obra ON edicion(obra_id);
CREATE INDEX ix_edicion_validacion ON edicion(estado_validacion);
CREATE INDEX ix_obra_autor ON obra_autor(autor_id);
CREATE INDEX ix_obra_genero ON obra_genero(genero_id);
CREATE INDEX ix_obra_etiqueta ON obra_etiqueta(etiqueta_id);
CREATE INDEX ix_obra_materia ON obra_materia_original(materia_id);
'''


def ctexto(valor):
    if valor is None:
        return ''
    return re.sub(r'\s+', ' ', str(valor)).strip()


def limpiar_csv(valor):
    """Evita que Calc/Excel ejecute contenido del catálogo como fórmula."""
    valor = ctexto(valor)
    return "'" + valor if valor.startswith(('=', '+', '-', '@')) else valor


def riesgos(item):
    motivos = []
    titulo = ctexto(item.get('titulo_es'))
    generos = set(item.get('generos_provisorios') or [])
    materias = [ctexto(x).lower() for x in (item.get('materias_originales') or [])]
    autores = item.get('autores') or []
    if not titulo or len(titulo) <= 4:
        motivos.append(('titulo_corto_o_vacio', 9))
    if re.search(r'spanish edition|edici[oó]n en espa[nñ]ol|/ the |/ a |/ english', titulo, re.I):
        motivos.append(('titulo_bilingue_o_marca_edicion', 3))
    if len(titulo)>10 and titulo.upper()==titulo and re.search(r'[A-ZÁÉÍÓÚ]', titulo):
        motivos.append(('titulo_todo_mayusculas', 1))
    if len(autores) >= 6:
        motivos.append(('muchos_autores_posibles_colaboradores', 8))
    if any('cover by ' in ctexto(a.get('nombre')).casefold() for a in autores):
        motivos.append(('autor_parece_credito_de_portada', 8))
    if any('Biografía' == g for g in generos) and any(s in ('fiction','ficción','novela','juvenile fiction') for s in materias):
        motivos.append(('biografia_con_materias_ficcion', 5))
    if 'Historia' in generos and 'Novela histórica' in generos:
        motivos.append(('historia_y_novela_historica_a_revisar', 4))
    if (generos & {'Ciencias','Tecnología'}) and (generos & {'Fantasía','Ciencia ficción','Romance','Terror'}):
        motivos.append(('ciencia_tecnologia_mezcladas_con_ficcion', 7))
    if len(generos) >= 4:
        motivos.append(('cuatro_o_mas_generos', 5))
    # Una sola coincidencia genérica en Open Library no es prueba fiable del género.
    if 'Fantasía' in generos and not any(s in ('fantasy','fantasy fiction','fantasía','ficción fantástica','novela fantástica') for s in materias):
        motivos.append(('fantasia_sin_materia_directa', 2))
    if len(materias) > 120:
        motivos.append(('demasiadas_materias', 2))
    anio = item.get('anio_obra_estimado')
    if not isinstance(anio, int) or anio < 1400 or anio > 2026:
        motivos.append(('anio_fuera_de_rango_o_ausente', 4))
    # Los siguientes campos vienen sin comprobar: no se usan como anomalía por registro.
    return sorted(motivos, key=lambda kv:-kv[1])


def insertar_relaciones(db, tabla_entidad, tabla_relacion, campo_fk, nombre, wid):
    db.execute(f'INSERT OR IGNORE INTO {tabla_entidad}(nombre) VALUES (?)', (nombre,))
    eid = db.execute(f'SELECT id FROM {tabla_entidad} WHERE nombre=?',(nombre,)).fetchone()[0]
    db.execute(f'INSERT OR IGNORE INTO {tabla_relacion}(obra_id,{campo_fk}) VALUES (?,?)',(wid,eid))


def generar(entrada: Path, salida: Path, limite_auditoria: int):
    registros = json.loads(entrada.read_text(encoding='utf-8'))
    if not isinstance(registros, list):
        raise ValueError('El archivo debe contener una lista de registros.')
    salida.mkdir(parents=True, exist_ok=True)
    path_db = salida / 'catalogo_prevalidacion.db'
    if path_db.exists():
        path_db.unlink()
    db = sqlite3.connect(path_db)
    db.executescript(SCHEMA)
    errores, revisiones, generos, categorias = [], [], Counter(), Counter()
    vistos_obras, vistas_ediciones = set(), set()
    with db:
        for indice,item in enumerate(registros,1):
            wid = ctexto(item.get('obra_id'))
            eid = ctexto(item.get('edicion_id'))
            titulo_obra = ctexto(item.get('titulo_original'))
            titulo_ed = ctexto(item.get('titulo_es'))
            if not WORK.fullmatch(wid) or not EDITION.fullmatch(eid) or not titulo_obra or not titulo_ed:
                errores.append({'fila':indice,'obra_id':wid,'edicion_id':eid,'motivo':'ID/título inválido'})
                continue
            if wid in vistos_obras or eid in vistas_ediciones:
                errores.append({'fila':indice,'obra_id':wid,'edicion_id':eid,'motivo':'ID duplicado'})
                continue
            vistos_obras.add(wid)
            vistas_ediciones.add(eid)
            anio = item.get('anio_obra_estimado')
            if not isinstance(anio,int) or not 0 < anio < 3000: anio=None
            cub = item.get('portada_obra_id')
            if not isinstance(cub,int) or cub <=0: cub=None
            categoria=ctexto(item.get('categoria_busqueda'))
            categorias[categoria]+=1
            db.execute('INSERT INTO obra(id_openlibrary,titulo_original,anio_primera_publicacion,portada_obra_id,categoria_busqueda) VALUES (?,?,?,?,?)', (wid,titulo_obra,anio,cub,categoria))
            db.execute('INSERT INTO edicion(id_openlibrary,obra_id,titulo,idioma,estado_validacion) VALUES (?,?,?,?,?)',(eid,wid,titulo_ed,'spa','PENDIENTE'))
            for ai, autor in enumerate(item.get('autores') or []):
                nombre = ctexto(autor.get('nombre'))
                aid = ctexto(autor.get('id'))
                if not nombre:continue
                if not AUTHOR.fullmatch(aid):
                    aid='LOCAL-'+hashlib.sha256(f'{wid}|{ai}|{nombre}'.encode('utf8')).hexdigest()[:20]
                db.execute('INSERT OR IGNORE INTO autor(id_openlibrary,nombre) VALUES (?,?)',(aid,nombre))
                db.execute('INSERT OR IGNORE INTO obra_autor(obra_id,autor_id) VALUES (?,?)',(wid,aid))
            for genero in sorted(set(item.get('generos_provisorios') or [])):
                valor=ctexto(genero)
                if valor:
                    insertar_relaciones(db,'genero','obra_genero','genero_id',valor,wid)
                    generos[valor]+=1
            for etiqueta in sorted(set(item.get('etiquetas_provisorias') or [])):
                valor=ctexto(etiqueta)
                if valor:insertar_relaciones(db,'etiqueta','obra_etiqueta','etiqueta_id',valor,wid)
            for materia in set(item.get('materias_originales') or []):
                valor=ctexto(materia)
                if not valor:continue
                db.execute('INSERT OR IGNORE INTO materia_original(texto) VALUES (?)',(valor,))
                mid=db.execute('SELECT id FROM materia_original WHERE texto=?',(valor,)).fetchone()[0]
                db.execute('INSERT OR IGNORE INTO obra_materia_original(obra_id,materia_id) VALUES (?,?)',(wid,mid))
            motivos=riesgos(item)
            revisiones.append({'obra_id':wid,'edicion_id':eid, 'titulo_es':titulo_ed, 'titulo_original':titulo_obra,
                'autores':' | '.join(ctexto(a.get('nombre')) for a in item.get('autores') or []),
                'categoria_busqueda':categoria, 'generos':' | '.join(item.get('generos_provisorios') or []),
                'etiquetas':' | '.join(item.get('etiquetas_provisorias') or []),
                'puntaje_riesgo':sum(p for _,p in motivos),
                'motivos':' | '.join(m for m,_ in motivos),
                'url':item.get('url_openlibrary') or f'https://openlibrary.org/books/{eid}',
                'generos_corregidos':'', 'etiquetas_corregidas':'', 'titulo_corregido':'','comentarios':''})
    integ=db.execute('PRAGMA foreign_key_check').fetchall()
    if integ: raise RuntimeError(f'Integridad referencial incorrecta: {integ[:3]}')
    conteos={tabla:db.execute(f'SELECT COUNT(*) FROM {tabla}').fetchone()[0]
           for tabla in ('obra','edicion','autor','obra_autor','genero','obra_genero','etiqueta','obra_etiqueta','materia_original','obra_materia_original')}
    estados=dict(db.execute('SELECT estado_validacion,COUNT(*) FROM edicion GROUP BY estado_validacion').fetchall())
    db.close()
    columnas = ['obra_id','edicion_id','titulo_es','titulo_original','autores','categoria_busqueda','generos','etiquetas','puntaje_riesgo','motivos','url','generos_corregidos','etiquetas_corregidas','titulo_corregido','comentarios']
    revisiones.sort(key=lambda x:(-x['puntaje_riesgo'],x['obra_id']))
    def escribir_csv(destino,filas):
        with destino.open('w',encoding='utf-8-sig',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=columnas,delimiter=';')
            writer.writeheader()
            for fila in filas:
                writer.writerow({k:limpiar_csv(fila.get(k,'')) for k in columnas})
    escribir_csv(salida/'auditoria_prioritaria.csv',revisiones[:limite_auditoria])
    escribir_csv(salida/'catalogo_resumido.csv',sorted(revisiones,key=lambda x:x['obra_id']))
    motivos_agrupados=Counter(m for r in revisiones for m in r['motivos'].split(' | ') if m)
    informe={'fuente':entrada.name,'modo':'PREVALIDACION_OFFLINE','registros_entrada':len(registros),
        'registros_validos':len(revisiones),'registros_descartados':len(errores),
        'conteos':conteos,'estados_edicion':estados,'categorias_busqueda':dict(categorias),
        'generos_propuestos':dict(generos),'alertas':dict(motivos_agrupados),
        'registros_con_alertas':sum(r['puntaje_riesgo']>0 for r in revisiones),
        'auditoria_exportada':min(limite_auditoria,len(revisiones)),
        'advertencias':[
            'No se verifico ISBN, editorial, portada de edicion ni sinopsis en espanol.',
            'Los generos y etiquetas importados siguen PROPUESTOS, no verificados.',
            'La categoria de busqueda no es un genero confirmado.',
            'La portada de obra no acredita una portada de la edicion espanola.',
            'Los titulos y anios sospechosos se marcaron, no se corrigieron automaticamente.',
            'Una etiqueta alerta no significa necesariamente un error.'
        ]}
    (salida/'metricas_prevalidacion.json').write_text(json.dumps(informe,ensure_ascii=False,indent=2),encoding='utf-8')
    (salida/'errores_importacion.json').write_text(json.dumps(errores,ensure_ascii=False,indent=2),encoding='utf-8')
    lineas = [
        '# Informe de prevalidacion bibliografica', '',
        f'- **Obras ingresadas:** {len(revisiones)} de {len(registros)}',
        f'- **Ediciones candidatas:** {conteos["edicion"]}; todas en estado `PENDIENTE`',
        f'- **Autores distintos:** {conteos["autor"]}',
        f'- **Materias originales distintas:** {conteos["materia_original"]}',
        f'- **Obras con alguna alerta heuristica:** {informe["registros_con_alertas"]} (no equivale a errores confirmados)',
        '', '## Alertas para revision', '', '| Alerta | Obras |', '|---|---:|'
    ]
    lineas += [f'| {m} | {c} |' for m,c in motivos_agrupados.most_common()]
    lineas += ['', '## Registros prioritarios', '', '| Obra | Título | Puntaje | Motivos |', '|---|---|---:|---|']
    lineas += [f'| {r["obra_id"]} | {r["titulo_es"].replace("|","/")[:65]} | {r["puntaje_riesgo"]} | {r["motivos"].replace("|",",")} |' for r in revisiones[:15]]
    lineas += ['', '## Limites', '',
      'Los 1000 registros son candidatos; **no se verificaron los atributos particulares de las ediciones**.',
      'El archivo de auditoría contiene sugerencias de revisión. No se aplican cambios sin evidencia.',
      'Para la importación a escala de 100.000 se deberán procesar los dumps oficiales de obras, ediciones y autores.']
    (salida/'informe_prevalidacion.md').write_text('\n'.join(lineas)+'\n',encoding='utf-8')
    print(json.dumps({'obras':conteos['obra'],'ediciones_pendientes':estados.get('PENDIENTE',0),
                      'autores':conteos['autor'],'materias':conteos['materia_original'],
                      'registros_con_alertas':informe['registros_con_alertas'],
                      'auditoria':informe['auditoria_exportada']},ensure_ascii=False,indent=2))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--entrada',required=True,type=Path)
    parser.add_argument('--salida',default=Path('salida_v3'),type=Path)
    parser.add_argument('--auditoria',type=int,default=100)
    args=parser.parse_args()
    if args.auditoria<1:parser.error('--auditoria debe ser >= 1')
    generar(args.entrada,args.salida,args.auditoria)


if __name__=='__main__':main()
