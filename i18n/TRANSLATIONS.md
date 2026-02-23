# Translation Operations

## Crowdin
Required environment variables:
- `CROWDIN_PROJECT_ID`
- `CROWDIN_PERSONAL_TOKEN`

Config file:
- `crowdin.yml`

Expected layout:
- source: `i18n/locales/en/**/*.json`
- translations: `i18n/locales/<lang>/**/*.json`

## Weblate
CLI config file:
- `.weblate`
- component template: `i18n/weblate-component.template.yml`

Recommended local override (untracked):
- `.weblate.ini`
- starter template: `.weblate.ini.example`

Required local value:
- Weblate API token for `https://hosted.weblate.org/api/`

## Language Policy
- English (`en`) is source-of-truth.
- German (`de`) is first maintained translation.
- Additional locales are community maintained.
