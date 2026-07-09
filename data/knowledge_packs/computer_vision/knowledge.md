# Computer Vision

## Image representation
- Tensor `(C, H, W)` in PyTorch (channels-first); TF/PIL/OpenCV use `(H, W, C)`. Batch = `(N, C, H, W)`.
- Pixels `uint8 [0,255]` → scale to float `[0,1]` (`/255`), then **normalize** per-channel `(x-μ)/σ`. ImageNet stats: `μ=[0.485,0.456,0.406]`, `σ=[0.229,0.224,0.225]`.
- **OpenCV reads BGR**, PIL/matplotlib read RGB → convert or channels get swapped. Grayscale = 1 channel; RGBA = 4.

## CNNs
- **Convolution**: learnable `k×k` filter slides over input, shares weights → translation equivariance, few params. Each filter → one output feature map.
- Output size: `⌊(H + 2p − k)/s⌋ + 1` (padding `p`, stride `s`). `padding='same'` keeps size (`p=k//2`, s=1). Stride>1 downsamples.
- Params per conv layer = `(k·k·C_in + 1)·C_out`.
- **Pooling** (max/avg) downsamples, adds translation invariance, no params. Global average pooling → classifier head (replaces huge FC).
- **Receptive field** grows with depth/stride/dilation — deeper neurons "see" more of the image.
- 1×1 conv = channel mixing / dimensionality change.

## Classic architectures
- **LeNet/AlexNet** → **VGG** (stacked 3×3). **ResNet**: residual blocks `x+F(x)` enable 50/101/152 layers, solves degradation/vanishing grads — strong default backbone.
- **Inception/GoogLeNet** (multi-scale), **DenseNet** (dense connections), **MobileNet/EfficientNet** (depthwise-separable convs, compound scaling — efficient/mobile), **ConvNeXt** (modernized CNN).
- **Vision Transformer (ViT)**: split image into patches (16×16) → linear embed → transformer encoder + `[CLS]`; needs large data or strong augmentation/distillation (DeiT); beats CNNs at scale. Hybrids/Swin add hierarchy + local windows.

## Tasks
- **Classification**: image → single label; softmax head.
- **Object detection**: bounding boxes + classes.
  - **Two-stage** (Faster R-CNN): region proposals (RPN) → classify+refine; accurate, slower.
  - **One-stage** (YOLO, SSD, RetinaNet): dense predictions in one pass; fast, real-time. YOLO grid + anchor/anchor-free.
  - **DETR**: transformer, set prediction, no NMS/anchors.
- **Segmentation**:
  - **Semantic** (per-pixel class): U-Net (encoder-decoder + skips), DeepLab (atrous/ASPP), FCN.
  - **Instance** (per-object masks): Mask R-CNN (detection + mask head).
  - **Panoptic** = semantic + instance.
- **Keypoints/pose**: heatmap regression (HRNet, OpenPose). **Depth, optical flow, tracking, OCR**.

## Data augmentation
- Geometric: flip (horizontal usually safe; vertical only if orientation-agnostic), rotate, crop/`RandomResizedCrop`, scale, translate, affine.
- Photometric: brightness/contrast/hue/saturation jitter, gaussian noise/blur, grayscale.
- Occlusion/mixing: Cutout/random erasing, **Mixup** (blend images+labels), **CutMix**, **RandAugment/AutoAugment**, **TrivialAugment**.
- **Apply to train only**; val/test get deterministic resize+normalize. Detection/segmentation: transform boxes/masks together with the image.

## Transfer learning
- Start from ImageNet-pretrained backbone; replace head for your classes.
- **Feature extraction**: freeze backbone, train head (small data). **Fine-tuning**: unfreeze some/all layers, low LR (1e-4 to 1e-5), often discriminative/layerwise LR.
- Huge speedup + accuracy on small datasets; match preprocessing (resize + normalization) to the pretrained model.

