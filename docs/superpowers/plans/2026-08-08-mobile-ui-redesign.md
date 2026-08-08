# Mobile UI Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace Coffee Code mobile's 15 independent, ad-hoc `StyleSheet` blocks with a shared design system (tokens + reusable components), restyled in a coffee-appropriate palette using the structural/geometric language of the `SWAY POO/MockupsSwayMobile` reference project (rounded cards, soft tinted shadows, pill chips/badges, Ionicons outline/filled, eyebrow labels) — pure visual layer change, zero navigation/data/logic changes.

**Architecture:** `mobile/theme/{colors,typography,spacing}.js` define design tokens. `mobile/components/{Button,Card,Input,Badge,Chip,ListItem,EmptyState}.js` are thin presentational wrappers reading those tokens (the native stack header, restyled in Task 3, covers screen-header needs — no separate `ScreenHeader` component). All 15 screens are migrated onto tokens+components, screen by role group, after foundation + `App.js` header restyle land first.

**Tech Stack:** React Native (Expo SDK 54), `@expo/vector-icons` (Ionicons) — new dependency, otherwise zero new packages. No styling library, no UI kit, no custom fonts, no navigation restructure.

## Global Constraints

- **No navigation logic changes.** Single stack navigator (`@react-navigation/native-stack`) stays exactly as is — same route names, same `Stack.Screen` registrations, same role-gating logic in `HomeScreen.js`. Only `screenOptions`/header *styling* changes.
- **No data/API/WebSocket logic changes.** Every existing `useFocusEffect`, `useState`, API call (`mobile/api/*.js`), and WS subscription (`connectToChannel` usage in `DetalleScreen.js`/`ColaPedidosScreen.js`/`CajaScreen.js`) must be byte-identical after a screen's restyle — only the returned JSX's markup/styling changes.
- **No dark mode.** Light-only tokens, matching the Sway reference (which also has none).
- **No custom font loading.** System default font, weight-differentiated only.
- **Color values, exactly as specified in Task 1** — do not invent alternate hex values mid-implementation.
- **Radii/shadow scale, exactly as specified in Task 1** — reuse the named tokens (`radii.r12`, `shadows.xs`, etc), never a raw inline number that duplicates a token value.
- Seed test credentials for manual reference only (no live device this session): `mesero@coffeecode.com`/`Mesero123!`, `cocinero@coffeecode.com`/`Cocinero123!`, `cajero@coffeecode.com`/`Cajero123!`.

---

### Task 1: Design tokens (`mobile/theme/`)

**Files:**
- Create: `mobile/theme/colors.js`
- Create: `mobile/theme/typography.js`
- Create: `mobile/theme/spacing.js`
- Create: `mobile/theme/index.js` (barrel re-export)

**Interfaces:**
- Produces: `colors` (object, from `colors.js`), `typography` (object, from `typography.js`), `spacing`/`radii`/`shadows` (objects, from `spacing.js`). All re-exported from `theme/index.js` so every later task imports via `import { colors, typography, spacing, radii, shadows } from '../theme'` (or relative path from `components/`/`screens/`).

- [ ] **Step 1: Create `mobile/theme/colors.js`**

```js
export const colors = {
  primary: '#3C2415',
  primaryDark: '#2A1810',
  primaryTint: 'rgba(60,36,21,0.08)',
  secondary: '#C77D33',
  secondaryTint: 'rgba(199,125,51,0.10)',

  background: '#FAF6F1',
  surface: '#FFFFFF',

  textPrimary: '#2B1B12',
  textSecondary: '#6B5A48',
  textTertiary: '#C4B8AB',
  textOnPrimary: '#FFFFFF',

  borderSubtle: 'rgba(43,27,18,0.08)',
  borderVisible: '#E4DACD',

  success: '#2E7D4F',
  successTint: '#E8F5EC',
  warning: '#8F5A00',
  warningTint: '#FDF3E2',
  danger: '#C0392B',
  dangerTint: '#FBEAE8',
  info: '#2E6B8C',
  infoTint: '#E8F1F5',
};
```

