import { FieldItem } from '../FieldItem'
import type { ReviewField } from '../../types/api'
import { getFieldLabel } from './fieldCatalog'
import './FieldList.css'

export type FieldListProps = {
  fields: readonly ReviewField[]
  selectedFieldId: string | null
  onSelectField: (field: ReviewField) => void
}

export function FieldList({
  fields,
  selectedFieldId,
  onSelectField,
}: FieldListProps) {
  return (
    <section className="field-list" aria-labelledby="field-list-title">
      <header className="field-list__header">
        <div>
          <p className="eyebrow">Dữ liệu trích xuất</p>
          <h2 id="field-list-title">Thông tin hồ sơ</h2>
        </div>
        <span>{fields.length} trường</span>
      </header>
      <p className="field-list__hint">
        Chọn một trường để xem vị trí thông tin trên tài liệu.
      </p>
      <ul className="field-list__items">
        {fields.map((field) => (
          <FieldItem
            key={field.id}
            field={field}
            label={getFieldLabel(field.field_code)}
            isSelected={field.id === selectedFieldId}
            onSelect={onSelectField}
          />
        ))}
      </ul>
    </section>
  )
}
