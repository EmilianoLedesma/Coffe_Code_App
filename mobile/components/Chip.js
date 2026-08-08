import { TouchableOpacity, Text, StyleSheet } from 'react-native';
import { colors, typography, spacing, radii } from '../theme';

export function Chip({ label, selected = false, onPress }) {
  return (
    <TouchableOpacity
      onPress={onPress}
      activeOpacity={0.7}
      style={[styles.base, selected && styles.selected]}
    >
      <Text style={[styles.label, selected && styles.labelSelected]}>{label}</Text>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  base: {
    minHeight: 44,
    justifyContent: 'center',
    borderRadius: radii.r999,
    borderWidth: 1,
    borderColor: colors.borderVisible,
    backgroundColor: colors.surface,
    paddingVertical: spacing.sm,
    paddingHorizontal: spacing.lg,
    marginRight: spacing.sm,
    marginBottom: spacing.sm,
  },
  selected: {
    backgroundColor: colors.primaryTint,
    borderColor: colors.primary,
  },
  label: {
    fontSize: typography.size.md,
    fontWeight: typography.weight.medium,
    color: colors.textSecondary,
  },
  labelSelected: {
    color: colors.primary,
    fontWeight: typography.weight.bold,
  },
});