- [ ] **Step 2: Create `mobile/theme/typography.js`**

```js
export const typography = {
  size: {
    xs: 11,
    sm: 12,
    md: 14,
    lg: 15,
    xl: 17,
    xxl: 22,
    hero: 28,
  },
  weight: {
    regular: '400',
    medium: '500',
    semibold: '600',
    bold: '700',
    extrabold: '800',
  },
  headline: {
    letterSpacing: -0.4,
  },
  eyebrow: {
    fontSize: 11,
    fontWeight: '600',
    letterSpacing: 0.6,
    textTransform: 'uppercase',
  },
};
```

- [ ] **Step 3: Create `mobile/theme/spacing.js`**

```js
export const spacing = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 20,
  xxl: 24,
  xxxl: 32,
  huge: 40,
};

export const radii = {
  r8: 8,
  r12: 12,
  r16: 16,
  r20: 20,
  r999: 999,
};

export const shadows = {
  xs: {
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.06,
    shadowRadius: 3,
    elevation: 1,
  },
  sm: {
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.07,
    shadowRadius: 10,
    elevation: 2,
  },
  md: {
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.10,
    shadowRadius: 20,
    elevation: 4,
  },
  glow: (color) => ({
    shadowColor: color,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.25,
    shadowRadius: 12,
    elevation: 3,
  }),
};
```

- [ ] **Step 4: Create `mobile/theme/index.js`**

```js
export { colors } from './colors';
export { typography } from './typography';
export { spacing, radii, shadows } from './spacing';
```

- [ ] **Step 5: Verify no syntax errors**

Run: `cd mobile && node -e "require('@babel/core')" 2>/dev/null; node --check theme/colors.js && node --check theme/typography.js && node --check theme/spacing.js && node --check theme/index.js`

(These are plain ES module files using `export`, which Node's `--check` may reject depending on Node version/module type — if `node --check` errors specifically on `export` syntax rather than a real typo, that's an environment limitation, not a code bug. In that case just re-read each file carefully instead and confirm valid JS syntax and no typos by eye — do not skip verification silently either way, report which method you used.)

Expected: all 4 files well-formed, no unmatched braces/parens, no undefined references (each is self-contained except `index.js`, which imports from local siblings only).

- [ ] **Step 6: Commit**

```bash
git add mobile/theme
git commit -m "feat(mobile): design tokens (colores, tipografia, spacing/radios/sombras)"
```

---

### Task 2: Install Ionicons + shared components (`mobile/components/`)

**Files:**
- Modify: `mobile/package.json` (add `@expo/vector-icons` dependency)
- Create: `mobile/components/Button.js`
- Create: `mobile/components/Card.js`
- Create: `mobile/components/Input.js`
- Create: `mobile/components/Badge.js`
- Create: `mobile/components/Chip.js`
- Create: `mobile/components/ListItem.js`
- Create: `mobile/components/EmptyState.js`

**Interfaces:**
- Consumes: `colors`, `typography`, `spacing`, `radii`, `shadows` from `../theme` (Task 1).
- Produces:
  - `Button({ variant: 'primary'|'secondary'|'text', label, onPress, disabled, loading })`
  - `Card({ children, size: 'default'|'hero', style, onPress })` (optional `onPress` — when passed, renders as a `TouchableOpacity` instead of a plain `View`, same conditional pattern as `ListItem`)
  - `Input({ label, value, onChangeText, placeholder, keyboardType, secureTextEntry, error, multiline })`
  - `Badge({ label, tone: 'success'|'warning'|'danger'|'info'|'neutral' })`
  - `Chip({ label, selected, onPress })`
  - `ListItem({ icon, title, subtitle, trailing, onPress })` (icon is an Ionicons name string, optional)
  - `EmptyState({ icon, message })` (icon is an Ionicons name string)

  All consumed by Tasks 4-8 (all screen migrations). Every prop name above is final — later tasks must use these exact names, not invent variants.

