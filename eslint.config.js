import js from '@eslint/js';
import globals from 'globals';

export default [
  { ignores: ['node_modules/**', '.venv/**', 'backend/**', 'tests/**'] },
  js.configs.recommended,
  {
    files: ['frontend/**/*.js'],
    languageOptions: {
      ecmaVersion: 2023,
      sourceType: 'module',
      globals: { ...globals.browser },
    },
    rules: {
      // Mirror the frontend's security posture (see tests/test_static.py).
      'no-eval': 'error',
      'no-implied-eval': 'error',
      'no-new-func': 'error',
      'no-script-url': 'error',
      eqeqeq: ['error', 'smart'],
      'no-var': 'error',
      'prefer-const': 'error',
    },
  },
];
