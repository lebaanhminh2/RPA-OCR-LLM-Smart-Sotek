import type { NormalizedBbox } from '../components/DocumentViewer'
import type { ReviewField, ReviewSource } from '../types/api'

export type ReviewSelection = {
  activeSource: ReviewSource
  documentId: string
  pageNumber: number
  highlights: NormalizedBbox[]
}

function toBbox(source: ReviewSource): NormalizedBbox {
  return {
    bbox_x: source.bbox_x,
    bbox_y: source.bbox_y,
    bbox_width: source.bbox_width,
    bbox_height: source.bbox_height,
  }
}

export function getReviewSelection(
  field: ReviewField | null,
  activeSourceId: string | null,
): ReviewSelection | null {
  if (field === null || field.sources.length === 0) {
    return null
  }

  const activeSource =
    field.sources.find((source) => source.ocr_block_id === activeSourceId) ??
    field.sources[0]

  return {
    activeSource,
    documentId: activeSource.document_id,
    pageNumber: activeSource.page_number,
    highlights: field.sources
      .filter(
        (source) =>
          source.document_id === activeSource.document_id &&
          source.page_number === activeSource.page_number,
      )
      .map(toBbox),
  }
}