- [ ] **Step 1: Add `@expo/vector-icons` to `mobile/package.json` and install**

`@expo/vector-icons` is already present as a nested dependency of `expo` itself (confirmed in `package-lock.json` under `expo/node_modules/@expo/vector-icons`) but not hoisted to the top level, so a direct `import { Ionicons } from '@expo/vector-icons'` from `mobile/components/*.js` may not resolve without an explicit top-level install. Add it explicitly:

```bash
cd mobile
npm install @expo/vector-icons@^15.0.3
```

Expected: `package.json`'s `dependencies` gains `"@expo/vector-icons": "^15.0.3"` (or whatever version npm resolves — accept npm's actual resolution, don't hand-edit the version string), `node_modules/@expo/vector-icons` exists at the top level after install.

- [ ] **Step 2: Create `mobile/components/Button.js`**

```js
import { TouchableOpacity, Text, ActivityIndicator, StyleSheet } from 'react-native';
import { colors, typography, spacing, radii, shadows } from '../theme';

export function Button({ variant = 'primary', label, onPress, disabled = false, loading = false }) {
  const isDisabled = disabled || loading;

  return (
    <TouchableOpacity
      onPress={onPress}
      disabled={isDisabled}
      activeOpacity={0.7}
      style={[
        styles.base,
        variant === 'primary' && styles.primary,
        variant === 'secondary' && styles.secondary,
        variant === 'text' && styles.text,
        isDisabled && styles.disabled,
      ]}
    >
      {loading ? (
        <ActivityIndicator color={variant === 'primary' ? colors.textOnPrimary : colors.primary} />
      ) : (
        <Text
          style={[
            styles.label,
            variant === 'primary' && styles.labelPrimary,
            variant === 'secondary' && styles.labelSecondary,
            variant === 'text' && styles.labelText,
          ]}
        >
          {label}
        </Text>
      )}
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  base: {
    height: 46,
    borderRadius: radii.r12,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: spacing.xl,
  },
  primary: {
    backgroundColor: colors.primary,
    ...shadows.glow(colors.primary),
  },
  secondary: {
    backgroundColor: 'transparent',
    borderWidth: 1.5,
    borderColor: colors.primary,
    borderStyle: 'dashed',
  },
  text: {
    backgroundColor: 'transparent',
    height: 'auto',
    paddingVertical: spacing.xs,
    paddingHorizontal: 0,
  },
  disabled: {
    opacity: 0.55,
  },
  label: {
    fontSize: typography.size.lg,
    fontWeight: typography.weight.semibold,
    letterSpacing: -0.2,
  },
  labelPrimary: {
    color: colors.textOnPrimary,
  },
  labelSecondary: {
    color: colors.primary,
  },
  labelText: {
    color: colors.primary,
    fontSize: typography.size.md,
    fontWeight: typography.weight.medium,
  },
});
```

- [ ] **Step 3: Create `mobile/components/Card.js`**

```js
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
```

- [ ] **Step 4: Create `mobile/components/Input.js`**

```js
import { View, Text, TextInput, StyleSheet } from 'react-native';
import { colors, typography, spacing, radii } from '../theme';

export function Input({ label, value, onChangeText, placeholder, keyboardType, secureTextEntry, error, multiline = false }) {
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
```

- [ ] **Step 5: Create `mobile/components/Badge.js`**

```js
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
```

- [ ] **Step 6: Create `mobile/components/Chip.js`**

```js
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
```

- [ ] **Step 7: Create `mobile/components/ListItem.js`**

