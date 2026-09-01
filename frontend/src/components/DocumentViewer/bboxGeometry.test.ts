import { describe, expect, it } from 'vitest'

import {
  normalizedBboxToPixelRectangle,
  type NormalizedBbox,
} from './bboxGeometry'

const typicalBbox: NormalizedBbox = {
  bbox_x: 0.12,
  bbox_y: 0.34,
  bbox_width: 0.3,
  bbox_height: 0.04,
}

describe('normalizedBboxToPixelRectangle', () => {
  it('converts a typical normalized bbox to displayed pixels', () => {
    expect(
      normalizedBboxToPixelRectangle(typicalBbox, {
        width: 1000,
        height: 2000,
      }),
    ).toEqual({
      left: 120,
      top: 680,
      width: 300,
      height: 80,
    })
  })

  it('scales the rectangle with the displayed page dimensions', () => {
    const baseRectangle = normalizedBboxToPixelRectangle(typicalBbox, {
      width: 1000,
      height: 2000,
    })
    const doubledRectangle = normalizedBboxToPixelRectangle(typicalBbox, {
      width: 2000,
      height: 4000,
    })

    expect(doubledRectangle).toEqual({
      left: baseRectangle.left * 2,
      top: baseRectangle.top * 2,
      width: baseRectangle.width * 2,
      height: baseRectangle.height * 2,
    })
  })

  it('maps a full-page bbox to the full displayed page', () => {
    expect(
      normalizedBboxToPixelRectangle(
        {
          bbox_x: 0,
          bbox_y: 0,
          bbox_width: 1,
          bbox_height: 1,
        },
        { width: 640, height: 480 },
      ),
    ).toEqual({
      left: 0,
      top: 0,
      width: 640,
      height: 480,
    })
  })
})
