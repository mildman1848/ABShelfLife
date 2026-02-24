# Translation Operations

## Source Layout

- Source language: `i18n/locales/en/**/*.json`
- German translation: `i18n/locales/de/**/*.json`

## Workflow

1. Update English source strings first.
2. Keep German strings semantically aligned.
3. Validate JSON syntax before committing.

## Language Policy

- English (`en`) is source-of-truth.
- German (`de`) is the maintained translation.
- Additional locales can be added under `i18n/locales/<lang>/` when needed.
