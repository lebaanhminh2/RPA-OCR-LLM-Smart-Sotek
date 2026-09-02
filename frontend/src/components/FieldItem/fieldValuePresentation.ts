const MULTI_CHOICE_FIELD_CODES = new Set(['muc_dich_vay'])
const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/

export function toFieldDraftValue(
  fieldCode: string,
  persistedValue: string | null,
): string {
  if (persistedValue === null) {
    return ''
  }
  if (!MULTI_CHOICE_FIELD_CODES.has(fieldCode)) {
    return persistedValue
  }

  try {
    const choices: unknown = JSON.parse(persistedValue)
    if (
      Array.isArray(choices) &&
      choices.every((choice) => typeof choice === 'string')
    ) {
      return choices.join(', ')
    }
  } catch {
    // Preserve a legacy/manual value so the reviewer can still correct it.
  }
  return persistedValue
}

export function toPersistedFieldValue(
  fieldCode: string,
  draftValue: string,
): string | null {
  const trimmedValue = draftValue.trim()
  if (trimmedValue === '') {
    return null
  }
  if (!MULTI_CHOICE_FIELD_CODES.has(fieldCode)) {
    return trimmedValue
  }

  const choices = [
    ...new Set(
      trimmedValue
        .split(',')
        .map((choice) => choice.trim())
        .filter((choice) => choice !== ''),
    ),
  ]
  return choices.length === 0 ? null : JSON.stringify(choices)
}

export function getFieldValidationMessage(
  fieldCode: string,
  draftValue: string,
): string | null {
  const trimmedValue = draftValue.trim()
  if (
    fieldCode === 'email' &&
    trimmedValue !== '' &&
    !EMAIL_PATTERN.test(trimmedValue)
  ) {
    return 'Email chưa đúng định dạng, vui lòng kiểm tra.'
  }
  return null
}
