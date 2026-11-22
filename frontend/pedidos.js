/* SIGEP Fase 4: pedidos y pagos. Las autorizaciones verdaderas están en Django. */
(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const money = n => Number(n || 0).toLocaleString('es-MX', {style:'currency',currency:'MXN'});
  const fecha = d => d ? new Date(d).toLocaleString('es-MX', {dateStyle:'medium',timeStyle:'short'}) : '—';
  const estados = {PENDIENTE:'Pendiente',CONFIRMADO:'Confirmado',EN_PREPARACION:'En preparación',LISTO:'Listo para entregar',ENTREGADO:'Entregado',CANCELADO:'Cancelado'};
  const siguientes = {
    ADMIN:{PENDIENTE:['CONFIRMADO','CANCELADO'],CONFIRMADO:['EN_PREPARACION','CANCELADO'],EN_PREPARACION:['LISTO'],LISTO:['ENTREGADO']},
    VENTAS:{PENDIENTE:['CONFIRMADO','CANCELADO'],CONFIRMADO:['CANCELADO'],LISTO:['ENTREGADO']},
    REPOSTERO:{CONFIRMADO:['EN_PREPARACION'],EN_PREPARACION:['LISTO']}
  };
  let request = null, rol = null, usuario = null, pedidos = [], productos = [], clientes = [], abierto = null;
  let consultaActual = 0;
  const el = (tag, className='', text='') => {
    const n = document.createElement(tag); if(className) n.className = className; n.textContent = text; return n;
  };
  const aviso = (id, msg, error = false) => {
    $(id).textContent = msg;
    $(id).hidden = !msg;
    $(id).className = 'pedidos-alerta ' + (error ? 'pedidos-error':'pedidos-ok');
  };
  const puedeCrear = () => ['ADMIN','VENTAS','CLIENTE'].includes(rol);
  const puedeCobrar = () => ['ADMIN','VENTAS'].includes(rol);

  async function iniciar({usuario: u, request: r}) {
    usuario = u; request = r; rol = u.is_superuser ? 'ADMIN' : u.rol?.codigo;
    $('pedidos-cliente-panel').hidden = rol !== 'CLIENTE';
    $('pedidos-produccion-panel').hidden = rol !== 'REPOSTERO';
    $('pedido-cliente-grupo').hidden = rol === 'CLIENTE';
    if (rol === 'CLIENTE' || rol === 'REPOSTERO') $('session-panel').classList.add('pedidos-sesion-ancha');
    await actualizar();
  }

  async function actualizar() {
    if (!request) return;
    const serial = ++consultaActual;
    const estado = rol === 'ADMIN' || rol === 'VENTAS' ? $('pedidos-filtro-estado').value : '';
    try {
      const lista = await request('/pedidos/' + (estado ? '?estado=' + encodeURIComponent(estado) : ''));
      if(serial !== consultaActual) return;
      pedidos = Array.isArray(lista) ? lista : (lista.results || []);
      pintar();
    } catch(err) {
      if(serial !== consultaActual) return;
      const id = ['ADMIN','VENTAS'].includes(rol) ? 'pedidos-admin-aviso' : rol === 'CLIENTE' ? 'pedidos-cliente-aviso' : 'pedidos-produccion-aviso';
      aviso(id, err.message, true);
    }
  }

  function pintar() {
    if (rol === 'CLIENTE') return pintarTarjetas('pedidos-cliente-lista', 'pedidos-cliente-aviso');
    if (rol === 'REPOSTERO') return pintarTarjetas('pedidos-produccion-lista','pedidos-produccion-aviso');
    if (!['ADMIN','VENTAS'].includes(rol)) return;
    const tabla = $('pedidos-tabla'); tabla.replaceChildren();
    $('pedidos-numero').textContent = pedidos.length;
    $('pedidos-pendientes').textContent = pedidos.filter(p => p.estado==='PENDIENTE').length;
    $('pedidos-por-entregar').textContent = pedidos.filter(p=>['CONFIRMADO','EN_PREPARACION','LISTO'].includes(p.estado)).length;
    for(const p of pedidos) {
      const tr=el('tr');
      for(const texto of [p.folio,p.cliente_nombre,fecha(p.fecha_entrega),money(p.total),money(p.saldo),estados[p.estado]||p.estado]) tr.appendChild(el('td','',texto));
      const c=el('td'); const b=el('button','sigep-action sigep-action-edit','Ver detalle');
      b.type='button'; b.addEventListener('click',()=>mostrarDetalle(p.id)); c.appendChild(b); tr.appendChild(c); tabla.appendChild(tr);
    }
    $('pedidos-tabla-vacia').hidden = pedidos.length>0;
    aviso('pedidos-admin-aviso','');
  }

  function pintarTarjetas(id, feedbackId) {
    const box=$(id); box.replaceChildren();
    for(const p of pedidos) {
      const card=el('article','pedidos-card');
      const head=el('div','pedidos-card-head');
      head.append(el('strong','',p.folio),el('span','pedidos-estado',estados[p.estado]||p.estado));
      card.appendChild(head);
      card.append(el('p','','Entrega: '+fecha(p.fecha_entrega)));
      if (rol !== 'REPOSTERO') card.append(el('p','','Total: '+money(p.total)+' · Saldo: '+money(p.saldo)));
      else card.append(el('p','',`${p.detalles.length} líneas de producto`));
      const b=el('button','sigep-button sigep-button-outline','Ver pedido'); b.type='button'; b.addEventListener('click',()=>mostrarDetalle(p.id));
      card.appendChild(b); box.appendChild(card);
    }
    if (!pedidos.length) box.appendChild(el('p','pedidos-sin-resultados','No hay pedidos para mostrar.'));
    aviso(feedbackId,'');
  }

  async function abrirNuevo() {
    if(!puedeCrear()) return;
    $('pedido-nuevo-form').reset(); aviso('pedido-nuevo-aviso',''); $('pedido-lineas').replaceChildren();
    $('pedido-cliente-grupo').hidden = rol==='CLIENTE';
    try {
      const resp = await fetch('/api/catalogo/productos/', {cache:'no-store'});
      if(!resp.ok) throw new Error('No fue posible cargar el catálogo.');
      const data=await resp.json(); productos=Array.isArray(data)?data:(data.results||[]);
      if(!productos.length) throw new Error('Aún no hay productos activos para solicitar.');
      if(rol!=='CLIENTE') {
        const resultado=await request('/clientes/?activo=true'); clientes=Array.isArray(resultado)?resultado:(resultado.results||[]);
        const select=$('pedido-cliente'); select.replaceChildren(new Option('Selecciona cliente',''));
        for(const c of clientes) select.add(new Option(`${c.nombre} ${c.apellidos} · ${c.telefono||c.correo||c.id}`,String(c.id)));
        if(!clientes.length) throw new Error('Primero registra un cliente activo en el módulo Clientes.');
      }
      // Minimo mañana; se respeta la hora local para crear ISO con toISOString.
      const manana = new Date(Date.now()+24*60*60*1000);
      const ajuste = new Date(manana.getTime()-manana.getTimezoneOffset()*60000).toISOString().slice(0,16);
      $('pedido-fecha-entrega').value=ajuste;
      anadirLinea(); $('pedido-dialog').showModal();
    } catch(e) {
      const id=rol==='CLIENTE'?'pedidos-cliente-aviso':'pedidos-admin-aviso'; aviso(id,e.message,true);
    }
  }

  function anadirLinea() {
    const cont=$('pedido-lineas');
    if(cont.children.length>=20) return aviso('pedido-nuevo-aviso','Máximo 20 líneas por pedido.',true);
    const row=el('div','pedidos-linea');
    const select=el('select'); select.required=true; select.setAttribute('aria-label','Producto');
    select.add(new Option('Selecciona producto',''));
    productos.forEach(p=>select.add(new Option(`${p.nombre} · ${money(p.precio_base)}`,String(p.id))));
    const cant=el('input'); cant.type='number'; cant.min='1'; cant.max='100'; cant.step='1'; cant.value='1'; cant.required=true; cant.setAttribute('aria-label','Cantidad');
    const nota=el('input'); nota.placeholder='Personalización (opcional)'; nota.maxLength=500; nota.setAttribute('aria-label','Personalización');
    const quitar=el('button','sigep-button sigep-button-outline','Quitar'); quitar.type='button'; quitar.addEventListener('click',()=>{row.remove(); calcularTotal();});
    select.addEventListener('change',calcularTotal); cant.addEventListener('input',calcularTotal);
    row.append(select,cant,nota,quitar); cont.appendChild(row); calcularTotal();
  }

  function calcularTotal() {
    let total=0;
    for(const row of $('pedido-lineas').children) {
      const [select,cant]=row.querySelectorAll('select, input');
      const p=productos.find(p=>String(p.id)===select.value);
      total+= (p?Number(p.precio_base):0) * (Number(cant.value)||0);
    }
    $('pedido-total-estimado').textContent=money(total)+' (estimado;)';
  }

  async function guardarNuevo(ev) {
    ev.preventDefault();
    const detalles=[];
    for(const row of $('pedido-lineas').children) {
      const select=row.querySelector('select'), inputs=row.querySelectorAll('input');
      if(!select.value || !Number.isInteger(Number(inputs[0].value)) || Number(inputs[0].value)<1) return aviso('pedido-nuevo-aviso','Revisa los productos y cantidades.',true);
      detalles.push({producto_id:Number(select.value),cantidad:Number(inputs[0].value),personalizacion:inputs[1].value.trim()});
    }
    if(!detalles.length) return aviso('pedido-nuevo-aviso','Agrega por lo menos un producto.',true);
    const local=$('pedido-fecha-entrega').value;
    const date=new Date(local);
    if(!local || isNaN(date.getTime()) || date<=new Date()) return aviso('pedido-nuevo-aviso','Selecciona una fecha de entrega futura.',true);
    const datos={fecha_entrega:date.toISOString(),observaciones:$('pedido-observaciones').value.trim(),detalles};
    if(rol!=='CLIENTE') {
      if(!$('pedido-cliente').value) return aviso('pedido-nuevo-aviso','Selecciona el cliente.',true);
      datos.cliente_id=Number($('pedido-cliente').value);
    }
    const btn=$('pedido-guardar'); btn.disabled=true;
    try {
      const creado=await request('/pedidos/','POST',datos);
      $('pedido-dialog').close();
      await actualizar(); mostrarDetalle(creado.id);
    } catch(e) { aviso('pedido-nuevo-aviso',e.message,true); }
    finally {btn.disabled=false;}
  }

  async function mostrarDetalle(id) {
    if(!request) return;
    try {
      const p=await request(`/pedidos/${id}/`);
      abierto=p; $('pedido-detalle-folio').textContent=p.folio;
      const wrap=$('pedido-detalle-contenido'); wrap.replaceChildren();
      const resumen=el('div','pedidos-resumen');
      for(const [l,v] of [['Cliente',p.cliente_nombre],['Estado',estados[p.estado]||p.estado],['Entrega',fecha(p.fecha_entrega)],['Total',money(p.total)],['Pagado',money(p.pagado)],['Saldo',money(p.saldo)]]) {
        const par=el('p');par.append(el('strong','',l+': '),el('span','',v));resumen.appendChild(par);
      }
      if(p.observaciones) resumen.append(el('p','','Observaciones: '+p.observaciones));
      wrap.appendChild(resumen);
      const titulo=el('h3','','Productos');wrap.appendChild(titulo);
      const lista=el('ul','pedidos-detalle-lista');
      for(const linea of p.detalles) {
        const li=el('li','',`${linea.cantidad} × ${linea.nombre_producto} · ${money(linea.subtotal)}`);
        if(linea.personalizacion) li.appendChild(el('small','',`Personalización: ${linea.personalizacion}`));
        lista.appendChild(li);
      }
      wrap.appendChild(lista);
      if(rol!=='REPOSTERO') {
        wrap.appendChild(el('h3','','Pagos registrados'));
        const pagos=el('ul','pedidos-detalle-lista');
        if(!p.pagos.length) pagos.appendChild(el('li','','Aún no hay pagos registrados.'));
        for(const pg of p.pagos) pagos.appendChild(el('li','',`${fecha(pg.fecha_pago)} · ${money(pg.monto)} · ${pg.metodo}${pg.referencia?' · '+pg.referencia:''}`));
        wrap.appendChild(pagos);
      }
      $('pedido-estado-acciones').replaceChildren();
      const opciones=siguientes[rol]?.[p.estado]||[];
      for(const opcion of opciones) {
        if(opcion==='CANCELADO' && Number(p.pagado)>0) continue;
        const b=el('button','sigep-button sigep-button-outline',estados[opcion]);
        b.type='button'; b.addEventListener('click',()=>cambiarEstado(p.id,opcion)); $('pedido-estado-acciones').appendChild(b);
      }
      const formulario=$('pedido-pago-form'); formulario.hidden=!puedeCobrar() || Number(p.saldo)<=0 || p.estado==='CANCELADO';
      formulario.reset();
      $('pedido-pago-monto').max=String(p.saldo);
      aviso('pedido-detalle-aviso','');
      $('pedido-detalle-dialog').showModal();
    } catch(e) {
      const id=rol==='CLIENTE'?'pedidos-cliente-aviso':rol==='REPOSTERO'?'pedidos-produccion-aviso':'pedidos-admin-aviso';
      aviso(id,e.message,true);
    }
  }

  async function cambiarEstado(id,nuevo) {
    if(!confirm(`¿Cambiar el pedido a "${estados[nuevo]}"?`)) return;
    try {
      await request(`/pedidos/${id}/estado/`,'PATCH',{estado:nuevo});
      $('pedido-detalle-dialog').close(); await actualizar();
    } catch(e) {aviso('pedido-detalle-aviso',e.message,true);}
  }

  async function guardarPago(ev) {
    ev.preventDefault();
    if(!abierto || !puedeCobrar()) return;
    const b=$('pedido-pago-guardar'); b.disabled=true;
    try {
      await request(`/pedidos/${abierto.id}/pagos/`,'POST',{
        monto:$('pedido-pago-monto').value, metodo:$('pedido-pago-metodo').value,
        referencia:$('pedido-pago-referencia').value.trim()
      });
      const id=abierto.id; $('pedido-detalle-dialog').close(); await actualizar(); await mostrarDetalle(id);
    } catch(e){aviso('pedido-detalle-aviso',e.message,true);}
    finally{b.disabled=false;}
  }

  function detener() {
    request=null;usuario=null;rol=null;pedidos=[];productos=[];clientes=[];abierto=null;consultaActual++;
    $('pedidos-cliente-panel').hidden=true; $('pedidos-produccion-panel').hidden=true;
    $('session-panel').classList.remove('pedidos-sesion-ancha');
    if($('pedido-dialog').open) $('pedido-dialog').close();
    if($('pedido-detalle-dialog').open) $('pedido-detalle-dialog').close();
  }

  $('pedidos-nuevo-admin').addEventListener('click',abrirNuevo);
  $('pedidos-nuevo-cliente').addEventListener('click',abrirNuevo);
  $('pedidos-refrescar').addEventListener('click',actualizar);
  $('pedidos-actualizar-cliente').addEventListener('click',actualizar);
  $('pedidos-actualizar-produccion').addEventListener('click',actualizar);
  $('pedidos-filtro-estado').addEventListener('change',actualizar);
  $('pedido-anadir-producto').addEventListener('click',anadirLinea);
  $('pedido-nuevo-form').addEventListener('submit',guardarNuevo);
  $('pedido-cerrar').addEventListener('click',()=> $('pedido-dialog').close());
  $('pedido-detalle-cerrar').addEventListener('click',()=> $('pedido-detalle-dialog').close());
  $('pedido-pago-form').addEventListener('submit',guardarPago);
  window.SIGEPPedidos={iniciar,actualizar,detener};
})();
