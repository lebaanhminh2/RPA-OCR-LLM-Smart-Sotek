import { describe, expect, it } from 'vitest'

import {
  getFieldValidationMessage,
  toFieldDraftValue,
  toPersistedFieldValue,
} from './fieldValuePresentation'

describe('field value presentation', () => {
  it('shows a serialized loan-purpose array as reviewer-friendly text', () => {
    expect(
      toFieldDraftValue('muc_dich_vay', '["Sửa nhà","Học tập"]'),
    ).toBe('Sửa nhà, Học tập')
  })

  it('serializes edited loan purposes back to the canonical JSON string', () => {
    expect(
      toPersistedFieldValue(
        'muc_dich_vay',
        'Sửa nhà, Học tập, Sửa nhà',
      ),
    ).toBe('["Sửa nhà","Học tập"]')
  })

  it('preserves ordinary fields and converts an empty draft to null', () => {
    expect(toFieldDraftValue('ho_ten', 'Nguyễn Văn An')).toBe(
      'Nguyễn Văn An',
    )
    expect(toPersistedFieldValue('ho_ten', '  Nguyễn Văn An  ')).toBe(
      'Nguyễn Văn An',
    )
    expect(toPersistedFieldValue('email', '  ')).toBeNull()
  })

  it('warns about malformed email without rejecting other text fields', () => {
    expect(
      getFieldValidationMessage('email', 'tranxuanha ogmail.com'),
    ).toBe('Email chưa đúng định dạng, vui lòng kiểm tra.')
    expect(
      getFieldValidationMessage('email', 'tranxuanha@gmail.com'),
    ).toBeNull()
    expect(
      getFieldValidationMessage('ho_ten', 'tranxuanha ogmail.com'),
    ).toBeNull()
  })
})
