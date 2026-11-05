"""Casos de uso de comprobantes: emitir, consultar y reenviar a la OSE."""

from __future__ import annotations

import contextlib
from dataclasses import dataclass
from decimal import Decimal

from src.application.comandos import EmitirComprobanteCmd, LineaCmd
from src.application.errores import Conflicto, OseNoDisponible, OseRespuestaInvalida, RecursoNoEncontrado
from src.application.puertos import (
    ClienteOSE,
    FirmaDigital,
    GeneradorIdentificadores,
    GeneradorUBL,
    RegistroIdempotencia,
    Reloj,
    RepositorioComprobantes,
    RepositorioIdempotencia,
    RepositorioKardex,
    RepositorioMigraciones,
    RepositorioProductos,
    SecuenciaCorrelativos,
    UnidadDeTrabajo,
    ValidadorEsquemaUBL,
)
from src.domain.catalogos import (
    MotivoNotaCredito,
    SentidoMovimiento,
    TipoComprobante,
    TipoDocumentoPLE,
    TipoOperacionInventario,
)
from src.domain.comprobante import BorradorComprobante, Cliente, Comprobante, Emisor, EstadoComprobante, Linea
from src.domain.errores import ErrorDominio, UnidadMedidaInvalida
from src.domain.inventario import DocumentoSoporte, MigracionLegado, Producto
from src.domain.pagos import Cuota, FormaPago
from src.domain.tributos import CERO, ConfiguracionISC
from src.domain.valores import DocumentoIdentidad, NumeroComprobante, Serie


@dataclass(frozen=True, slots=True)
class ResultadoEmision:
    comprobante: Comprobante
    repetido: bool = False  # True si se devolvió el resultado de una solicitud idempotente previa


@dataclass(frozen=True, slots=True)
class _EfectoInventario:
    producto: Producto
    sentido: SentidoMovimiento
    tipo_operacion: TipoOperacionInventario
    cantidad: Decimal


class EnvioOse:
    """Envía un comprobante firmado y registra el resultado (CDR o fallo) en el agregado."""

    def __init__(self, *, ose: ClienteOSE, uow: UnidadDeTrabajo, comprobantes: RepositorioComprobantes,
                 inventario: _Inventario) -> None:
        self._ose = ose
        self._uow = uow
        self._comprobantes = comprobantes
        self._inventario = inventario

    def enviar(self, comprobante: Comprobante) -> None:
        """Lanza ``OseNoDisponible`` u ``OseRespuestaInvalida`` después de registrar el fallo."""
        comprobante.asegurar_envio_posible()
        try:
            cdr = self._ose.enviar(comprobante.nombre_archivo, comprobante.xml_firmado or b"")
            cdr.estado_resultante  # noqa: B018 - valida que el código sea un CDR y no una excepción
        except (OseNoDisponible, OseRespuestaInvalida):
            self._registrar_fallo(comprobante)
            raise
        except ErrorDominio as exc:
            self._registrar_fallo(comprobante)
            raise OseRespuestaInvalida(exc.mensaje) from exc

        with self._uow.transaccion():
            comprobante.registrar_cdr(cdr)
            if comprobante.estado is EstadoComprobante.RECHAZADO:
                self._inventario.revertir(comprobante)
            self._comprobantes.actualizar(comprobante)

    def _registrar_fallo(self, comprobante: Comprobante) -> None:
        with self._uow.transaccion():
            comprobante.registrar_envio_fallido()
            self._comprobantes.actualizar(comprobante)