## Metrics
- Classification: accuracy, top-5, F1, confusion matrix.
- Detection: **IoU** `area(∩)/area(∪)` of boxes; a prediction is TP if IoU≥threshold (0.5) and class correct. **AP** = area under precision–recall curve per class; **mAP** = mean over classes. COCO **mAP@[0.5:0.95]** averages IoU thresholds; also mAP@0.5.
- Segmentation: **IoU/Jaccard**, **mIoU** (mean over classes), **Dice** `2|A∩B|/(|A|+|B|)` (F1 of pixels), pixel accuracy.
- Detection post-processing: **NMS** removes overlapping duplicate boxes above IoU threshold; confidence threshold trades precision/recall.

## Preprocessing / inference pipeline
- Train: `Resize/RandomResizedCrop → augment → ToTensor → Normalize`.
- Inference: `Resize → CenterCrop → ToTensor → Normalize` (same μ/σ), `model.eval()`, `torch.no_grad()`.
- Resize preserving aspect ratio (letterbox/pad) for detection; square resize distorts. Batch requires equal sizes — pad or resize.
- TTA (test-time augmentation) averages flips/crops. Export ONNX/TensorRT for deployment; quantize/prune for edge.

## Loss functions by task
- Classification: cross-entropy (+ label smoothing 0.1). Multi-label: BCE-with-logits.
- Detection: classification (focal loss for dense one-stage — handles fg/bg imbalance) + box regression (Smooth L1 / IoU / GIoU / DIoU / CIoU).
- Segmentation: pixel cross-entropy + **Dice loss** / Tversky (imbalanced masks); combine (CE+Dice) for stability.
- Keypoints: MSE on Gaussian heatmaps. Metric learning: triplet / contrastive / ArcFace (face recognition).

## Detection mechanics
- Anchors: predefined boxes at multiple scales/ratios per location; anchor-free (FCOS, CenterNet) predict box directly. Feature Pyramid Network (FPN) fuses multi-scale features for small+large objects.
- Assign GT to anchors by IoU; predict class + box offsets + objectness. **NMS** per class removes duplicates (IoU threshold ~0.5); Soft-NMS decays instead of dropping.
- YOLO: grid cells predict boxes+class in one pass, real-time. Faster R-CNN: RPN proposals → RoIAlign → head.

## Segmentation mechanics
- U-Net: symmetric encoder-decoder + skip connections restore spatial detail; standard for medical/small data.
- Atrous/dilated conv (DeepLab ASPP) enlarges receptive field without downsampling. Upsample via transposed conv / bilinear + conv.
- Output `(N, num_classes, H, W)` logits → per-pixel argmax. Instance: Mask R-CNN adds a per-RoI mask branch.

## Vision Transformers detail
- Image → patches (16×16) → linear projection + position embeddings + `[CLS]` → transformer encoder. Data-hungry; needs large pretraining or DeiT distillation / heavy augmentation on small data.
- **Swin**: hierarchical, shifted local windows → linear complexity, works as detection/segmentation backbone. ConvNeXt shows modernized CNNs match ViTs. CLIP: contrastive image-text pretraining → zero-shot classification.

## Training + deployment recipe
- Backbone: ImageNet-pretrained ResNet/EfficientNet/ViT. Head per task. AdamW/SGD+momentum, cosine LR + warmup, weight decay, label smoothing, strong augmentation (RandAugment/Mixup/CutMix).
- Mixed precision, batch size to fill VRAM, EMA of weights for stability. Validate mIoU/mAP each epoch; checkpoint best.
- Deploy: `eval()`+`inference_mode()`, export ONNX/TensorRT, int8 quantization/pruning for edge, batch + resize consistently, TTA for last accuracy points.

