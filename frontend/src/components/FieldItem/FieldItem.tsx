import { useState, type KeyboardEvent } from 'react'

import type { ReviewField } from '../../types/api'
import {
  getFieldValidationMessage,
  toFieldDraftValue,
  toPersistedFieldValue,
} from './fieldValuePresentation'
import './FieldItem.css'

type SaveState = 'idle' | 'saving' | 'success' | 'error'

export type FieldItemProps = {
  field: ReviewField
  label: string
  isSelected: boolean
  isEditable: boolean
  onSelect: (field: ReviewField) => void
  onSave: (field: ReviewField, currentValue: string | null) => Promise<void>
}

export function FieldItem({
  field,
  label,
  isSelected,
  isEditable,
  onSelect,
  onSave,
}: FieldItemProps) {
  const [draftValue, setDraftValue] = useState(
    toFieldDraftValue(field.field_code, field.current_value),
  )
  const [saveState, setSaveState] = useState<SaveState>('idle')
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const validationMessage = getFieldValidationMessage(
    field.field_code,
    draftValue,
  )

  async function saveDraft() {
    if (!isEditable || saveState === 'saving') {
      return
    }

    const newValue = toPersistedFieldValue(field.field_code, draftValue)
    if (newValue === field.current_value) {
      return
    }

    setSaveState('saving')
    setErrorMessage(null)
    try {
      await onSave(field, newValue)
      setDraftValue(toFieldDraftValue(field.field_code, newValue))
      setSaveState('success')
    } catch (error: unknown) {
      setSaveState('error')
      setErrorMessage(
        error instanceof Error ? error.message : 'Không thể lưu thay đổi.',
      )
    }
  }

  function handleKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === 'Enter') {
      event.currentTarget.blur()
    }
    if (event.key === 'Escape') {
      setDraftValue(
        toFieldDraftValue(field.field_code, field.current_value),
      )
      setSaveState('idle')
      setErrorMessage(null)
    }
  }

  return (
    <li
      className={`field-item${isSelected ? ' field-item--selected' : ''}`}
    >
      <label className="field-item__content">
        <span className="field-item__label">{label}</span>
        <input
          className="field-item__input"
          value={draftValue}
          type={field.field_code === 'email' ? 'email' : 'text'}
          placeholder="Chưa trích xuất"
          disabled={!isEditable || saveState === 'saving'}
          aria-invalid={validationMessage !== null}
          onFocus={() => onSelect(field)}
          onChange={(event) => {
            setDraftValue(event.target.value)
            setSaveState('idle')
            setErrorMessage(null)
          }}
          onBlur={() => void saveDraft()}
          onKeyDown={handleKeyDown}
          aria-label={label}
        />
      </label>
      <div className="field-item__footer">
        <button
          type="button"
          className="field-item__evidence-button"
          onClick={() => onSelect(field)}
          aria-pressed={isSelected}
        >
          {field.sources.length > 0
            ? `${field.sources.length} vùng bằng chứng`
            : 'Không có bằng chứng'}
        </button>
        <span
          className={`field-item__save-status field-item__save-status--${
            validationMessage !== null && saveState === 'idle'
              ? 'error'
              : saveState
          }`}
          aria-live="polite"
        >
          {saveState === 'saving'
            ? 'Đang lưu...'
            : saveState === 'success'
              ? 'Đã lưu'
              : saveState === 'error'
                ? errorMessage
                : validationMessage !== null
                  ? validationMessage
                : isEditable
                  ? 'Enter hoặc rời ô để lưu'
                  : 'Chỉ xem'}
        </span>
      </div>
    </li>
  )
}
