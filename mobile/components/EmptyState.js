import { View, Text, StyleSheet } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { colors, typography, spacing } from '../theme';

export function EmptyState({ icon = 'file-tray-outline', message }) {
  return (
    <View style={styles.container}>
      <Ionicons name={icon} size={40} color={colors.textTertiary} />
      <Text style={styles.message}>{message}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: spacing.huge,
  },
  message: {
    marginTop: spacing.md,
    fontSize: typography.size.lg,
    color: colors.textSecondary,
    textAlign: 'center',
  },
});