```js
import { TouchableOpacity, View, Text, StyleSheet } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { colors, typography, spacing, radii } from '../theme';

export function ListItem({ icon, title, subtitle, trailing, onPress }) {
  const Container = onPress ? TouchableOpacity : View;
  const extraProps = onPress ? { activeOpacity: 0.7 } : {};

  return (
    <Container onPress={onPress} {...extraProps} style={styles.container}>
      {icon ? (
        <View style={styles.iconWrap}>
          <Ionicons name={icon} size={20} color={colors.primary} />
        </View>
      ) : null}
      <View style={styles.textWrap}>
        <Text style={styles.title} numberOfLines={1}>{title}</Text>
        {subtitle ? <Text style={styles.subtitle} numberOfLines={1}>{subtitle}</Text> : null}
      </View>
      {trailing ? <View style={styles.trailing}>{trailing}</View> : null}
    </Container>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.surface,
    borderRadius: radii.r12,
    padding: spacing.md,
    marginBottom: spacing.sm,
  },
  iconWrap: {
    width: 36,
    height: 36,
    borderRadius: radii.r12,
    backgroundColor: colors.primaryTint,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: spacing.md,
  },
  textWrap: {
    flex: 1,
  },
  title: {
    fontSize: typography.size.lg,
    fontWeight: typography.weight.semibold,
    color: colors.textPrimary,
  },
  subtitle: {
    fontSize: typography.size.md,
    color: colors.textSecondary,
    marginTop: 2,
  },
  trailing: {
    marginLeft: spacing.md,
  },
});
```

- [ ] **Step 8: Create `mobile/components/EmptyState.js`**

```js
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
```

- [ ] **Step 9: Verify**

Re-read all 7 component files. Confirm: every import resolves (relative `../theme` path correct from `components/`, `@expo/vector-icons` importable after Step 1's install), no undefined variables, JSX balanced, `StyleSheet.create` blocks well-formed, prop names match exactly what's documented in this task's Interfaces section (future tasks depend on these exact names).

- [ ] **Step 10: Commit**

```bash
git add mobile/package.json mobile/package-lock.json mobile/components
git commit -m "feat(mobile): componentes compartidos de UI (Button, Card, Input, Badge, Chip, ListItem, EmptyState) + Ionicons"
```

---

### Task 3: Restyle `App.js` navigation header

**Files:**
- Modify: `mobile/App.js`

**Interfaces:**
- Consumes: `colors`, `typography` from `./theme` (Tasks 1-2).
- Produces: no new exports — this task only changes `screenOptions` passed to the stack navigator. Later screen-migration tasks (4-8) rely on this task already being done so their screens render under the restyled header without needing to touch header config themselves.

- [ ] **Step 1: Read the current `App.js` in full**

Confirm the current `Stack.Navigator` setup, its `screenOptions` (if any), and which screens already override `headerShown: false` (per the recon: `Splash` and `Login`). Do not change which screens have `headerShown: false` — only restyle the header appearance for screens that do show one.

- [ ] **Step 2: Add restyled `screenOptions` to the `Stack.Navigator`**

Import `colors` and `typography` from `./theme` at the top of `App.js`. Add (or merge into existing) `screenOptions` on the `<Stack.Navigator>` element:

```js
screenOptions={{
  headerStyle: { backgroundColor: colors.surface },
  headerTitleStyle: {
    color: colors.textPrimary,
    fontWeight: typography.weight.bold,
    fontSize: typography.size.xl,
  },
  headerTintColor: colors.primary,
  headerShadowVisible: false,
  contentStyle: { backgroundColor: colors.background },
}}
```

Do not remove or alter any individual `<Stack.Screen>`'s own `options` (e.g. `Splash`/`Login`'s `headerShown: false`) — this `screenOptions` is the navigator-level default that per-screen options continue to override as before.

- [ ] **Step 3: Verify**

Re-read the full file. Confirm the import is added, `screenOptions` is valid JS (correct braces), and every existing `<Stack.Screen>` registration (route names, per-screen `options`) is unchanged — this task must not add/remove/rename any route.

- [ ] **Step 4: Commit**

```bash
git add mobile/App.js
git commit -m "feat(mobile): restyle del header de navegacion con tokens del tema"
```

---

### Task 4: Migrate shared/auth screens (Splash, Login, RecuperarPassword, Home)

**Files:**
- Modify: `mobile/screens/SplashScreen.js`
- Modify: `mobile/screens/LoginScreen.js`
- Modify: `mobile/screens/RecuperarPassword.js`
- Modify: `mobile/screens/HomeScreen.js`

