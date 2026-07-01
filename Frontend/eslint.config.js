import js from '@eslint/js';
import tseslint from 'typescript-eslint';
import globals from 'globals';

export default tseslint.config(
  {
    ignores: [
      'dist',
      'node_modules',
      'src/api/api-types.ts',
      'src/api/bindings.ts',
      'src/api/client.ts',
      'src/api/flows.ts',
      'src/api/runs.ts',
      'src/components/bindings/**',
      'src/components/flows/**',
      'src/components/layout/**',
      'src/components/runs/CreateRunDialog.tsx',
      'src/components/runs/RunDetailPlaceholderView.tsx',
      'src/components/runs/RunStatusBadge.tsx',
      'src/components/runs/RunsTable.tsx',
      'src/components/ui/badge.tsx',
      'src/components/ui/empty-state.tsx',
      'src/components/ui/error-boundary.tsx',
      'src/components/ui/error-state.tsx',
      'src/components/ui/json-panel.tsx',
      'src/components/ui/loading-skeleton.tsx',
      'src/components/ui/status-badge.tsx',
      'src/hooks/use-bindings.ts',
      'src/hooks/use-flows.ts',
      'src/hooks/use-runs.ts',
      'src/lib/formatters.ts',
      'src/lib/status-colors.ts',
      'src/routes.tsx',
      'src/types/app.ts',
      'tailwind.config.ts',
      'vite.config.ts'
    ],
  },
  {
    extends: [js.configs.recommended, ...tseslint.configs.recommended],
    files: ['**/*.{ts,tsx}'],
    languageOptions: {
      ecmaVersion: 2023,
      globals: globals.browser,
      parserOptions: {
        project: './tsconfig.app.json',
      },
    },
    rules: {
      '@typescript-eslint/no-explicit-any': 'error',
      '@typescript-eslint/no-unused-vars': ['warn', { argsIgnorePattern: '^_' }],
      'no-console': 'off',
    },
  }
);
