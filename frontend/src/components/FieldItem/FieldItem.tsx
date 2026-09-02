import { useState, type KeyboardEvent } from 'react'

import type { ReviewField } from '../../types/api'
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
  const [draftValue, setDraftValue] = useState(field.current_value ?? '')
  const [saveState, setSaveState] = useState<SaveState>('idle')
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  async function saveDraft() {
    if (!isEditable || saveState === 'saving') {
      return
    }

    const trimmedValue = draftValue.trim()
    const newValue = trimmedValue === '' ? null : trimmedValue
    if (newValue === field.current_value) {
      return
    }

    setSaveState('saving')
    setErrorMessage(null)
    try {
      await onSave(field, newValue)
      setDraftValue(newValue ?? '')
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
      setDraftValue(field.current_value ?? '')
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
          placeholder="Chưa trích xuất"
          disabled={!isEditable || saveState === 'saving'}
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
          className={`field-item__save-status field-item__save-status--${saveState}`}
          aria-live="polite"
        >
          {saveState === 'saving'
            ? 'Đang lưu...'
            : saveState === 'success'
              ? 'Đã lưu'
              : saveState === 'error'
                ? errorMessage
                : isEditable
                  ? 'Enter hoặc rời ô để lưu'
                  : 'Chỉ xem'}
        </span>
      </div>
    </li>
  )
}
