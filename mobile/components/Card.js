import { View, TouchableOpacity, StyleSheet } from 'react-native';
import { colors, spacing, radii, shadows } from '../theme';

export function Card({ children, size = 'default', style, onPress }) {
  const Container = onPress ? TouchableOpacity : View;
  const extraProps = onPress ? { activeOpacity: 0.85 } : {};

  return (
    <Container onPress={onPress} {...extraProps} style={[styles.base, size === 'hero' && styles.hero, style]}>
      {children}
    </Container>
  );
}

const styles = StyleSheet.create({
  base: {
    backgroundColor: colors.surface,
    borderRadius: radii.r12,
    padding: spacing.lg,
    ...shadows.xs,
  },
  hero: {
    borderRadius: radii.r20,
    padding: spacing.xl,
  },
});
