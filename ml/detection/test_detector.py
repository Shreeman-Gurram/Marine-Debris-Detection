"""SONARIS DRISHTI YOLO Detector - Inference Test Script.

Usage:
    python ml/detection/test_detector.py <path-to-image>
"""

import argparse
from pathlib import Path
import sys
from ultralytics import YOLO


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run DRISHTI YOLO anomaly detection on a Side-Scan Sonar (SSS) image."
    )
    parser.add_argument(
        "image_path",
        type=str,
        help="Path to the input sonar image file",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Path to the YOLO model file (.pt). Defaults to models/best_detector.pt",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Directory to save annotated images. Defaults to outputs/detection_test",
    )
    parser.add_argument(
        "--conf",
        type=float,
        default=0.25,
        help="Confidence threshold for detections (default: 0.25)",
    )
    return parser.parse_args()


def resolve_paths(args):
    # Resolve project root (two levels up from ml/detection)
    project_root = Path(__file__).resolve().parent.parent.parent

    # Input image path
    image_path = Path(args.image_path)
    if not image_path.is_absolute():
        image_path = (Path.cwd() / image_path).resolve()

    # Model path
    if args.model:
        model_path = Path(args.model)
        if not model_path.is_absolute():
            model_path = (Path.cwd() / model_path).resolve()
    else:
        model_path = project_root / "models" / "best_detector.pt"

    # Output directory
    if args.output_dir:
        output_dir = Path(args.output_dir)
        if not output_dir.is_absolute():
            output_dir = (Path.cwd() / output_dir).resolve()
    else:
        output_dir = project_root / "outputs" / "detection_test"

    return image_path, model_path, output_dir


def main():
    args = parse_args()
    image_path, model_path, output_dir = resolve_paths(args)

    # Validate image path
    if not image_path.exists():
        print(f"Error: Input image not found: {image_path}", file=sys.stderr)
        sys.exit(1)

    # Validate model path
    if not model_path.exists():
        print(f"Error: Model file not found: {model_path}", file=sys.stderr)
        sys.exit(1)

    # Load model
    try:
        model = YOLO(str(model_path))
        print("Model loaded successfully")
        print(f"Model path: {model_path}")
        print(f"Model classes: {model.names}")
    except Exception as e:
        print(f"Error: Failed to load model: {e}", file=sys.stderr)
        sys.exit(1)

    # Run inference
    print(f"\nRunning inference on: {image_path}")
    results = model.predict(source=str(image_path), conf=args.conf, verbose=False)
    result = results[0]

    # Process detections
    num_detections = len(result.boxes)
    print(f"\nTotal number of detections: {num_detections}")

    if num_detections > 0:
        print("\nDetection details:")
        for idx, box in enumerate(result.boxes, start=1):
            cls_id = int(box.cls[0].item())
            class_name = model.names.get(cls_id, f"class_{cls_id}")
            confidence = float(box.conf[0].item())
            xyxy = [round(coord, 2) for coord in box.xyxy[0].tolist()]

            print(f"  [{idx}] Detected Class: {class_name}")
            print(f"      Confidence Score: {confidence:.4f}")
            print(f"      Bounding Box [x1, y1, x2, y2]: {xyxy}")
    else:
        print("No anomalies detected above confidence threshold.")

    # Ensure output directory exists and save annotated image
    output_dir.mkdir(parents=True, exist_ok=True)
    output_filename = f"annotated_{image_path.name}"
    output_path = output_dir / output_filename

    result.save(filename=str(output_path))
    print(f"\nAnnotated output image saved to: {output_path}")


if __name__ == "__main__":
    main()
