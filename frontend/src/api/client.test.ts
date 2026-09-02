import { afterEach, describe, expect, it, vi } from 'vitest'

import { updateReviewField, uploadCase } from './client'

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('review API client', () => {
  it('patches the current field value', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          id: 'field-1',
          case_id: 'case-1',
          field_code: 'ho_ten',
          original_value: 'NGUYEN VAN A',
          current_value: 'Nguyễn Văn A',
        }),
        {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        },
      ),
    )
    vi.stubGlobal('fetch', fetchMock)

    const updated = await updateReviewField(
      'case-1',
      'field-1',
      'Nguyễn Văn A',
    )

    expect(updated.current_value).toBe('Nguyễn Văn A')
    expect(fetchMock).toHaveBeenCalledWith(
      'http://127.0.0.1:8000/cases/case-1/fields/field-1',
      {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ current_value: 'Nguyễn Văn A' }),
      },
    )
  })

  it('uploads the whole case once', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          id: 'case-1',
          status: 'COMPLETED',
          created_at: '2026-09-02T10:00:00Z',
          updated_at: '2026-09-02T10:30:00Z',
        }),
        {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        },
      ),
    )
    vi.stubGlobal('fetch', fetchMock)

    const completedCase = await uploadCase('case-1')

    expect(completedCase.status).toBe('COMPLETED')
    expect(fetchMock).toHaveBeenCalledWith(
      'http://127.0.0.1:8000/cases/case-1/upload',
      { method: 'POST' },
    )
  })
})
