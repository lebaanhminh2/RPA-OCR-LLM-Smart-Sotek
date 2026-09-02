import type { ReviewField } from '../../types/api'
import './FieldItem.css'

export type FieldItemProps = {
  field: ReviewField
  label: string
  isSelected: boolean
  onSelect: (field: ReviewField) => void
}

export function FieldItem({
  field,
  label,
  isSelected,
  onSelect,
}: FieldItemProps) {
  const hasValue = field.current_value !== null && field.current_value !== ''

  return (
    <li>
      <button
        type="button"
        className={`field-item${isSelected ? ' field-item--selected' : ''}`}
        onClick={() => onSelect(field)}
        aria-pressed={isSelected}
      >
        <span className="field-item__label">{label}</span>
        <span
          className={`field-item__value${hasValue ? '' : ' field-item__value--empty'}`}
        >
          {hasValue ? field.current_value : 'Chưa trích xuất'}
        </span>
        <span className="field-item__evidence">
          {field.sources.length > 0
            ? `${field.sources.length} vùng bằng chứng`
            : 'Không có bằng chứng'}
        </span>
      </button>
    </li>
  )
}
