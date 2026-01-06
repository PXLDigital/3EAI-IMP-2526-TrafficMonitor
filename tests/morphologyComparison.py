import cv2
import numpy as np
import os
import matplotlib.pyplot as plt
import subprocess

# =========================
# CONFIG
# =========================

M3U8_URL = "https://hls.media.verkeerscentrum.be/WEB_K_O5027_A11_ZELZATETNL__103.7_A.stream/chunklist.m3u8"
REFERER = "https://players.media.verkeerscentrum.be/"
ORIGIN = "https://players.media.verkeerscentrum.be"

WIDTH = 854
HEIGHT = 480
MAX_FRAMES = 50         # number of frames to sample for comparison

OUTPUT_DIR = "morphology_output"


# =========================
# MORPHOLOGY COMPARISON
# =========================

class MorphologyComparison:
    def __init__(self):
        # Background subtractors
        self.bg_mog2 = cv2.createBackgroundSubtractorMOG2(
            history=500, varThreshold=50, detectShadows=True
        )
        self.bg_knn = cv2.createBackgroundSubtractorKNN(
            history=500, dist2Threshold=400, detectShadows=True
        )

        # Kernels (same idea as in complete_script)
        self.kernel_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
        self.kernel_dilate = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
        self.kernel_open = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        self.kernel_erode = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (1, 1))

        # Iterations (you can mirror complete_script values)
        self.it_close = 1
        self.it_dilate = 1
        self.it_open = 3
        self.it_erode = 1

        # Morphology variants to compare
        self.variants = {
            "no_morph": self.no_morph,
            "close_only": self.close_only,
            "close_dilate": self.close_dilate,
            "full_pipeline": self.full_pipeline,
        }

        # Metrics storage: per variant
        self.results = {
            name: {
                "fg_pixels": [],
                "contours": [],
            }
            for name in self.variants
        }

        os.makedirs(OUTPUT_DIR, exist_ok=True)

    # ---------- PREPROCESSING (BEST FROM YOUR PIPELINE) ----------

    def preprocess(self, frame):
        # === 1. Preprocessing: LAB + CLAHE ===
        lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
        # split the 3-channel LAB image
        l, a, b = cv2.split(lab)

        clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
        lEnhanced = clahe.apply(l)
        labEnhanced = cv2.merge((lEnhanced, a, b))
        enhanced = cv2.cvtColor(labEnhanced, cv2.COLOR_LAB2BGR)

        enhanced = cv2.convertScaleAbs(enhanced, alpha=1.05, beta=5)
        blurred = cv2.medianBlur(enhanced, 5)
        return blurred


    # ---------- BACKGROUND SUBTRACTION (MOG2 + KNN + AND) ----------

    def background_subtraction(self, frame):
        blurred = self.preprocess(frame)

        fg_mog2 = self.bg_mog2.apply(blurred)
        fg_knn = self.bg_knn.apply(blurred)

        # thresholds (same idea as complete_script)
        _, fg_mog2 = cv2.threshold(fg_mog2, 150, 255, cv2.THRESH_BINARY)
        _, fg_knn = cv2.threshold(fg_knn, 180, 255, cv2.THRESH_BINARY)

        fg_mask = cv2.bitwise_and(fg_mog2, fg_knn)
        return fg_mask, fg_mog2, fg_knn

    # ---------- MORPHOLOGY VARIANTS ----------

    def no_morph(self, mask):
        return mask

    def close_only(self, mask):
        fg = cv2.morphologyEx(
            mask, cv2.MORPH_CLOSE, self.kernel_close, iterations=self.it_close
        )
        return fg

    def close_dilate(self, mask):
        fg = cv2.morphologyEx(
            mask, cv2.MORPH_CLOSE, self.kernel_close, iterations=self.it_close
        )
        fg = cv2.dilate(fg, self.kernel_dilate, iterations=self.it_dilate)
        return fg

    def full_pipeline(self, mask):
        fg = cv2.morphologyEx(
            mask, cv2.MORPH_CLOSE, self.kernel_close, iterations=self.it_close
        )
        fg = cv2.dilate(fg, self.kernel_dilate, iterations=self.it_dilate)
        fg = cv2.morphologyEx(
            fg, cv2.MORPH_OPEN, self.kernel_open, iterations=self.it_open
        )
        fg = cv2.erode(fg, self.kernel_erode, iterations=self.it_erode)
        return fg

    # ---------- METRIC CALCULATION ----------

    def count_metrics(self, mask):
        fg_pixels = cv2.countNonZero(mask)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        return fg_pixels, len(contours)

    # ---------- MAIN TEST FUNCTION ----------

    def test_frame(self, frame, frame_id):
        """
        For one frame:
          - Compute fg_mask from bg subtraction
          - Apply each morphology variant
          - Save side-by-side image
          - Store metrics
        """
        fg_mask, fg_mog2, fg_knn = self.background_subtraction(frame)

        panels = []

        # First panel: raw AND mask (before morphology) for reference
        base = cv2.resize(cv2.cvtColor(fg_mask, cv2.COLOR_GRAY2BGR), (300, 200))
        panels.append(base)

        # Apply each variant
        for name, func in self.variants.items():
            morphed = func(fg_mask)
            fg_px, cnts = self.count_metrics(morphed)

            self.results[name]["fg_pixels"].append(fg_px)
            self.results[name]["contours"].append(cnts)

            color = cv2.resize(
                cv2.cvtColor(morphed, cv2.COLOR_GRAY2BGR), (300, 200)
            )
            panels.append(color)

            # Save per-variant standalone image (for detailed report)
            cv2.imwrite(
                os.path.join(OUTPUT_DIR, f"{name}_frame_{frame_id}.jpg"),
                color,
            )

        # Combine as one horizontal strip:
        # [fg_mask_raw | no_morph | close_only | close_dilate | full_pipeline]
        comparison = np.hstack(panels)
        cv2.imwrite(
            os.path.join(OUTPUT_DIR, f"morph_frame_{frame_id}.jpg"),
            comparison,
        )

    # ---------- GRAPHS ----------

    def create_graphs(self):
        # fg_pixels plot
        plt.figure(figsize=(12, 6))
        for name in self.variants:
            plt.plot(self.results[name]["fg_pixels"], label=name)
        plt.title("Foreground pixels vs frame (morphology variants)")
        plt.xlabel("Frame")
        plt.ylabel("Foreground pixels")
        plt.legend()
        plt.grid(True)
        plt.tight_layout()
        plt.savefig(os.path.join(OUTPUT_DIR, "fg_pixels.png"))
        plt.close()

        # contours plot
        plt.figure(figsize=(12, 6))
        for name in self.variants:
            plt.plot(self.results[name]["contours"], label=name)
        plt.title("Contour count vs frame (morphology variants)")
        plt.xlabel("Frame")
        plt.ylabel("Contours")
        plt.legend()
        plt.grid(True)
        plt.tight_layout()
        plt.savefig(os.path.join(OUTPUT_DIR, "contours.png"))
        plt.close()

    # ---------- SUMMARY TABLE ----------

    def print_summary(self):
        print("\n=== MORPHOLOGY SUMMARY RESULTS ===\n")
        print(
            f"{'Variant':<15} | {'Avg fg px':<12} | {'Avg contours':<12}"
        )
        print("-" * 45)
        for name in self.variants:
            d = self.results[name]
            print(
                f"{name:<15} | "
                f"{np.mean(d['fg_pixels']):<12.1f} | "
                f"{np.mean(d['contours']):<12.1f}"
            )