class _Inventario:
    """Efectos de un comprobante en el Kardex y en los documentos legado."""

    def __init__(self, *, reloj: Reloj, kardex: RepositorioKardex, migraciones: RepositorioMigraciones,
                 ids: GeneradorIdentificadores, establecimiento: str) -> None:
        self._reloj = reloj
        self._kardex = kardex
        self._migraciones = migraciones
        self._ids = ids
        self._establecimiento = establecimiento

    def efectos(self, borrador: BorradorComprobante | Comprobante,
                productos: dict[int, Producto]) -> list[_EfectoInventario]:
        if borrador.tipo in (TipoComprobante.FACTURA, TipoComprobante.BOLETA):
            if borrador.documentos_legado:
                return []  # la salida física ya se registró al migrar el vale
            sentido, operacion = SentidoMovimiento.SALIDA, TipoOperacionInventario.VENTA
        elif isinstance(borrador.motivo, MotivoNotaCredito) and borrador.motivo.es_devolucion:
            sentido, operacion = SentidoMovimiento.ENTRADA, TipoOperacionInventario.ENTRADA_DEVOLUCION_CLIENTE
        else:
            return []
        return [
            _EfectoInventario(productos[ln.numero], sentido, operacion, ln.cantidad)
            for ln in borrador.lineas
            if ln.numero in productos
        ]

    def verificar(self, borrador: BorradorComprobante, efectos: list[_EfectoInventario]) -> None:
        acumulado: dict[str, Decimal] = {}
        for efecto in efectos:
            codigo = efecto.producto.codigo
            acumulado[codigo] = acumulado.get(codigo, CERO) + efecto.cantidad
            self._kardex.obtener(self._establecimiento, efecto.producto).verificar(
                fecha=borrador.fecha_emision, tipo_operacion=efecto.tipo_operacion,
                sentido=efecto.sentido, cantidad=acumulado[codigo],
            )

    def aplicar(self, comprobante: Comprobante, efectos: list[_EfectoInventario]) -> None:
        documento = self._documento(comprobante)
        for efecto in efectos:
            kardex = self._kardex.obtener(self._establecimiento, efecto.producto)
            kardex.registrar(
                id_movimiento=self._ids.siguiente("MOV"), fecha=comprobante.fecha_emision,
                tipo_operacion=efecto.tipo_operacion, sentido=efecto.sentido, cantidad=efecto.cantidad,
                documento=documento, glosa=f"{comprobante.tipo.descripcion} {comprobante.serie_numero}",
            )
            self._kardex.guardar(kardex)

    def revertir(self, comprobante: Comprobante) -> None:
        """Un comprobante rechazado no tiene validez: se compensa su movimiento (nunca se borra)."""
        for nro in comprobante.documentos_legado:
            migracion = self._migraciones.obtener(nro)
            if migracion is not None:
                migracion.revertir_facturacion()
                self._migraciones.guardar(migracion)
        documento = self._documento(comprobante)
        hoy = self._reloj.ahora().date()
        for movimiento in list(self._kardex.movimientos()):
            if movimiento.documento != documento:
                continue
            kardex = self._kardex.obtener(movimiento.establecimiento, movimiento.producto)
            inverso = (SentidoMovimiento.ENTRADA if movimiento.sentido is SentidoMovimiento.SALIDA
                       else SentidoMovimiento.SALIDA)
            kardex.registrar(
                id_movimiento=self._ids.siguiente("MOV"), fecha=max(hoy, kardex.movimientos[-1].fecha),
                tipo_operacion=TipoOperacionInventario.OTROS, sentido=inverso,
                cantidad=movimiento.entrada or movimiento.salida, documento=documento,
                glosa=f"Reversión: {comprobante.serie_numero} rechazado por la OSE",
            )
            self._kardex.guardar(kardex)

    @staticmethod
    def _documento(comprobante: Comprobante) -> DocumentoSoporte:
        return DocumentoSoporte(
            TipoDocumentoPLE.desde_comprobante(comprobante.tipo), str(comprobante.numero.serie),
            str(comprobante.numero.correlativo), comprobante.fecha_emision,
        )


