module.exports = {
  env: {
    browser: true,
    es2021: true,
    node: true,
  },
  extends: [
    'eslint:recommended',
    'prettier', // Must be last to override other configs
  ],
  parserOptions: {
    ecmaVersion: 'latest',
    sourceType: 'module',
  },
  rules: {
    // Align with CONTRIBUTING.md standards
    'max-depth': ['error', 3], // Max 3 nesting levels
    'max-lines': ['warn', { max: 300, skipBlankLines: true, skipComments: true }],
    'max-params': ['warn', 5], // Max 5 parameters
    'no-console': ['warn', { allow: ['warn', 'error'] }],
    'no-unused-vars': ['error', { argsIgnorePattern: '^_' }],
    'prefer-const': 'error',
    'no-var': 'error',
    eqeqeq: ['error', 'always'],
    curly: ['error', 'all'],
    'brace-style': ['error', '1tbs'],
    'comma-dangle': ['error', 'always-multiline'],
    semi: ['error', 'always'],
    quotes: ['error', 'single', { avoidEscape: true }],
  },
  overrides: [
    {
      files: ['*.test.js', '*.spec.js'],
      env: {
        jest: true,
      },
      rules: {
        'max-lines': 'off', // Test files can be longer
      },
    },
  ],
  ignorePatterns: ['node_modules/', 'dist/', 'build/', '*.min.js', 'room/node_modules/'],
};