# =========================
# VIDEO INPUT (A11 STREAM)
# =========================

def create_ffmpeg_process():
    headers = f"Referer: {REFERER}\r\nOrigin: {ORIGIN}\r\n"
    command = [
        "ffmpeg", "-headers", headers,
        "-fflags", "nobuffer", "-flags", "low_delay",
        "-i", M3U8_URL,
        "-vf", f"scale={WIDTH}:{HEIGHT}",
        "-f", "rawvideo", "-pix_fmt", "bgr24",
        "-an", "-sn", "-"
    ]
    return subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        bufsize=10 ** 7,
    )


def get_frame(process):
    frame_size = WIDTH * HEIGHT * 3
    raw = process.stdout.read(frame_size)
    if not raw or len(raw) < frame_size:
        return None
    frame = np.frombuffer(raw, np.uint8).reshape((HEIGHT, WIDTH, 3))
    return frame


# =========================
# MAIN
# =========================

def main():
    print("Starting morphology comparison on A11 stream...")
    comp = MorphologyComparison()
    proc = create_ffmpeg_process()

    frame_id = 0

    while frame_id < MAX_FRAMES:
        frame = get_frame(proc)
        if frame is None:
            print("No more frames or stream ended.")
            break

        comp.test_frame(frame, frame_id)
        frame_id += 1

    proc.terminate()

    comp.create_graphs()
    comp.print_summary()
    print(f"\nDone. Results saved in '{OUTPUT_DIR}' directory.\n")


if __name__ == "__main__":
    main()
