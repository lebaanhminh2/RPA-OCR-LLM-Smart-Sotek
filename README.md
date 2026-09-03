# Smart Sotek IDP model assets

Nhánh `model-assets` chỉ lưu các model OCR cần để khôi phục môi trường local.
Các file binary lớn được quản lý bằng Git LFS và không nằm trên nhánh `main`,
nhằm tránh làm nặng deployment frontend trên Vercel.

## Nội dung

```text
model_weights/
├── paddle_detection/
│   ├── inference.yml
│   ├── inference.json
│   └── inference.pdiparams
└── vietocr/
    ├── config.yml
    └── weights.pth
```

Nguồn model:

- PaddleOCR `PP-OCRv6_medium_det`, giấy phép Apache-2.0.
- VietOCR `vgg_transformer`, dự án VietOCR của pbcquoc.

## Kiểm tra SHA-256

```text
85218D2E3D98F5A21C58B4220627BE923A97AEE5DB3CC71F39536AB31AC53960  paddle_detection/inference.pdiparams
0F1A7EC35DA36173529C7A60238B7F7919E3831929C3F700AD90AD4896ADECD5  paddle_detection/inference.json
7298D5EAD546584AF2504D03355F881AC7A7BC0EB1E282D3E159277C1D0AF871  paddle_detection/inference.yml
380512193A8B6CBF6FAD80DEACDC9B6939D10D473D199892FC6408D13775EA59  vietocr/weights.pth
```

Xem hướng dẫn phục hồi đầy đủ trên nhánh `main` tại `docs/RESTORE_PROJECT.md`.
