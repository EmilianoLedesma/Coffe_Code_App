import { View, Text, TextInput, StyleSheet } from 'react-native';
import { colors, typography, spacing, radii } from '../theme';

export function Input({ label, value, onChangeText, placeholder, keyboardType, secureTextEntry, error, multiline = false, ...inputProps }) {
  return (
    <View style={styles.container}>
      {label ? <Text style={styles.label}>{label}</Text> : null}
      <TextInput
        value={value}
        onChangeText={onChangeText}
        placeholder={placeholder}
        placeholderTextColor={colors.textTertiary}
        keyboardType={keyboardType}
        secureTextEntry={secureTextEntry}
        multiline={multiline}
        style={[styles.input, multiline && styles.multiline, error && styles.inputError]}
        {...inputProps}
      />
      {error ? (
        <View style={styles.errorBanner}>
          <Text style={styles.errorText}>{error}</Text>
        </View>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    marginBottom: spacing.lg,
  },
  label: {
    fontSize: typography.eyebrow.fontSize,
    fontWeight: typography.eyebrow.fontWeight,
    letterSpacing: typography.eyebrow.letterSpacing,
    textTransform: typography.eyebrow.textTransform,
    color: colors.textSecondary,
    marginBottom: spacing.xs,
  },
  input: {
    height: 46,
    borderWidth: 1,
    borderColor: colors.borderVisible,
    borderRadius: radii.r12,
    paddingHorizontal: spacing.lg,
    fontSize: typography.size.lg,
    color: colors.textPrimary,
    backgroundColor: colors.surface,
  },
  multiline: {
    height: 100,
    paddingTop: spacing.md,
    textAlignVertical: 'top',
  },
  inputError: {
    borderColor: colors.danger,
  },
  errorBanner: {
    backgroundColor: colors.dangerTint,
    borderWidth: 1,
    borderColor: 'rgba(192,57,43,0.3)',
    borderRadius: radii.r8,
    paddingVertical: spacing.sm,
    paddingHorizontal: spacing.md,
    marginTop: spacing.xs,
  },
  errorText: {
    color: colors.danger,
    fontSize: typography.size.md,
  },
});