class EmitirComprobante:
    def __init__(
        self,
        *,
        emisor: Emisor,
        plazo_envio_dias: int,
        reloj: Reloj,
        uow: UnidadDeTrabajo,
        secuencia: SecuenciaCorrelativos,
        comprobantes: RepositorioComprobantes,
        idempotencia: RepositorioIdempotencia,
        productos: RepositorioProductos,
        kardex: RepositorioKardex,
        migraciones: RepositorioMigraciones,
        ids: GeneradorIdentificadores,
        generador_ubl: GeneradorUBL,
        validador_xsd: ValidadorEsquemaUBL,
        firma: FirmaDigital,
        ose: ClienteOSE,
    ) -> None:
        self._emisor = emisor
        self._plazo = plazo_envio_dias
        self._reloj = reloj
        self._uow = uow
        self._secuencia = secuencia
        self._comprobantes = comprobantes
        self._idempotencia = idempotencia
        self._productos = productos
        self._migraciones = migraciones
        self._generador = generador_ubl
        self._validador = validador_xsd
        self._firma = firma
        self._inventario = _Inventario(reloj=reloj, kardex=kardex, migraciones=migraciones, ids=ids,
                                       establecimiento=emisor.codigo_establecimiento)
        self.envio = EnvioOse(ose=ose, uow=uow, comprobantes=comprobantes, inventario=self._inventario)

    def ejecutar(self, cmd: EmitirComprobanteCmd) -> ResultadoEmision:
        with self._uow.transaccion():
            previo = self._buscar_idempotente(cmd)
            if previo is not None:
                return ResultadoEmision(previo, repetido=True)

            ahora = self._reloj.ahora()
            fecha = cmd.fecha_emision or ahora.date()
            productos: dict[int, Producto] = {}
            lineas = tuple(self._linea(i, ln, fecha, productos) for i, ln in enumerate(cmd.lineas, start=1))
            referencia, acreditado = self._referencia(cmd)
            borrador = BorradorComprobante.preparar(
                tipo=cmd.tipo,
                serie=Serie(cmd.serie),
                fecha_emision=fecha,
                hora_emision=ahora.time().replace(microsecond=0),
                hoy=ahora.date(),
                plazo_dias=self._plazo,
                moneda=cmd.moneda,
                tipo_cambio=cmd.tipo_cambio,
                emisor=self._emisor,
                cliente=Cliente(
                    DocumentoIdentidad(cmd.cliente.tipo_documento, cmd.cliente.numero_documento.strip().upper()),
                    cmd.cliente.nombre.strip(),
                    cmd.cliente.direccion,
                ),
                lineas=lineas,
                documentos_legado=tuple(d.strip() for d in cmd.documentos_legado),
                referencia=referencia,
                motivo=cmd.motivo,
                sustento=cmd.sustento,
                total_notas_credito_previas=acreditado,
                forma_pago=FormaPago(cmd.forma_pago.tipo, tuple(Cuota(c.monto, c.fecha_vencimiento)
                                                                 for c in cmd.forma_pago.cuotas))
                if cmd.forma_pago else None,
            )
            vales = self._vales_legado(borrador, productos)
            efectos = self._inventario.efectos(borrador, productos)
            self._inventario.verificar(borrador, efectos)

            # Todas las reglas pasaron: recién ahora se consume un correlativo.
            comprobante = borrador.numerar(self._secuencia.siguiente(self._emisor.ruc, cmd.tipo, borrador.serie))
            xml = self._generador.generar(comprobante)
            self._validador.validar(xml, comprobante.tipo)
            firmado = self._firma.firmar(xml)
            self._validador.validar(firmado.xml, comprobante.tipo)
            comprobante.registrar_firma(firmado.xml, firmado.digest_value)

            self._comprobantes.agregar(comprobante)
            self._inventario.aplicar(comprobante, efectos)
            for vale in vales:
                vale.marcar_facturada(f"{comprobante.tipo.value}/{comprobante.serie_numero}")
                self._migraciones.guardar(vale)
            if cmd.clave_idempotencia:
                self._idempotencia.guardar(
                    cmd.clave_idempotencia,
                    RegistroIdempotencia(cmd.huella or "", comprobante.tipo, comprobante.serie_numero),
                )

        # El envío a la OSE va fuera de la transacción: es E/S remota y puede tardar o fallar.
        # Si falla, el comprobante queda PENDIENTE_ENVIO y se reintenta con ReenviarComprobante.
        with contextlib.suppress(OseNoDisponible, OseRespuestaInvalida):
            self.envio.enviar(comprobante)
        return ResultadoEmision(comprobante)

    # --- pasos -------------------------------------------------------------------------
    def _buscar_idempotente(self, cmd: EmitirComprobanteCmd) -> Comprobante | None:
        if not cmd.clave_idempotencia:
            return None
        registro = self._idempotencia.obtener(cmd.clave_idempotencia)
        if registro is None:
            return None
        if registro.huella != (cmd.huella or ""):
            raise Conflicto(
                f"La clave de idempotencia '{cmd.clave_idempotencia}' ya se usó con un contenido distinto "
                f"(comprobante {registro.serie_numero}).",
                codigo="ERR-IDEMPOTENCIA-CONFLICTO",
            )
        return self._comprobantes.obtener(registro.tipo, registro.serie_numero)

    def _linea(self, numero: int, cmd: LineaCmd, fecha, productos: dict[int, Producto]) -> Linea:
        if cmd.codigo_producto:
            producto = self._productos.obtener(cmd.codigo_producto)
            if producto is None:
                raise ErrorDominio(f"El producto '{cmd.codigo_producto}' no existe en el catálogo.",
                                   codigo="ERR-PRODUCTO-NO-EXISTE", campo=f"lineas[{numero - 1}].codigo_producto")
            if producto.unidad is not cmd.unidad_medida:
                raise UnidadMedidaInvalida(
                    f"El producto {producto.codigo} se controla en {producto.unidad.value} "
                    f"({producto.unidad.descripcion}); la línea usa {cmd.unidad_medida.value}.",
                    campo=f"lineas[{numero - 1}].unidad_medida",
                )
            productos[numero] = producto
        isc = None
        if cmd.isc is not None:
            isc = ConfiguracionISC(cmd.isc.sistema, cmd.isc.tasa, cmd.isc.monto_fijo, cmd.isc.precio_venta_publico)
        return Linea.calcular(
            numero=numero, codigo_producto=cmd.codigo_producto, descripcion=cmd.descripcion,
            unidad=cmd.unidad_medida, cantidad=cmd.cantidad, valor_unitario=cmd.valor_unitario,
            afectacion=cmd.afectacion_igv, isc=isc, aplica_icbper=cmd.aplica_icbper, fecha_emision=fecha,
        )

    def _referencia(self, cmd: EmitirComprobanteCmd) -> tuple[Comprobante | None, Decimal]:
        if cmd.referencia is None:
            return None, CERO
        numero = NumeroComprobante.parsear(cmd.referencia.serie_numero)
        referencia = self._comprobantes.obtener(cmd.referencia.tipo, str(numero))
        if referencia is None:
            raise ErrorDominio(
                f"El comprobante de referencia {cmd.referencia.tipo.value}/{numero} no existe.",
                codigo="ERR-REFERENCIA-NO-EXISTE", campo="referencia",
            )
        acreditado = sum(
            (n.totales.importe_total for n in self._comprobantes.notas_de(referencia)
             if n.tipo is TipoComprobante.NOTA_CREDITO and n.es_valido_tributariamente),
            CERO,
        )
        return referencia, acreditado

    def _vales_legado(self, borrador: BorradorComprobante, productos: dict[int, Producto]) -> list[MigracionLegado]:
        codigos_facturados = {p.codigo for p in productos.values()}
        vales = []
        for nro in borrador.documentos_legado:
            vale = self._migraciones.obtener(nro)
            if vale is None:
                raise ErrorDominio(f"El documento legado '{nro}' no ha sido migrado.",
                                   codigo="ERR-LEGADO-NO-MIGRADO", campo="documentos_legado")
            vale.asegurar_pendiente()
            if vale.movimiento.producto.codigo not in codigos_facturados:
                raise ErrorDominio(
                    f"El documento legado '{nro}' despachó {vale.movimiento.producto.codigo}, que no figura en "
                    "las líneas del comprobante.",
                    codigo="ERR-LEGADO-NO-CORRESPONDE", campo="documentos_legado",
                )
            vales.append(vale)
        return vales


class ConsultarComprobante:
    def __init__(self, *, comprobantes: RepositorioComprobantes) -> None:
        self._comprobantes = comprobantes

    def ejecutar(self, tipo: TipoComprobante, serie_numero: str) -> Comprobante:
        numero = NumeroComprobante.parsear(serie_numero)
        comprobante = self._comprobantes.obtener(tipo, str(numero))
        if comprobante is None:
            raise RecursoNoEncontrado(f"No existe el comprobante {tipo.value}/{numero}.",
                                      codigo="ERR-COMPROBANTE-NO-ENCONTRADO")
        return comprobante


class ReenviarComprobante:
    """Reintenta el envío de un comprobante PENDIENTE_ENVIO (por ejemplo, tras una caída de la OSE)."""

    def __init__(self, *, consultar: ConsultarComprobante, envio: EnvioOse) -> None:
        self._consultar = consultar
        self._envio = envio

    def ejecutar(self, tipo: TipoComprobante, serie_numero: str) -> Comprobante:
        comprobante = self._consultar.ejecutar(tipo, serie_numero)
        self._envio.enviar(comprobante)
        return comprobante
