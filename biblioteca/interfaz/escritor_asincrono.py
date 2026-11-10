"""Un comando aceptado termina; nunca se reemplaza por otro guardado."""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from functools import partial

from biblioteca.errores import ErrorBiblioteca


class EscritorOcupado(ErrorBiblioteca):
    pass


class EscritorAsincrono:
    def __init__(self):
        self._ejecutor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="horizonte-guardado")
        self._tarea = None
        self._cerrado = False

    async def ejecutar(self, funcion, *args, **kwargs):
        if self._cerrado:
            raise EscritorOcupado("La sesión se está cerrando. Reconectá antes de guardar.")
        if self._tarea is not None and not self._tarea.done():
            raise EscritorOcupado("Hay un guardado en curso. Esperá su confirmación.")
        self._tarea = asyncio.get_running_loop().run_in_executor(
            self._ejecutor, partial(funcion, *args, **kwargs))
        # Recuperar también excepciones cuando el usuario ya dejó de esperar.
        self._tarea.add_done_callback(lambda f: f.exception() if not f.cancelled() else None)
        return await asyncio.shield(self._tarea)

    def cerrar(self):
        self._cerrado = True
        self._ejecutor.shutdown(wait=False, cancel_futures=False)

    async def esperar_cierre(self):
        if self._tarea is not None:
            try:
                await asyncio.shield(self._tarea)
            except Exception:
                # El formulario comunica fallos; al reconectar se relee la base.
                pass