## Convolution arithmetic + shapes
- Output spatial size `O = ⌊(H + 2p − d(k−1) − 1)/s⌋ + 1` (dilation `d`, else `⌊(H+2p−k)/s⌋+1`).
- `Conv2d(in_ch, out_ch, kernel, stride, padding)` → output `(N, out_ch, O, O)`. Params `= out_ch·(in_ch·k·k + 1)`.
- Downsample paths: stride-2 conv or pooling halve H,W and typically double channels. Track spatial size + channels through the net; a wrong flatten dim into the FC head is the classic bug.
- Transposed conv upsamples (`ConvTranspose2d`); prefer bilinear upsample + 3×3 conv to avoid checkerboard artifacts.

## Backbones + when to use
- **ResNet-18/50** — reliable default, fast, well-pretrained. **EfficientNet/ConvNeXt** — better accuracy/FLOP. **MobileNetV3** — mobile/edge. **ViT/Swin** — SOTA at scale, need big data or strong aug/distillation. **CLIP** — zero-shot + open-vocabulary.
- Match input resolution + normalization to the backbone's pretraining (e.g. 224×224, ImageNet μ/σ). Higher resolution helps small objects but costs compute.

## Augmentation library notes
- `torchvision.transforms` / **albumentations** (bbox+mask aware) / **kornia** (GPU, differentiable).
- Detection/segmentation: transform image AND targets together; drop boxes that fall outside crops; keep masks aligned.
- Tune augmentation strength to dataset size (more data → lighter aug). Heavy aug (Mixup/CutMix/RandAugment) regularizes small datasets but can hurt if labels/geometry break.

## Evaluation detail
- **IoU** threshold defines a match; sweep confidence to build the PR curve → **AP** per class → **mAP**. COCO reports mAP@[0.5:0.95] (avg over 10 IoU thresholds) plus AP-small/medium/large.
- Segmentation: per-class IoU → mIoU; Dice for overlap; boundary F1 for edge quality. Always report per-class, not just mean, to expose rare-class failure.
- Calibrate confidence thresholds + NMS IoU on validation; they materially shift precision/recall.

## Inference pipeline checklist
- Same resize + normalization (μ/σ, /255, RGB order) as training. `model.eval()` + `inference_mode()`.
- Letterbox/pad to preserve aspect for detection; batch requires equal sizes. Undo letterbox when mapping boxes back to original coords.
- Deploy: ONNX/TensorRT export, int8 quantization/pruning for edge, half precision on GPU, TTA (flips/multi-scale) for a final accuracy bump.

## Pitfalls -> Fix
- **Normalization mismatch** (train stats ≠ inference, or forgot /255) -> use identical μ/σ and scaling everywhere; match pretrained model's stats.
- **BGR vs RGB** (OpenCV) -> `cv2.cvtColor(img, COLOR_BGR2RGB)`; check channel order end-to-end.
- **Aspect-ratio distortion from square resize** -> letterbox/pad, especially for detection.
- **Augmentation applied to val/test** -> deterministic transforms only for eval.
- **Boxes/masks not transformed with image** -> use albumentations/detection transforms that update targets.
- **Class imbalance / tiny objects in detection** -> focal loss, hard-negative mining, anchor tuning, oversample, multi-scale.
- **Data leakage** (same scene/patient across splits, near-duplicate frames) -> group split by source.
- **Wrong tensor layout** `(H,W,C)` into a `(N,C,H,W)` model -> `permute`/`ToTensor`.
- **Label off-by-one / background class** -> confirm class index convention (0 background vs 0 first class).
- **Reporting accuracy on imbalanced classes** -> per-class F1/IoU, mAP, confusion matrix.
- **Forgetting model.eval()** (BatchNorm/Dropout) -> set eval + no_grad at inference.
- **Comparing mAP across different IoU thresholds/definitions** -> state metric (mAP@0.5 vs @[0.5:0.95]) and dataset convention.
- **Overfitting small dataset from scratch** -> transfer learning + strong augmentation.
- **NMS/confidence thresholds untuned** -> sweep on val; too-high conf drops recall, too-low IoU merges objects.
