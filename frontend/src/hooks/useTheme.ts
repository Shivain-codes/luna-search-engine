import { useThemeStore } from '@/store/themeStore'

export function useTheme() {
  const { theme, resolvedTheme, setTheme, initializeTheme } = useThemeStore()

  return {
    theme,
    resolvedTheme,
    setTheme,
    initializeTheme,
    isDark: resolvedTheme === 'dark',
  }
}