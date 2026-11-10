// Definir esta función y ejecutar: return await medirCliente(page);
// En runPlaywrightCode, con la página 3B.4 ya navegada al Catálogo,
// accesibilidad habilitada y la primera página visible. No usa paquetes nuevos.
// Las capturas verifican composición del cliente; no miden una pantalla física.
async function medirCliente(page) {
const resultados = [];
await page.evaluate(() => { globalThis.__horizonte_medicion = {muestras: [], finalizada: false}; });
const ahora = () => page.evaluate(() => performance.now());
const frame = () => page.evaluate(() => new Promise(resolve =>
  requestAnimationFrame(() => requestAnimationFrame(() => resolve(performance.now())))));
const escenarios = [
  {nombre: 'titulo_original', texto: 'Original sintético 000011', esperado: '1–1 de 1 · 24 por página'},
  {nombre: 'titulo_edicion', texto: 'Libro sintético 000012', esperado: '1–1 de 1 · 24 por página'},
  {nombre: 'titulo_alternativo', texto: 'alternativa sintética 000050', esperado: '1–1 de 1 · 24 por página'},
  {nombre: 'autor', texto: 'Autor sintético 0001', esperado: '1–24 de 100 · 24 por página'},
  {nombre: 'sin_resultados', texto: 'NoExiste_Benchmark_Horizonte', esperado: 'Sin resultados'},
  {nombre: 'pagina_completa', texto: 'sintético', esperado: '1–24 de 100000 · 24 por página'},
];
// 1 calentamiento por escenario, luego 3 muestras. Misma vista y conexiones
// independientes del proveedor de consultas para cada petición del servidor.
for (const escenario of escenarios) {
  for (let repeticion = 0; repeticion < 4; repeticion++) {
    // Forzar un cambio inequívoco: no aceptar el resultado de la repetición previa.
    await page.getByRole('textbox').fill('PreparaciónSinCoincidencias_' + escenario.nombre + repeticion);
    await page.getByText('Buscando…', {exact: true}).first().waitFor({state: 'attached', timeout: 10000});
    await page.getByText('0 obras · datos sintéticos', {exact: true}).waitFor({state: 'attached', timeout: 20000});
    await page.getByText('Buscando…', {exact: true}).first().waitFor({state: 'detached', timeout: 10000});
    await frame();
    const inicio = await ahora();
    await page.getByRole('textbox').fill(escenario.texto);
    // El indicador es la evidencia de que Flet recibió este evento de entrada.
    await page.getByText('Buscando…', {exact: true}).first().waitFor({state: 'attached', timeout: 10000});
    const cargando = await ahora();
    await page.getByText(escenario.esperado, {exact: true}).waitFor({state: 'attached', timeout: 30000});
    await page.getByText('Buscando…', {exact: true}).first().waitFor({state: 'detached', timeout: 10000});
    const semantica = await ahora();
    const siguienteFrame = await frame();
    const captura = await page.screenshot({animations: 'disabled'});
    const fin = await ahora();
    resultados.push({escenario: escenario.nombre, repeticion, calentamiento: repeticion === 0,
      hasta_carga_ms: cargando - inicio, hasta_semantica_ms: semantica - inicio,
      hasta_frame_ms: siguienteFrame - inicio, hasta_captura_ms: fin - inicio,
      captura_bytes: captura.length, esperado: escenario.esperado});
    await page.evaluate(muestras => { globalThis.__horizonte_medicion.muestras = muestras; }, resultados);
  }
}
async function esperarListado() {
  await page.getByText('Cargando catálogo…', {exact: true}).first().waitFor({state: 'attached', timeout: 10000});
  await page.getByText('Cargando catálogo…', {exact: true}).first().waitFor({state: 'detached', timeout: 30000});
}
async function limpiar() {
  await page.getByRole('button', {name:'Limpiar filtros', exact:true}).click();
  await esperarListado();
}
async function medirAccion(escenario, repeticion, accion, esperado, calentamiento) {
  const inicio = await ahora();
  await accion();
  await esperarListado();
  await page.getByText(esperado, {exact:true}).waitFor({state:'attached',timeout:30000});
  const semantica = await ahora();
  await frame();
  const captura = await page.screenshot({animations:'disabled'});
  const fin = await ahora();
  resultados.push({escenario, repeticion, calentamiento, hasta_semantica_ms:semantica-inicio,
    hasta_captura_ms:fin-inicio, captura_bytes:captura.length, esperado});
  await page.evaluate(muestras => { globalThis.__horizonte_medicion.muestras = muestras; }, resultados);
}
// Los primeros botones son tema, sede de trabajo, Inicio, Catálogo y los tres
// filtros. Elegir opciones por nombre; no usar coordenadas de capturas.
for(let n=0;n<4;n++) {
  await limpiar();
  await medirAccion('genero', n, async()=>{
    await page.getByRole('button').nth(4).click();
    await page.getByRole('button',{name:'Género sintético 0',exact:true}).click();
  }, '1–24 de 18182 · 24 por página', n===0);
}
for(let n=0;n<4;n++) {
  await limpiar();
  await page.getByRole('button').nth(5).click();
  await page.getByRole('button',{name:'Norte',exact:true}).click();
  await esperarListado();
  await medirAccion('disponibilidad_local', n, async()=>{
    await page.getByRole('button').nth(6).click();
    await page.getByRole('button',{name:'Disponibles',exact:true}).click();
  }, '1–24 de 15824 · 24 por página', n===0);
}
await limpiar();
for(let n=0;n<3;n++) {
  await medirAccion('pagina_siguiente', n+1, async()=>{
    await page.locator('[aria-label="Página siguiente"]').getByRole('button').click();
  }, `${25+24*n}–${48+24*n} de 100000 · 24 por página`, false);
}
const informe = {fecha_utc: new Date().toISOString(), muestras: resultados, finalizada: true,
  navegador: await page.evaluate(() => navigator.userAgent),
  viewport: await page.evaluate(() => ({ancho: innerWidth, alto: innerHeight, dpr: devicePixelRatio})),
  metodologia: 'Entrada a semántica, dos requestAnimationFrame y captura completada; incluye debounce, protocolo y automatización. No equivale a latencia física de escritorio.'};
await page.evaluate(informe => { globalThis.__horizonte_medicion = informe; }, informe);
return informe;
}
