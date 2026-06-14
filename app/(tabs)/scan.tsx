import { Feather } from '@expo/vector-icons';
import { CameraView, useCameraPermissions } from 'expo-camera';
import * as Haptics from 'expo-haptics';
import React, { useCallback, useRef, useState } from 'react';
import { ActivityIndicator, Pressable, StyleSheet, View } from 'react-native';
import { ScanResultSheet } from '../../components/ScanResultSheet';
import { AppText, Button, Overline } from '../../components/ui';
import { TextField } from '../../components/inputs';
import { fetchProduct } from '../../lib/openfoodfacts';
import { palette, radii, spacing } from '../../lib/theme';
import type { ScannedProduct } from '../../lib/types';

export default function Scan() {
  const [permission, requestPermission] = useCameraPermissions();
  const [loading, setLoading] = useState(false);
  const [product, setProduct] = useState<ScannedProduct | null>(null);
  const [notFound, setNotFound] = useState<string | null>(null);
  const [manual, setManual] = useState('');
  const lock = useRef(false);

  const lookup = useCallback(async (barcode: string) => {
    if (lock.current) return;
    lock.current = true;
    setLoading(true);
    setNotFound(null);
    void Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
    try {
      const result = await fetchProduct(barcode);
      if (result) setProduct(result);
      else setNotFound(barcode);
    } catch {
      setNotFound(barcode);
    } finally {
      setLoading(false);
    }
  }, []);

  const reset = () => {
    setProduct(null);
    setNotFound(null);
    lock.current = false;
  };

  // Permission not yet known.
  if (!permission) {
    return (
      <View style={styles.center}>
        <ActivityIndicator color={palette.glow} />
      </View>
    );
  }

  return (
    <View style={styles.root}>
      {permission.granted ? (
        <CameraView
          style={StyleSheet.absoluteFill}
          barcodeScannerSettings={{
            barcodeTypes: ['ean13', 'ean8', 'upc_a', 'upc_e', 'code128'],
          }}
          onBarcodeScanned={({ data }) => {
            if (!product && !loading) void lookup(data);
          }}
        />
      ) : (
        <View style={[StyleSheet.absoluteFill, styles.noCam]} />
      )}

      {/* Dark vignette + framing */}
      <View style={styles.overlay} pointerEvents="box-none">
        <View style={styles.topBar}>
          <Overline color={palette.ink}>Scan a barcode</Overline>
          <AppText variant="caption" color={palette.inkMuted} style={{ textAlign: 'center', marginTop: 4 }}>
            Point at a product barcode to grade it instantly
          </AppText>
        </View>

        <View style={styles.frame}>
          <Corner pos="tl" />
          <Corner pos="tr" />
          <Corner pos="bl" />
          <Corner pos="br" />
          {loading && (
            <View style={styles.scanning}>
              <ActivityIndicator color={palette.glow} />
              <AppText variant="caption" color={palette.glow}>Reading label…</AppText>
            </View>
          )}
        </View>

        <View style={styles.bottom}>
          {!permission.granted && (
            <View style={styles.permCard}>
              <Feather name="camera-off" size={22} color={palette.inkMuted} />
              <AppText variant="bodyMedium" style={{ textAlign: 'center' }}>
                Camera access needed to scan
              </AppText>
              <Button label="Enable camera" onPress={requestPermission} />
            </View>
          )}

          {notFound && (
            <View style={styles.permCard}>
              <Feather name="alert-circle" size={20} color={palette.warn} />
              <AppText variant="caption" color={palette.inkMuted} style={{ textAlign: 'center' }}>
                No match for {notFound} in the Open Food Facts database.
              </AppText>
              <Button label="Try again" variant="ghost" onPress={reset} />
            </View>
          )}

          {/* Manual entry fallback (also covers web / no camera) */}
          {!notFound && (
            <View style={styles.manualRow}>
              <View style={{ flex: 1 }}>
                <TextField
                  placeholder="Enter barcode manually"
                  keyboardType="numeric"
                  value={manual}
                  onChangeText={setManual}
                />
              </View>
              <Pressable
                style={styles.manualBtn}
                onPress={() => manual.length >= 6 && lookup(manual)}
              >
                <Feather name="search" size={20} color={palette.void} />
              </Pressable>
            </View>
          )}
        </View>
      </View>

      {product && <ScanResultSheet product={product} onClose={reset} />}
    </View>
  );
}

function Corner({ pos }: { pos: 'tl' | 'tr' | 'bl' | 'br' }) {
  const base: any = { position: 'absolute', width: 30, height: 30, borderColor: palette.glow };
  const map: Record<string, any> = {
    tl: { top: -1, left: -1, borderTopWidth: 3, borderLeftWidth: 3, borderTopLeftRadius: radii.md },
    tr: { top: -1, right: -1, borderTopWidth: 3, borderRightWidth: 3, borderTopRightRadius: radii.md },
    bl: { bottom: -1, left: -1, borderBottomWidth: 3, borderLeftWidth: 3, borderBottomLeftRadius: radii.md },
    br: { bottom: -1, right: -1, borderBottomWidth: 3, borderRightWidth: 3, borderBottomRightRadius: radii.md },
  };
  return <View style={[base, map[pos]]} />;
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: palette.void },
  center: { flex: 1, backgroundColor: palette.base, alignItems: 'center', justifyContent: 'center' },
  noCam: { backgroundColor: '#0B100E' },
  overlay: {
    flex: 1,
    justifyContent: 'space-between',
    paddingTop: 80,
    paddingBottom: 130,
    paddingHorizontal: spacing.xl,
    backgroundColor: 'rgba(6,10,9,0.45)',
  },
  topBar: { alignItems: 'center' },
  frame: {
    alignSelf: 'center',
    width: 260,
    height: 170,
    alignItems: 'center',
    justifyContent: 'center',
  },
  scanning: { alignItems: 'center', gap: spacing.sm },
  bottom: { gap: spacing.md },
  permCard: {
    backgroundColor: palette.surface,
    borderRadius: radii.lg,
    borderWidth: 1,
    borderColor: palette.hairline,
    padding: spacing.xl,
    alignItems: 'center',
    gap: spacing.md,
  },
  manualRow: { flexDirection: 'row', gap: spacing.sm, alignItems: 'center' },
  manualBtn: {
    width: 54,
    height: 54,
    borderRadius: radii.md,
    backgroundColor: palette.glow,
    alignItems: 'center',
    justifyContent: 'center',
  },
});
