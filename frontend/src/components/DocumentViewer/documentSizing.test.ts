import { describe, expect, it } from 'vitest'

import { fitDocumentScale } from './documentSizing'

describe('fitDocumentScale', () => {
  it('shrinks an oversized document to the available width', () => {
    expect(fitDocumentScale(2000, 1000, 1)).toBe(0.5)
  })

  it('does not enlarge a document that already fits', () => {
    expect(fitDocumentScale(600, 1000, 1)).toBe(1)
  })

  it('applies zoom relative to the fitted size', () => {
    expect(fitDocumentScale(2000, 1000, 1.5)).toBe(0.75)
  })

  it('rejects dimensions that cannot produce a usable scale', () => {
    expect(() => fitDocumentScale(0, 1000, 1)).toThrow(RangeError)
    expect(() => fitDocumentScale(1000, Number.NaN, 1)).toThrow(RangeError)
    expect(() => fitDocumentScale(1000, 1000, 0)).toThrow(RangeError)
  })
})
