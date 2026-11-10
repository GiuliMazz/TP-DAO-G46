// Definir y ejecutar: return await comprobarInteraccion(page);
// Usar la misma página Playwright, Catálogo y tema claro.
async function comprobarInteraccion(page) {
const entrada = page.getByRole('textbox');
const cargando = page.getByText('Buscando…', {exact:true}).first();
await entrada.fill('Original sintético 000011');
await page.getByText('1 obra · datos sintéticos',{exact:true}).waitFor({state:'attached',timeout:15000});
await cargando.waitFor({state:'detached',timeout:10000});
await entrada.fill('sintético');
await cargando.waitFor({state:'attached',timeout:10000});
// Ensayo de interacción, no una muestra de latencia SQL: dejar pasar debounce
// para que el trabajador ya esté consultando; contrastar después con su registro.
await page.waitForTimeout(350);
const inicio = await page.evaluate(()=>performance.now());
await page.locator('[aria-label="Activar modo oscuro"]').getByRole('button').click();
await page.locator('[aria-label="Activar modo claro"]').waitFor({state:'attached',timeout:10000});
const fin = await page.evaluate(()=>performance.now());
const respuesta = {cambio_tema_ms:fin-inicio, indicador_carga_al_cambiar_tema:await cargando.count()>0};
await page.getByText('100000 obras · datos sintéticos',{exact:true}).waitFor({state:'attached',timeout:20000});
await cargando.waitFor({state:'detached',timeout:10000});
await entrada.fill('Original sintético 000012');
await page.getByText('1 obra · datos sintéticos',{exact:true}).waitFor({state:'attached',timeout:10000});
await cargando.waitFor({state:'detached',timeout:10000});
await entrada.fill('sintético');
await cargando.waitFor({state:'attached',timeout:10000});
await page.waitForTimeout(350);
await entrada.fill('Original sintético 001234');
await page.getByRole('group',{name:/Abrir ficha de Libro sintético 001234/}).waitFor({state:'attached',timeout:15000});
await cargando.waitFor({state:'detached',timeout:10000});
return {respuesta, obsoleta:{resultado_final:'Libro sintético 001234',consulta_reemplazada:'sintético',
  texto_final:await entrada.inputValue()}};
}
