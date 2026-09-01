export type NormalizedBbox = {
  bbox_x: number
  bbox_y: number
  bbox_width: number
  bbox_height: number
}

export type DisplayedPageDimensions = {
  width: number
  height: number
}

export type PixelRectangle = {
  left: number
  top: number
  width: number
  height: number
}

export function normalizedBboxToPixelRectangle(
  bbox: NormalizedBbox,
  page: DisplayedPageDimensions,
): PixelRectangle {
  return {
    left: bbox.bbox_x * page.width,
    top: bbox.bbox_y * page.height,
    width: bbox.bbox_width * page.width,
    height: bbox.bbox_height * page.height,
  }
}
