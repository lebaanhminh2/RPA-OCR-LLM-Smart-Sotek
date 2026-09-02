# M3-T7 — OCR handwriting feasibility evaluation

Evaluation date: 2026-09-02

## Scope

This evaluation checks the approved local OCR stack on synthetic,
non-personal loan-form fields that resemble handwriting. It is an early MVP
feasibility check, not a production accuracy benchmark and not evidence about
real customer handwriting.

The three fixed samples contain invented values only:

- [Name field](ocr-handwriting-samples/synthetic_handwriting_name.png)
- [Requested amount field](ocr-handwriting-samples/synthetic_handwriting_amount.png)
- [Monthly income field](ocr-handwriting-samples/synthetic_handwriting_income.png)

The printed labels use Arial. Handwritten values use the OFL-licensed Patrick
Hand and Dancing Script fonts from the official
[Google Fonts repository](https://github.com/google/fonts). The images include
slight rotation, a form border, and an underline. Font files are not part of
the repository.

## Runtime and offline method

- Adapter: real `LocalOCRAdapter`; no fake detector, recognizer, or OCR result.
- Detection: `PP-OCRv6_medium_det` with PaddleOCR 3.7.0 and PaddlePaddle 3.3.1.
- Recognition: official VietOCR `vgg_transformer` weights with VietOCR 0.3.12.
- Device: CPU.
- Model root used for this run:
  `C:\Users\lebaa\AppData\Local\SmartSotek\ocr-models\m3-baseline`.
- Before adapter initialization, socket name resolution, socket connection,
  and `requests` session calls were replaced with functions that raise an
  assertion. Initialization and all three inference calls completed without
  invoking those functions. Network was not needed during the evaluation.

Model asset hashes:

| Asset | SHA-256 |
|---|---|
| `PP-OCRv6_medium_det_infer.tar` | `144D0621E059566E5086E228829171591C144C2DEB07B2DAD4962214FBABFCF7` |
| Paddle `inference.pdiparams` | `85218D2E3D98F5A21C58B4220627BE923A97AEE5DB3CC71F39536AB31AC53960` |
| VietOCR `vgg-transformer.pth` | `380512193A8B6CBF6FAD80DEACDC9B6939D10D473D199892FC6408D13775EA59` |
| Merged VietOCR `config.yml` | `0CAA2CC6168702B8334AB9298DB15907AA4BCFF915065BAE472D31DDB9BBB871` |

## Results

`confidence` below is PaddleOCR's detection confidence. VietOCR 0.3.12 does
not provide a recognition-confidence value through the adapter's current
`predict` call, so these numbers must not be treated as text-accuracy scores.

| Sample | Expected handwritten value | Relevant OCR output | Detector confidence | Finding |
|---|---|---|---:|---|
| Requested amount | `Tám mươi triệu đồng` | `Tám mươi triệu đồng` | 0.872842 | Exact match. The printed label was also read correctly. |
| Monthly income | `Hai mươi lăm triệu đồng` | `Thu nhập hàng tháng: Hai mươi lăm triệu đồng` | 0.745116 | Handwritten value was exact; detector merged it with the printed label. |
| Name | `Người vay thử nghiệm` | `Người vay thứ nghiệm` | 0.882575 | One Vietnamese tone error: `thử` became `thứ`. |

The small printed synthetic header also produced errors such as `MẪU` → `MÃU`
and an extra `THỊ` token on two samples. These errors did not remove the main
field values, but they show that downstream extraction must tolerate noisy OCR
text and must not infer accuracy from detection confidence.

Fixture hashes:

| Sample | SHA-256 |
|---|---|
| `synthetic_handwriting_amount.png` | `F2E58BB2FE5E479D6A92A00851BB8D4C25F0B724465669075E3979F89598D7C2` |
| `synthetic_handwriting_income.png` | `20D1E22C4007B1202B927EE20D8DE5993C51A4118F397DCB96625E0F090414DC` |
| `synthetic_handwriting_name.png` | `AF479F7948DC39E957C6AC382FC0E19474D8636F6FBF523AADC31964D8006887` |

## Assessment

**MVP baseline: acceptable for a controlled synthetic demo, with known
limitations.** All three intended handwritten values were detected and
recognized; two were exact and one had a single tone-mark error. This satisfies
the M3 feasibility gate, but the small sample set and font-generated writing do
not establish production readiness for varied human handwriting.

VietOCR fine-tuning is **not a blocking recommendation from this limited run**.
Before production use, build a separate, explicitly approved benchmark using a
larger set of representative but non-sensitive handwriting. If that benchmark
shows material field loss or frequent character/diacritic errors, create a
dedicated VietOCR fine-tuning task. Do not change the OCR provider or checkpoint
without approval.
