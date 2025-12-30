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
MAX_FRAMES = 5        # number of frames to sample for comparison

OUTPUT_DIR = "comparison_output"


# =========================
# PREPROCESS COMPARISON
# =========================

class PreprocessComparison:
    def __init__(self):
        # Background subtractors
        self.mog2 = cv2.createBackgroundSubtractorMOG2(
            history=500, varThreshold=50, detectShadows=True
        )
        self.knn = cv2.createBackgroundSubtractorKNN(
            history=500, dist2Threshold=400, detectShadows=True
        )

        # Preprocessing methods
        self.methods = {
            "original": lambda f: f,
            "gaussian": lambda f: cv2.GaussianBlur(f, (5, 5), 0),
            "median": lambda f: cv2.medianBlur(f, 5),
            "clahe": self.apply_CLAHE,
            "hsv_v": self.extract_HSV_V,
        }

        # Metrics storage
        self.results = {
            m: {
                "fg_mog2": [],
                "fg_knn": [],
                "contours_mog2": [],
                "contours_knn": [],
            }
            for m in self.methods
        }

        # Output directory
        os.makedirs(OUTPUT_DIR, exist_ok=True)

    # ---------- PREPROCESSING METHODS ----------

    def apply_CLAHE(self, frame):
        lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        l2 = clahe.apply(l)
        lab2 = cv2.merge([l2, a, b])
        return cv2.cvtColor(lab2, cv2.COLOR_LAB2BGR)

    def extract_HSV_V(self, frame):
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        v = hsv[:, :, 2]
        return cv2.cvtColor(v, cv2.COLOR_GRAY2BGR)

    # ---------- METRIC CALCULATION ----------

    def count_metrics(self, mask):
        fg_pixels = cv2.countNonZero(mask)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        return fg_pixels, len(contours)

    # ---------- MAIN TEST FUNCTION ----------

    def test_frame(self, frame, frame_id):
        """
        Evaluate all preprocessing methods on a single frame.
        Saves:
          - one combined image with all methods stacked vertically
          - one image per method with 4 panels: original | pre | MOG2 | KNN
        """
        comparisons_row = []

        for name, func in self.methods.items():
            # 1. Preprocess
            pre_frame = func(frame)

            # 2. Background subtraction
            mask_mog2 = self.mog2.apply(pre_frame)
            mask_knn = self.knn.apply(pre_frame)

            # 3. Threshold shadows
            _, mask_mog2 = cv2.threshold(mask_mog2, 250, 255, cv2.THRESH_BINARY)
            _, mask_knn = cv2.threshold(mask_knn, 250, 255, cv2.THRESH_BINARY)

            # 4. Metrics
            fg_m2, con_m2 = self.count_metrics(mask_mog2)
            fg_knn, con_knn = self.count_metrics(mask_knn)

            self.results[name]["fg_mog2"].append(fg_m2)
            self.results[name]["fg_knn"].append(fg_knn)
            self.results[name]["contours_mog2"].append(con_m2)
            self.results[name]["contours_knn"].append(con_knn)

            # 5. Build visualization row (original | preprocessed | MOG2 | KNN)
            previews = [
                cv2.resize(frame, (300, 200)),
                cv2.resize(pre_frame, (300, 200)),
                cv2.resize(cv2.cvtColor(mask_mog2, cv2.COLOR_GRAY2BGR), (300, 200)),
                cv2.resize(cv2.cvtColor(mask_knn, cv2.COLOR_GRAY2BGR), (300, 200)),
            ]

            row = np.hstack(previews)
            comparisons_row.append(row)

            # Save per-method image for report: e.g. median_frame_10.jpg
            cv2.imwrite(
                os.path.join(OUTPUT_DIR, f"{name}_frame_{frame_id}.jpg"),
                row,
            )

        # Combine all methods vertically in one big image
        combined = np.vstack(comparisons_row)
        cv2.imwrite(
            os.path.join(OUTPUT_DIR, f"frame_{frame_id}.jpg"),
            combined,
        )

    # ---------- FINAL GRAPH OUTPUT ----------

    def create_graphs(self):
        for metric in ["fg_mog2", "fg_knn", "contours_mog2", "contours_knn"]:
            plt.figure(figsize=(12, 6))
            for method in self.methods:
                plt.plot(self.results[method][metric], label=method)
            plt.title(f"Metric: {metric}")
            plt.xlabel("Frame")
            plt.ylabel("Value")
            plt.legend()
            plt.grid(True)
            plt.tight_layout()
            plt.savefig(os.path.join(OUTPUT_DIR, f"{metric}.png"))
            plt.close()

    # ---------- SUMMARY TABLE ----------

    def print_summary(self):
        print("\n=== SUMMARY RESULTS ===\n")
        print(
            f"{'Method':<12} | {'Avg fg MOG2':<12} | "
            f"{'Avg fg KNN':<12} | {'Contours M2':<12} | {'Contours KNN':<12}"
        )
        print("-" * 70)
        for m in self.methods:
            d = self.results[m]
            print(
                f"{m:<12} | "
                f"{np.mean(d['fg_mog2']):<12.1f} | "
                f"{np.mean(d['fg_knn']):<12.1f} | "
                f"{np.mean(d['contours_mog2']):<12.1f} | "
                f"{np.mean(d['contours_knn']):<12.1f}"
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
    print("Starting blur/preprocess comparison on A11 stream...")
    comp = PreprocessComparison()
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
