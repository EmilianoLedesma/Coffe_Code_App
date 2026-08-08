import { View, Text, StyleSheet } from 'react-native';
import { colors, typography, spacing, radii } from '../theme';

const TONE_MAP = {
  success: { fg: colors.success, bg: colors.successTint },
  warning: { fg: colors.warning, bg: colors.warningTint },
  danger: { fg: colors.danger, bg: colors.dangerTint },
  info: { fg: colors.info, bg: colors.infoTint },
  neutral: { fg: colors.textSecondary, bg: colors.borderSubtle },
};

export function Badge({ label, tone = 'neutral' }) {
  const { fg, bg } = TONE_MAP[tone] || TONE_MAP.neutral;

  return (
    <View style={[styles.container, { backgroundColor: bg }]}>
      <View style={[styles.dot, { backgroundColor: fg }]} />
      <Text style={[styles.label, { color: fg }]}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'center',
    alignSelf: 'flex-start',
    borderRadius: radii.r999,
    paddingVertical: spacing.xs / 2,
    paddingHorizontal: spacing.md,
  },
  dot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    marginRight: spacing.xs,
  },
  label: {
    fontSize: typography.size.sm,
    fontWeight: typography.weight.bold,
    textTransform: 'uppercase',
    letterSpacing: 0.3,
  },
});