**Interfaces:**
- Consumes: `colors`, `typography`, `spacing`, `radii`, `shadows` from `../theme`; `Button`, `Card`, `Input` from `../components` (Tasks 1-3). `Ionicons` from `@expo/vector-icons` for any icon needs (e.g. a coffee-cup or storefront icon on Home/Splash).

For each of the 4 files in this task:

- [ ] **Step 1: Read the file in full** — note its existing state variables, event handlers (`onPress`/`onChangeText` functions), API calls, and navigation calls. None of this logic changes in this task.

- [ ] **Step 2: Replace the screen's `StyleSheet.create` block and JSX markup**, screen by screen:

  - **`SplashScreen.js`**: keep the existing logo `<Image>` and loading logic untouched; wrap the screen content in a `View` using `colors.background`; if there's a loading spinner, recolor it to `colors.primary` (ActivityIndicator `color` prop).
  - **`LoginScreen.js`**: wrap the form in a `Card` (`size="hero"`); replace each bare `TextInput` (email, password) with `Input` (pass the existing `value`/`onChangeText`/`placeholder` props through unchanged — only the rendering component changes, not the state it's wired to); replace the submit button with `Button variant="primary"` wired to the existing submit handler; replace the "forgot password" link with `Button variant="text"` wired to the existing navigation call. Do not change the existing `useAuth().login` call or its error handling — only which component renders the trigger for it.
  - **`RecuperarPassword.js`**: same pattern as Login's form — `Card` wrapper, `Input` for the email field, `Button variant="primary"` for submit. The existing local `Alert`-based stub logic (noted in recon as not yet wired to a real API call) stays exactly as is — this task is visual only, not a scope to "fix" the stub.
  - **`HomeScreen.js`**: replace the per-role button list (`BOTONES_POR_ROL`) rendering with `ListItem` (one per role button, `icon` set to a reasonable Ionicons name per destination — e.g. `restaurant-outline` for Mesas, `flame-outline` for Cocina, `cash-outline` for Caja — pick sensibly, this isn't in the Task 2 mapping table verbatim, use judgment), each `onPress` wired to the existing navigation call unchanged. Keep the existing logout button, restyled as `Button variant="secondary"`.

- [ ] **Step 3: Verify each file**

Re-read all 4 files fully after editing. Confirm: no leftover unused imports (old inline `StyleSheet` fully replaced, not left dead alongside the new one), no removed/renamed state variables or handlers, all navigation calls (`navigation.navigate(...)`) use the exact same route names as before, JSX balanced.

- [ ] **Step 4: Commit**

```bash
git add mobile/screens/SplashScreen.js mobile/screens/LoginScreen.js mobile/screens/RecuperarPassword.js mobile/screens/HomeScreen.js
git commit -m "feat(mobile): rediseno visual de pantallas compartidas (Splash, Login, RecuperarPassword, Home)"
```

---

### Task 5: Migrate Mesero screens (Mesas, Pedido, Detalle)

**Files:**
- Modify: `mobile/screens/MesasScreen.js`
- Modify: `mobile/screens/PedidoScreen.js`
- Modify: `mobile/screens/DetalleScreen.js`

**Interfaces:**
- Consumes: `colors`, `typography`, `spacing`, `radii`, `shadows` from `../theme`; `Button`, `Card`, `Badge`, `ListItem`, `EmptyState` from `../components`; `Ionicons` from `@expo/vector-icons`.

**Important — `DetalleScreen.js` and its WebSocket subscription:** this file was touched most recently by the just-completed Fase 4 (WebSocket) work. It has TWO `useFocusEffect` hooks (one REST fetch, one WS subscription using the mandated `cancelado` boolean-flag guard pattern) and depends on a stable `pedidoId` (not `pedido?.id`) — see the file's current state, don't reconstruct this from memory. **Do not modify either `useFocusEffect` hook, the WS subscription logic, the `cancelado` guard, or the `connectToChannel` call in any way** — only the JSX returned by the component and its `StyleSheet.create` block are in scope.

- [ ] **Step 1: Read all 3 files in full** — note existing state, handlers, API calls, navigation calls. `DetalleScreen.js` additionally: note the WS effect exactly as described above so you don't disturb it.

- [ ] **Step 2: Replace `StyleSheet.create` blocks and JSX markup**:

  - **`MesasScreen.js`**: table grid — replace each table tile with a `Card` (`size="default"`) containing the table number and a `Badge` for its status (`tone="success"` for Libre, `tone="warning"` for Reservada, `tone="danger"` for Ocupada — matching the existing color meanings from recon: green/amber/red). Keep the existing `onPress` per tile (navigates to new pedido or existing pedido detail) unchanged.
  - **`PedidoScreen.js`**: menu list items become `ListItem` (title = product name, subtitle = price, trailing = an add/quantity control — keep whatever quantity-adjustment UI already exists, just restyle its container, don't redesign the interaction). Cart/running total section becomes a `Card`. Submit button becomes `Button variant="primary"`.
  - **`DetalleScreen.js`**: order info becomes a `Card`; each item in the order's detail list becomes a `ListItem`; order status becomes a `Badge` (map `Pendiente`→`tone="neutral"`, `En preparación`→`tone="warning"`, `Listo`→`tone="info"`, `Entregado`→`tone="success"`, `Cancelado`→`tone="danger"`); the "Marcar como Entregado" button becomes `Button variant="primary"`; the manual "Actualizar" button (WS fallback, must stay) becomes `Button variant="text"`.

- [ ] **Step 3: Verify**

Re-read all 3 files. Confirm no logic changes (especially `DetalleScreen.js`'s WS effect — diff it mentally against what Step 1 noted, byte-identical), all handlers/navigation calls intact, JSX balanced, Badge `tone` mapping covers all 5 pedido statuses used in `DetalleScreen.js` and all 3 mesa statuses used in `MesasScreen.js`.

- [ ] **Step 4: Commit**

```bash
git add mobile/screens/MesasScreen.js mobile/screens/PedidoScreen.js mobile/screens/DetalleScreen.js
git commit -m "feat(mobile): rediseno visual de pantallas de Mesero (Mesas, Pedido, Detalle)"
```

---

### Task 6: Migrate Cocina screens (Cocina home, ColaPedidos, CocinaDetalle, Menu, Inventario)

**Files:**
- Modify: `mobile/screens/CocinaScreen.js`
- Modify: `mobile/screens/ColaPedidosScreen.js`
- Modify: `mobile/screens/CocinaDetalleScreen.js`
- Modify: `mobile/screens/MenuScreen.js`
- Modify: `mobile/screens/InventarioScreen.js`

**Interfaces:**
- Consumes: `colors`, `typography`, `spacing`, `radii`, `shadows` from `../theme`; `Button`, `Card`, `Badge`, `Chip`, `ListItem`, `EmptyState` from `../components`; `Ionicons` from `@expo/vector-icons`.

**Important — `ColaPedidosScreen.js`:** also touched by Fase 4. Has a second `useFocusEffect` with the WS `cancelado` guard subscribing to the `cocina` channel, AND (from the final Fase 4 review fix) a loading-guard condition that must stay `if (loading && pedidos.length === 0)` — not reverted to a bare `if (loading)`. **Do not modify the WS effect, the `cancelado` guard, or that specific loading-guard condition's logic** — only its visual rendering (i.e., you may change what the spinner/empty view looks like, but the *condition* that decides whether to show it must stay exactly `loading && pedidos.length === 0`, checking whatever the file's actual list-state variable is named).

- [ ] **Step 1: Read all 5 files in full** — note state, handlers, API calls, navigation calls. `ColaPedidosScreen.js` additionally: note the WS effect and loading-guard condition exactly as described above.

- [ ] **Step 2: Replace `StyleSheet.create` blocks and JSX markup**:

  - **`CocinaScreen.js`** (home/landing for this role): pending-order count becomes a prominent `Card` (`size="hero"`) with a large number + label; nav buttons to Cola/Menu/Inventario become `ListItem`s with icons (`list-outline` for Cola, `restaurant-outline` for Menu, `cube-outline` for Inventario).
  - **`ColaPedidosScreen.js`**: queue rows become `ListItem` (title = mesa/pedido identifier, subtitle = time or item count, trailing = a `Badge` for status). Empty queue state uses `EmptyState` with an instructive message, not a bare "vacío" — e.g. "Sin pedidos pendientes. Aparecerán aquí en cuanto un mesero cree uno." (or equivalent wording matching the file's existing tone), so the screen explains what will appear and why it's empty, not just that it's empty.
  - **`CocinaDetalleScreen.js`**: order detail becomes a `Card`; item list becomes `ListItem`s; status-advance buttons (Pendiente→En preparación→Listo) become `Button variant="primary"`; low-stock alert (existing `Alert.alert`, per recon this was fixed to be blocking in a prior phase — do not change how/when it's triggered) — if there's any inline low-stock banner in the JSX besides the `Alert.alert` call, restyle it using `colors.warningTint`/`colors.warning`, matching the `Input` component's error-banner pattern.
  - **`MenuScreen.js`**: category filter row becomes a row of `Chip`s (`selected` = active category); product list becomes `ListItem`s (trailing = delete icon button using `Ionicons name="trash-outline"`); "add product" form/button becomes `Button variant="secondary"` (dashed style, matching Sway's "add new" convention) opening whatever the existing add-flow is (don't redesign the flow itself, just its trigger's visual style). The existing "aviso" soft-delete message (from a prior phase's fix) stays functionally identical, restyle its container only.
  - **`InventarioScreen.js`**: ingredient list becomes `ListItem`s (trailing = +1/-1 stock buttons, restyled as small `Button variant="secondary"` or icon-only touchables using `Ionicons name="add-circle-outline"`/`"remove-circle-outline"` — keep the exact +1/-1 adjustment logic, only restyle the buttons; whatever container you use, give it an explicit `minWidth: 44, minHeight: 44` — icon-only touch targets must meet the 44×44pt minimum, an icon alone at its natural size is too small to tap reliably); below-minimum-stock highlighting (existing, fixed in a prior phase to use `Number()` comparison — do not touch that comparison logic) becomes a `Badge tone="danger"` or a tinted `ListItem` background, implementer's reasonable choice, applied only when the existing highlight condition is already true.

- [ ] **Step 3: Verify**

Re-read all 5 files. Confirm no logic changes (`ColaPedidosScreen.js` WS effect + loading-guard condition especially — diff mentally against what Step 1 noted), stock-comparison logic in `InventarioScreen.js` untouched, all handlers/navigation calls intact, JSX balanced.

- [ ] **Step 4: Commit**

```bash
git add mobile/screens/CocinaScreen.js mobile/screens/ColaPedidosScreen.js mobile/screens/CocinaDetalleScreen.js mobile/screens/MenuScreen.js mobile/screens/InventarioScreen.js
git commit -m "feat(mobile): rediseno visual de pantallas de Cocina (home, Cola, Detalle, Menu, Inventario)"
```

---

### Task 7: Migrate Caja screens (Caja, Pago, Gastos)

**Files:**
- Modify: `mobile/screens/CajaScreen.js`
- Modify: `mobile/screens/PagoScreen.js`
- Modify: `mobile/screens/GastosScreen.js`

**Interfaces:**
- Consumes: `colors`, `typography`, `spacing`, `radii`, `shadows` from `../theme`; `Button`, `Card`, `Badge`, `Chip`, `Input`, `ListItem`, `EmptyState` from `../components`; `Ionicons` from `@expo/vector-icons`.

**Important — `CajaScreen.js`:** also touched by Fase 4. Same pattern as `ColaPedidosScreen.js` in Task 6: has a WS effect (`caja` channel, `cancelado` guard) and a loading-guard condition that must stay `if (loading && pedidos.length === 0)` (checking whatever the file's actual list-state variable is named) — not reverted to a bare `if (loading)`. **Do not modify the WS effect, the `cancelado` guard, or that loading-guard condition's logic.**

**Important — `GastosScreen.js`:** this file was substantially reworked in the just-completed Fase 3b (Registrar Compra) plan, including a final-review fix that moved its cards into a `FlatList`'s `ListHeaderComponent` (to fix a real scroll/overflow bug) and split its error state into `error` (gasto form) and `errorCompra` (compra form, rendered in its own card). **Do not revert the `ListHeaderComponent` structure back to a flat top-level layout, and do not merge `error`/`errorCompra` back into one shared state** — both were real bugs fixed in the immediately preceding plan. Restyle the content *inside* `renderHeader()` and inside the `FlatList`'s `renderItem`, keeping that structural shape.

- [ ] **Step 1: Read all 3 files in full** — note state, handlers, API calls, navigation calls. `CajaScreen.js` and `GastosScreen.js` additionally: note the specifics called out above exactly as they currently exist in the file (don't rely on this plan's summary — read the real current code).

- [ ] **Step 2: Replace `StyleSheet.create` blocks and JSX markup**:

  - **`CajaScreen.js`**: queue rows (orders ready to charge) become `ListItem` (title = mesa/pedido identifier, subtitle = total or item count, trailing = a `Button variant="primary"` labeled "Cobrar" navigating to Pago). Empty state uses `EmptyState` with an instructive message, not a bare "vacío" — e.g. "Sin pedidos por cobrar. Aparecerán aquí cuando cocina marque un pedido como Listo." (or equivalent wording matching the file's existing tone).
  - **`PagoScreen.js`**: order summary becomes a `Card`; payment-method picker becomes a row of `Chip`s (one per método de pago, `selected` = chosen method); amount-received field becomes `Input` (`keyboardType="numeric"`); confirm button becomes `Button variant="primary"`; the existing `error && !pedido` crash guard (fixed in a prior phase) must stay exactly as is — only its rendered error message's visual style changes, using the same error-banner pattern as `Input`'s `error` prop (`colors.dangerTint`/`colors.danger`).
  - **`GastosScreen.js`**: within `renderHeader()` — the existing gasto-form card becomes a `Card` containing `Input`s for descripcion/monto and a `Button variant="primary"` for "Agregar gasto"; the existing "Comprar insumo" card becomes a `Card` containing a row of `Chip`s for ingredient selection (replacing the current `TouchableOpacity`+`Text` chip pattern — same selection behavior, restyled), `Input`s for cantidad/monto, and `Button variant="primary"` for "Registrar compra"; the totals box becomes a `Card`. Within the `FlatList`'s `renderItem` — each session-gasto row becomes a `ListItem`.

- [ ] **Step 3: Verify**

Re-read all 3 files. Confirm no logic changes (`CajaScreen.js` WS effect + loading-guard, `GastosScreen.js` `ListHeaderComponent` structure + split error states, `PagoScreen.js` null-guard — diff mentally against what Step 1 noted), all handlers/navigation calls intact, JSX balanced.

- [ ] **Step 4: Commit**

```bash
git add mobile/screens/CajaScreen.js mobile/screens/PagoScreen.js mobile/screens/GastosScreen.js
git commit -m "feat(mobile): rediseno visual de pantallas de Caja (Caja, Pago, Gastos)"
```

---

## Redesign complete when

All 7 tasks committed, every one of the 15 screens plus `App.js`'s header renders exclusively through `mobile/theme/` tokens and `mobile/components/` shared components (no screen retains its own ad-hoc inline color/spacing values for things the shared system already covers), and no screen's data-fetching, WebSocket, navigation, or business logic differs from its pre-redesign behavior. Real visual QA (does it look good on an actual screen size, touch target comfort, text wrapping) is explicitly deferred to the user running Expo Go on a device — no task in this plan claims to have verified that, per this plan's Verification Approach in the design spec.
