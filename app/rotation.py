"""Rotation logic sourced verbatim from the provided specification."""
from PIL import Image, ImageOps, ImageEnhance, ImageFilter 
from PIL import ImageFile; ImageFile.LOAD_TRUNCATED_IMAGES = True
import pytesseract
import re
from io import BytesIO
import os
import numpy as np

# ---------- helpers ----------
def _preprocess_for_ocr(img, min_size=1000):
    """Enhance image for better OCR on small/low-quality images."""
    # Convert to grayscale if not already
    if img.mode != 'L':
        img = img.convert('L')

    # Resize if too small (helps OCR)
    w, h = img.size
    if min(w, h) < min_size:
        scale = min_size / min(w, h)
        new_w, new_h = int(w * scale), int(h * scale)
        img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

    # Enhance contrast
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(2.0)

    # Sharpen
    img = img.filter(ImageFilter.SHARPEN)

    # Simple binarization (Otsu-like)
    arr = np.array(img)
    threshold = np.median(arr)
    arr = ((arr > threshold) * 255).astype(np.uint8)
    img = Image.fromarray(arr)

    return img

def _ocr_score(img, lang="fas+eng"):
    """OCR quality score with better handling of sparse text."""
    # Try preprocessed version
    processed = _preprocess_for_ocr(img.copy())

    d = pytesseract.image_to_data(processed, lang=lang, output_type=pytesseract.Output.DICT)

    score = 0
    word_count = 0
    high_conf_words = 0

    for txt, conf in zip(d.get("text", []), d.get("conf", [])):
        try:
            c = int(conf)
        except Exception:
            c = -1

        if txt and txt.strip() and c > 0:
            word_count += 1
            # Weight by confidence AND length
            score += c * len(txt.strip())
            if c > 70:  # High confidence threshold
                high_conf_words += 1

    # Bonus for having high-confidence words (better discriminator)
    if high_conf_words > 0:
        score += high_conf_words * 100

    # Penalty for very low word count (unreliable)
    if word_count < 2:
        score *= 0.5

    return score

def _try_osd_multiple_configs(img, lang="fas+eng"):
    """Try OSD with multiple PSM configurations."""
    configs_to_try = [
        "--psm 0",  # OSD only
        f"--psm 0 -l {lang}",  # OSD with language
        "--psm 1",  # Auto with OSD
    ]

    for config in configs_to_try:
        try:
            osd = pytesseract.image_to_osd(img, config=config)
            ccw = _parse_osd_ccw(osd)
            if ccw in (0, 90, 180, 270):
                return ccw
        except Exception:
            continue

    return None

def _parse_osd_ccw(osd_text: str) -> int | None:
    """Parse OSD output to get CCW rotation needed."""
    m = re.search(r"Rotate:\s+(\d+)", osd_text)
    if m:
        cw = int(m.group(1)) % 360
        return (360 - cw) % 360

    m = re.search(r"Orientation in degrees:\s+(\d+)", osd_text)
    if m:
        deg = int(m.group(1)) % 360
        return (360 - deg) % 360

    return None

def _smart_open(image):
    """Open from path/bytes/PIL.Image and honor EXIF orientation."""
    if isinstance(image, Image.Image):
        return ImageOps.exif_transpose(image)
    if isinstance(image, (bytes, bytearray)):
        return ImageOps.exif_transpose(Image.open(BytesIO(image)))
    if not os.path.exists(str(image)):
        raise FileNotFoundError(image)
    return ImageOps.exif_transpose(Image.open(image))

# ---------- main ----------
def auto_orient_for_ocr(image, lang="fas+eng", min_score_diff=200):
    """
    Auto-orient image for OCR with improved handling of small images.

    Args:
        image: Path, bytes, or PIL Image
        lang: Tesseract language codes
        min_score_diff: Minimum score difference to trust rotation (higher = more conservative)

    Returns:
        (rotated_image, ccw_degrees, cw_degrees, direction, confidence)
        - ccw_degrees ∈ {0,90,180,270}  -> rotate CCW by this to fix
        - cw_degrees  = (360 - ccw) % 360
        - direction in {'upright','left','right','upside-down'}
        - confidence in {'high','medium','low'}
    """
    img = _smart_open(image)

    # 1) Try OSD with multiple configurations
    ccw = _try_osd_multiple_configs(img, lang)
    if ccw in (0, 90, 180, 270):
        fixed = img.rotate(ccw, expand=True)
        cw = (360 - ccw) % 360
        label = {0:'upright', 90:'left', 180:'upside-down', 270:'right'}[ccw]
        return fixed, ccw, cw, label, 'high'

    # 2) Score all quarter-turns with improved scoring
    scores = {}
    for angle in (0, 90, 180, 270):
        rotated = img.rotate(angle, expand=True)
        scores[angle] = _ocr_score(rotated, lang=lang)

    # Find best rotation
    best_ccw = max(scores, key=scores.get)
    best_score = scores[best_ccw]

    # Check if the best score is significantly better than others
    other_scores = [s for a, s in scores.items() if a != best_ccw]
    if other_scores:
        second_best = max(other_scores)
        score_diff = best_score - second_best

        # Determine confidence
        if score_diff > min_score_diff * 2:
            confidence = 'high'
        elif score_diff > min_score_diff:
            confidence = 'medium'
        else:
            confidence = 'low'
            # If very uncertain and best is not upright, default to upright
            if best_ccw != 0 and score_diff < min_score_diff * 0.5:
                best_ccw = 0
    else:
        confidence = 'low'

    best_img = img.rotate(best_ccw, expand=True)
    cw = (360 - best_ccw) % 360
    label = {0:'upright', 90:'left', 180:'upside-down', 270:'right'}[best_ccw]

    return best_img, best_ccw, cw, label, confidence


# Example usage:
if __name__ == "__main__":
    rotated, ccw, cw, dir_label, conf = auto_orient_for_ocr(
        "39c1f6c9-dbe9-4030-80d7-b56e78056408-02036217-f88e-4743-93fd-ee26007f76d4-00000000-0000-0000-0000-000000000000.jpeg",
        lang="fas+eng"
    )
    rotated.save("oriented_output_test.jpg")
    print(f"Rotate CCW by {ccw}° ({dir_label})  ==  CW by {cw}°")
    print(f"Confidence: {conf}")
