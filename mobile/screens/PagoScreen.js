import React, { useCallback, useState } from 'react';
import { View, Text, StyleSheet, ScrollView, ActivityIndicator } from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { getPedido } from '../api/pedidos_caja';
import { getTicket } from '../api/tickets';
import { registrarVenta } from '../api/caja';
import { ApiError } from '../api/client';
import { Button } from '../components/Button';
import { Card } from '../components/Card';
import { Chip } from '../components/Chip';
import { Input } from '../components/Input';
import { colors, typography, spacing, radii } from '../theme';

const METODOS = [
  { key: 'Efectivo', label: 'Efectivo' },
  { key: 'Tarjeta débito', label: 'Tarjeta débito' },
  { key: 'Tarjeta crédito', label: 'Tarjeta crédito' },
  { key: 'Transferencia', label: 'Transferencia' },
];

export default function PagoScreen({ route, navigation }) {
  const { ticketId, pedidoId, numeroMesa } = route.params;

  const [pedido, setPedido] = useState(null);
  const [ticket, setTicket] = useState(null);
  const [loading, setLoading] = useState(true);
  const [metodoPago, setMetodoPago] = useState('');
  const [monto, setMonto] = useState('');
  const [procesando, setProcesando] = useState(false);
  const [error, setError] = useState('');
  const [resultado, setResultado] = useState(null);

  const cargar = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [pedidoData, ticketData] = await Promise.all([
        getPedido(pedidoId),
        getTicket(ticketId).catch(() => null),
      ]);
      setPedido(pedidoData);
      setTicket(ticketData);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo cargar el pedido');
    } finally {
      setLoading(false);
    }
  }, [pedidoId, ticketId]);

  useFocusEffect(
    useCallback(() => {
      cargar();
    }, [cargar])
  );

  const pagar = async () => {
    if (!metodoPago) {
      setError('Selecciona un método de pago');
      return;
    }
    if (!monto || Number(monto) <= 0) {
      setError('Ingresa el monto recibido');
      return;
    }

    setProcesando(true);
    setError('');
    try {
      const ticketPagado = await registrarVenta({ ticketId, metodoPago, monto: Number(monto) });
      setResultado(ticketPagado);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo procesar el pago');
    } finally {
      setProcesando(false);
    }
  };

  if (loading && !pedido) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color={colors.primary} />
      </View>
    );
  }

  if (error && !pedido) {
    return (
      <View style={styles.center}>
        <View style={styles.errorBanner}>
          <Text style={styles.errorText}>{error}</Text>
        </View>
        <Button variant="primary" label="Reintentar" onPress={cargar} />
      </View>
    );
  }

  if (resultado) {
    const fecha = new Date(resultado.fecha_emision);
    return (
      <ScrollView style={styles.container} contentContainerStyle={{ paddingBottom: spacing.xxl }}>
        <View style={styles.receipt}>
          <Text style={styles.receiptHeader}>COFFEE CODE</Text>
          <Text style={styles.receiptSub}>Folio #{resultado.id} — Mesa {numeroMesa ?? resultado.id_mesa}</Text>
          <Text style={styles.receiptSub}>{fecha.toLocaleString()}</Text>

          <View style={styles.dashedLine} />

          {pedido?.detalle.map((item) => (
            <View key={item.id} style={styles.receiptRow}>
              <Text style={styles.receiptItem} numberOfLines={1}>
                {item.cantidad}x {item.producto.nombre}
              </Text>
              <Text style={styles.receiptAmount}>
                ${(item.cantidad * Number(item.precio_unitario)).toFixed(2)}
              </Text>
            </View>
          ))}

          <View style={styles.dashedLine} />

          <View style={styles.receiptRow}>
            <Text style={styles.receiptItem}>Subtotal</Text>
            <Text style={styles.receiptAmount}>${resultado.subtotal}</Text>
          </View>
          <View style={styles.receiptRow}>
            <Text style={styles.receiptItem}>IVA</Text>
            <Text style={styles.receiptAmount}>${resultado.iva}</Text>
          </View>
          <View style={styles.receiptRow}>
            <Text style={styles.receiptTotalLabel}>TOTAL</Text>
            <Text style={styles.receiptTotalAmount}>${resultado.total}</Text>
          </View>

          <View style={styles.dashedLine} />

          <View style={styles.receiptRow}>
            <Text style={styles.receiptItem}>Método</Text>
            <Text style={styles.receiptAmount}>{resultado.pago.metodo.nombre}</Text>
          </View>
          <View style={styles.receiptRow}>
            <Text style={styles.receiptItem}>Recibido</Text>
            <Text style={styles.receiptAmount}>${resultado.pago.monto_recibido}</Text>
          </View>
          <View style={styles.receiptRow}>
            <Text style={styles.receiptItem}>Cambio</Text>
            <Text style={styles.receiptAmount}>${resultado.pago.cambio}</Text>
          </View>
        </View>

        <Button variant="primary" label="Volver a Caja" onPress={() => navigation.navigate('Caja')} />
      </ScrollView>
    );
  }

  return (
    <ScrollView style={styles.container} contentContainerStyle={{ paddingBottom: spacing.xxl }}>

      <Text style={styles.title}>Procesar Pago</Text>

      <Card>
        <Text style={styles.subtitle}>Mesa {numeroMesa ?? pedido.id_mesa} — Pedido #{pedido.id}</Text>

        {pedido.detalle.map((item) => (
          <Text key={item.id} style={styles.text}>
            {item.producto.nombre} x{item.cantidad} — ${item.precio_unitario}
          </Text>
        ))}

        {ticket ? (
          <>
            <Text style={styles.totalLine}>Subtotal: ${ticket.subtotal}</Text>
            <Text style={styles.totalLine}>IVA: ${ticket.iva}</Text>
            <Text style={styles.total}>Total a cobrar: ${ticket.total}</Text>
          </>
        ) : null}
      </Card>

      <Text style={styles.subtitle}>Método de pago</Text>

      <View style={styles.row}>
        {METODOS.map((m) => (
          <Chip
            key={m.key}
            label={m.label}
            selected={metodoPago === m.key}
            onPress={() => !procesando && setMetodoPago(m.key)}
          />
        ))}
      </View>

      <Input
        label="Monto recibido"
        keyboardType="numeric"
        placeholder="Ej. 200"
        value={monto}
        onChangeText={setMonto}
        editable={!procesando}
      />

      {error ? (
        <View style={styles.errorBanner}>
          <Text style={styles.errorText}>{error}</Text>
        </View>
      ) : null}

      <Button
        variant="primary"
        label="Confirmar y Pagar"
        onPress={pagar}
        loading={procesando}
        disabled={procesando}
      />

    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.background, padding: spacing.lg },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center', padding: spacing.xl },
  title: {
    fontSize: typography.size.xxl,
    fontWeight: typography.weight.bold,
    color: colors.textPrimary,
    marginBottom: spacing.lg,
  },
  subtitle: {
    fontSize: typography.size.xl,
    fontWeight: typography.weight.semibold,
    color: colors.textPrimary,
    marginTop: spacing.md,
    marginBottom: spacing.sm,
  },
  text: { fontSize: typography.size.lg, color: colors.textPrimary },
  totalLine: { fontSize: typography.size.md, color: colors.textSecondary, marginTop: spacing.xs },
  total: {
    fontSize: typography.size.xl,
    fontWeight: typography.weight.bold,
    color: colors.textPrimary,
    marginTop: spacing.sm,
  },
  errorBanner: {
    backgroundColor: colors.dangerTint,
    borderWidth: 1,
    borderColor: 'rgba(192,57,43,0.3)',
    borderRadius: radii.r8,
    paddingVertical: spacing.sm,
    paddingHorizontal: spacing.md,
    marginBottom: spacing.md,
  },
  errorText: { color: colors.danger, fontSize: typography.size.md },
  row: { flexDirection: 'row', flexWrap: 'wrap', marginBottom: spacing.md },
  receipt: {
    backgroundColor: colors.surface,
    borderRadius: radii.r12,
    padding: spacing.lg,
    marginBottom: spacing.lg,
  },
  receiptHeader: {
    fontSize: typography.size.xl,
    fontWeight: typography.weight.bold,
    color: colors.textPrimary,
    textAlign: 'center',
    letterSpacing: 1,
  },
  receiptSub: {
    fontSize: typography.size.sm,
    color: colors.textSecondary,
    textAlign: 'center',
    marginTop: 2,
  },
  dashedLine: {
    borderBottomWidth: 1,
    borderStyle: 'dashed',
    borderColor: colors.borderSubtle,
    marginVertical: spacing.md,
  },
  receiptRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: spacing.xs,
  },
  receiptItem: { fontSize: typography.size.md, color: colors.textPrimary, flex: 1, marginRight: spacing.sm },
  receiptAmount: { fontSize: typography.size.md, color: colors.textPrimary },
  receiptTotalLabel: { fontSize: typography.size.lg, fontWeight: typography.weight.bold, color: colors.textPrimary },
  receiptTotalAmount: { fontSize: typography.size.lg, fontWeight: typography.weight.bold, color: colors.textPrimary },
});
