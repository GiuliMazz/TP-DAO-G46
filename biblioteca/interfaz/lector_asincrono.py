"""Un trabajador y una petición pendiente por destino, reemplazable.

Cancelar una espera no cancela SQLite ni habilita otro trabajador. El bombeo
conserva su turno hasta que termina el hilo y su conexión se cierra.
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from functools import partial


class ConsultaReemplazada(Exception):
    pass


class LectorAsincrono:
    DESTINOS = frozenset({"catalogo", "ficha", "configuracion", "socios", "sedes", "inventario"})

    def __init__(self):
        self._ejecutor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="horizonte-lectura")
        self._pendientes = {}
        self._bombeo = None
        self._cerrado = False

    async def ejecutar(self, destino, funcion, *args, **kwargs):
        if destino not in self.DESTINOS:
            raise ValueError("Destino de lectura desconocido")
        if self._cerrado:
            raise ConsultaReemplazada()
        futuro = asyncio.get_running_loop().create_future()
        anterior = self._pendientes.get(destino)
        if anterior is not None and not anterior[1].done():
            anterior[1].set_exception(ConsultaReemplazada())
        self._pendientes[destino] = (partial(funcion, *args, **kwargs), futuro)
        if self._bombeo is None or self._bombeo.done():
            self._bombeo = asyncio.create_task(self._procesar())
        return await futuro

    async def _procesar(self):
        while self._pendientes and not self._cerrado:
            destino = next(iter(self._pendientes))
            funcion, futuro = self._pendientes.pop(destino)
            if futuro.done():
                continue
            try:
                resultado = await asyncio.get_running_loop().run_in_executor(self._ejecutor, funcion)
            except Exception as error:
                if not futuro.done():
                    futuro.set_exception(error)
            else:
                if not futuro.done():
                    futuro.set_result(resultado)

    def cerrar(self):
        self._cerrado = True
        for _, futuro in self._pendientes.values():
            if not futuro.done():
                futuro.set_exception(ConsultaReemplazada())
        self._pendientes.clear()
        self._ejecutor.shutdown(wait=False, cancel_futures=True)

    async def esperar_cierre(self):
        """Una reconexión espera al hilo previo sin congelar el ciclo gráfico."""
        if self._bombeo is not None:
            await asyncio.shield(self._bombeo)
