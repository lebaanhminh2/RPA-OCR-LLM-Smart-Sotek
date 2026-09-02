import { describe, expect, it } from 'vitest'

import type { ReviewField, ReviewSource } from '../types/api'
import { getReviewSelection } from './reviewSelection'

function source(
  ocrBlockId: string,
  documentId: string,
  pageNumber: number,
  bboxX: number,
): ReviewSource {
  return {
    ocr_block_id: ocrBlockId,
    document_id: documentId,
    page_number: pageNumber,
    bbox_x: bboxX,
    bbox_y: 0.2,
    bbox_width: 0.3,
    bbox_height: 0.04,
  }
}

function field(sources: ReviewSource[]): ReviewField {
  return {
    id: 'field-1',
    case_id: 'case-1',
    field_code: 'ho_ten',
    original_value: 'NGUYỄN VĂN AN',
    current_value: 'NGUYỄN VĂN AN',
    sources,
  }
}

describe('getReviewSelection', () => {
  it('returns no viewer selection when the field has no evidence', () => {
    expect(getReviewSelection(field([]), null)).toBeNull()
  })

  it('returns every bbox on the selected document page', () => {
    const first = source('block-1', 'document-1', 2, 0.1)
    const second = source('block-2', 'document-1', 2, 0.5)
    const otherPage = source('block-3', 'document-1', 3, 0.7)

    const selection = getReviewSelection(
      field([first, second, otherPage]),
      first.ocr_block_id,
    )

    expect(selection).toMatchObject({
      documentId: 'document-1',
      pageNumber: 2,
      activeSource: first,
    })
    expect(selection?.highlights).toEqual([
      {
        bbox_x: 0.1,
        bbox_y: 0.2,
        bbox_width: 0.3,
        bbox_height: 0.04,
      },
      {
        bbox_x: 0.5,
        bbox_y: 0.2,
        bbox_width: 0.3,
        bbox_height: 0.04,
      },
    ])
  })

  it('switches to evidence on another document and page', () => {
    const first = source('block-1', 'document-1', 1, 0.1)
    const target = source('block-2', 'document-2', 4, 0.6)

    expect(
      getReviewSelection(field([first, target]), target.ocr_block_id),
    ).toMatchObject({
      documentId: 'document-2',
      pageNumber: 4,
      activeSource: target,
      highlights: [
        {
          bbox_x: 0.6,
          bbox_y: 0.2,
          bbox_width: 0.3,
          bbox_height: 0.04,
        },
      ],
    })
  })
})
