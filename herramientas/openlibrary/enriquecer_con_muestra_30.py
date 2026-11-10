#!/usr/bin/env python3
"""Enriquece la base de prevalidación con JSON originales de la muestra anterior.

Se conservan las ediciones sin correspondencia, sin atribuirlas a otra obra.
ENRIQUECIDA no equivale a VALIDADA: falta control de calidad final.
"""
from __future__ import annotations
import argparse
import json
import re
import sqlite3
from pathlib import Path


def texto(v):
    if isinstance(v,dict):return texto(v.get('value'))
    return str(v or '').strip()


def isbn13(v):
    x=re.sub(r'[^0-9]','',str(v))
    return len(x)==13 and sum(int(d)*(1 if i%2==0 else 3) for i,d in enumerate(x))%10==0


def isbn10(v):
    x=re.sub(r'[^0-9X]','',str(v).upper())
    return len(x)==10 and re.fullmatch(r'[0-9]{9}[0-9X]',x) and sum((10-i)*(10 if c=='X' else int(c)) for i,c in enumerate(x))%11==0


def sinopsis_probablemente_espanol(desc):
    palabras=re.findall(r'[a-záéíóúñü]+',desc.casefold())
    es=sum(p in {'el','la','los','las','que','una','uno','para','con','del','sus','por','este','esta','cuando'} for p in palabras)
    en=sum(p in {'the','and','with','they','their','from','this','that','for','will','his','her'} for p in palabras)
    return es>=5 and es>=en*2


def enriquecer(base:Path, originales:Path):
    registros=json.loads(originales.read_text(encoding='utf-8'))
    db=sqlite3.connect(base)
    db.execute('PRAGMA foreign_keys=ON')
    coincidencias=0;enriquecidas=0;con_sinopsis_es=0;titulo_mejorado=0
    with db:
        for dato in registros:
            ed=dato.get('edicion') or {};obra=dato.get('obra') or {}
            eid=texto(ed.get('key')).split('/')[-1]
            wid=texto(obra.get('key')).split('/')[-1]
            registro=db.execute('SELECT titulo FROM edicion WHERE id_openlibrary=? AND obra_id=?',(eid,wid)).fetchone()
            if not registro:continue
            coincidencias+=1
            anterior=registro[0]
            titulo=texto(ed.get('title')) or anterior
            completo=texto(ed.get('full_title'))
            if (len(titulo)<=4 or 'spanish edition' in titulo.casefold()) and len(completo)>len(titulo):
                titulo=completo
            if titulo!=anterior:titulo_mejorado+=1
            i13=next((str(v) for v in (ed.get('isbn_13') or []) if isbn13(v)),None)
            i10=next((str(v) for v in (ed.get('isbn_10') or []) if isbn10(v)),None)
            covers=next((v for v in (ed.get('covers') or []) if isinstance(v,int) and v>0),None)
            idiomas=ed.get('languages') or []
            spa=any(isinstance(l,dict) and texto(l.get('key')).endswith('/spa') for l in idiomas)
            pubs=[texto(p) for p in (ed.get('publishers') or []) if texto(p)]
            pages=ed.get('number_of_pages')
            pages=pages if isinstance(pages,int) and pages>0 else None
            fecha=texto(ed.get('publish_date'))
            anios=re.search(r'\b(?:1[5-9]\d{2}|20\d{2})\b',fecha)
            anio=int(anios.group()) if anios else None
            desc=texto(ed.get('description'))
            desc_es=desc if sinopsis_probablemente_espanol(desc) else None
            con_sinopsis_es+=bool(desc_es)
            if obra.get('description'):
                db.execute('UPDATE obra SET descripcion_original=? WHERE id_openlibrary=?',(texto(obra['description']),wid))
            estado='ENRIQUECIDA' if (spa and (i13 or i10) and covers) else 'PENDIENTE'
            enriquecidas+=(estado=='ENRIQUECIDA')
            db.execute('''UPDATE edicion SET titulo=?,isbn_13=?,isbn_10=?,editorial=?,anio_publicacion=?,
                numero_paginas=?,portada_edicion_id=?,descripcion_es=?,idioma_verificado=?,estado_validacion=?,
                fuente_detalle=? WHERE id_openlibrary=?''',
                (titulo,i13,i10,pubs[0] if pubs else None,anio,pages,covers,desc_es,int(spa),estado,
                 'JSON_original_muestra_30',eid))
    assert not db.execute('PRAGMA foreign_key_check').fetchall()
    db.close()
    return {'coincidencias_edicion':coincidencias,'ediciones_enriquecidas':enriquecidas,
            'descripciones_edicion_es':con_sinopsis_es,'titulos_mejorados':titulo_mejorado}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base',type=Path,required=True)
    parser.add_argument('--originales',type=Path,required=True)
    a=parser.parse_args()
    print(json.dumps(enriquecer(a.base,a.originales),ensure_ascii=False,indent=2))
