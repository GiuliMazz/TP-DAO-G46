#!/usr/bin/env python3
"""Ejecuta la etapa 1 completa (offline) y consolida el informe final.

Uso:
    python3 ejecutar_etapa1.py --catalogo catalogo_exploratorio.json \
        --detalles respuestas_originales.json --salida resultado_etapa1
"""
import argparse
import json
import sqlite3
from pathlib import Path
from preparar_catalogo import generar
from enriquecer_con_muestra_30 import enriquecer


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--catalogo',required=True,type=Path)
    p.add_argument('--detalles',type=Path)
    p.add_argument('--salida',type=Path,default=Path('resultado_etapa1'))
    p.add_argument('--auditoria',type=int,default=100)
    a=p.parse_args()
    if a.auditoria<1:p.error('--auditoria debe ser al menos 1')
    generar(a.catalogo,a.salida,a.auditoria)
    est={'coincidencias_edicion':0,'ediciones_enriquecidas':0,'descripciones_edicion_es':0,'titulos_mejorados':0}
    if a.detalles:
        est=enriquecer(a.salida/'catalogo_prevalidacion.db',a.detalles)
    db=sqlite3.connect(a.salida/'catalogo_prevalidacion.db')
    estados=dict(db.execute('SELECT estado_validacion,COUNT(*) FROM edicion GROUP BY estado_validacion'))
    assert not db.execute('PRAGMA foreign_key_check').fetchall()
    db.close()
    archivo=a.salida/'metricas_prevalidacion.json'
    datos=json.loads(archivo.read_text(encoding='utf-8'))
    datos['estados_edicion']=estados
    datos['reutilizacion_muestra_30']=est
    archivo.write_text(json.dumps(datos,ensure_ascii=False,indent=2),encoding='utf-8')
    reporte=a.salida/'informe_prevalidacion.md'
    texto=reporte.read_text(encoding='utf-8')
    texto=texto.replace('todas en estado `PENDIENTE`',f'estados: {estados}')
    texto += ('\n## Aprovechamiento de la muestra anterior\n\n'
              f'- Ediciones coincidentes: **{est["coincidencias_edicion"]}**\n'
              f'- Ediciones enriquecidas (no validadas): **{est["ediciones_enriquecidas"]}**\n'
              f'- Sinopsis de edición probablemente en español: **{est["descripciones_edicion_es"]}**\n'
              f'- Títulos sustituidos por un título más completo del mismo JSON: **{est["titulos_mejorados"]}**\n\n'
              'Este paso no consulta la API ni inventa metadatos. Las ediciones enriquecidas conservan el estado `ENRIQUECIDA` hasta su revisión final.\n')
    reporte.write_text(texto,encoding='utf-8')
    print(json.dumps({'estados_finales':estados,'muestra_30':est},ensure_ascii=False,indent=2))


if __name__=='__main__':main()
