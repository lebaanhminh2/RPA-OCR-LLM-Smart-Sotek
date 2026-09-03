import { afterEach, describe, expect, it, vi } from 'vitest'

import {
  DEMO_CASE_ID,
  getCaseReview,
  getDocumentFile,
  updateReviewField,
  uploadCase,
} from './client'

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('review API client', () => {
  it('edits demo data in memory and loads its evidence document', async () => {
    const demoPayload = {
      case: {
        id: DEMO_CASE_ID,
        status: 'READY_FOR_REVIEW',
        created_at: '2026-09-03T09:00:00Z',
        updated_at: '2026-09-03T09:10:00Z',
      },
      review: {
        case_id: DEMO_CASE_ID,
        status: 'READY_FOR_REVIEW',
        fields: [
          {
            id: 'demo-field',
            case_id: DEMO_CASE_ID,
            field_code: 'ho_ten',
            original_value: 'NGUYỄN VĂN AN',
            current_value: 'NGUYỄN VĂN AN',
            sources: [
              {
                ocr_block_id: 'demo-block',
                document_id: 'demo-document',
                page_number: 1,
                bbox_x: 0.1,
                bbox_y: 0.2,
                bbox_width: 0.3,
                bbox_height: 0.04,
              },
            ],
          },
        ],
      },
      documents: { 'demo-document': '/demo-documents/cccd_front.pdf' },
    }
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(JSON.stringify(demoPayload), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
      )
      .mockResolvedValueOnce(
        new Response(new Blob(['demo pdf'], { type: 'application/pdf' }), {
          status: 200,
          headers: { 'Content-Type': 'application/pdf' },
        }),
      )
    vi.stubGlobal('fetch', fetchMock)

    const review = await getCaseReview(DEMO_CASE_ID)
    const updated = await updateReviewField(
      DEMO_CASE_ID,
      review.fields[0].id,
      'Nguyễn Văn An',
    )
    const document = await getDocumentFile(
      review.fields[0].sources[0].document_id,
    )

    expect(updated.current_value).toBe('Nguyễn Văn An')
    expect(document.documentType).toBe('pdf')
    expect(fetchMock).toHaveBeenNthCalledWith(1, '/demo-data.json')
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      '/demo-documents/cccd_front.pdf',
    )
  })

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
