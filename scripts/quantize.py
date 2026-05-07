"""Convert a fine-tuned LFM2.5-VL-450M checkpoint to quantized GGUF.

Mirrors `wildfire-prevention/scripts/quantize.py` from the Liquid cookbook.
Produces two artifacts required by llama-server for VLM inference:
  1. Quantized backbone GGUF  (language model)
  2. mmproj GGUF              (vision tower + multimodal projector)

Will clone llama.cpp if not present and build llama-quantize. If a system
`llama-quantize` is on PATH (e.g. installed via Homebrew), it is used
instead of building from source.

Prerequisites (cannot be automated):
  - git
  - cmake (only if no system llama-quantize and no prebuilt one in llama.cpp)
  - A C++ compiler (macOS: run `xcode-select --install` if missing)

Usage:
    uv run scripts/quantize.py \\
        --checkpoint <path-to-leap-finetune-output-dir> \\
        --output ./outputs/zamba-deforestation-Q8_0.gguf

    # Different quantization level
    uv run scripts/quantize.py \\
        --checkpoint <path-to-leap-finetune-output-dir> \\
        --output ./outputs/zamba-deforestation-Q4_K_M.gguf \\
        --quant Q4_K_M
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
LLAMA_CPP_DIR = REPO_ROOT / "llama.cpp"
LLAMA_CPP_REPO = "https://github.com/ggerganov/llama.cpp"
VALID_QUANTS = ["Q4_0", "Q4_K_M", "Q5_K_M", "Q6_K", "Q8_0", "F16"]


def run(cmd: list[str], cwd: Path | None = None) -> None:
    result = subprocess.run(cmd, cwd=cwd)
    if result.returncode != 0:
        print(f"Command failed: {' '.join(cmd)}")
        sys.exit(result.returncode)


def check_build_tools(need_cmake: bool) -> None:
    tools = ["git"]
    if need_cmake:
        tools += ["cmake", "c++"]
    for tool in tools:
        if not shutil.which(tool):
            print(f"Missing required tool: {tool}")
            if tool in ("cmake", "c++"):
                print("  On macOS: run `xcode-select --install` and `brew install cmake`")
            sys.exit(1)


def find_quantize_bin() -> Path:
    """Resolve a usable llama-quantize binary, building if necessary."""
    local = LLAMA_CPP_DIR / "build" / "bin" / "llama-quantize"
    if local.exists():
        return local
    system = shutil.which("llama-quantize")
    if system:
        return Path(system)

    check_build_tools(need_cmake=True)
    if not LLAMA_CPP_DIR.exists():
        print(f"Cloning llama.cpp into {LLAMA_CPP_DIR} ...")
        run(["git", "clone", "--depth=1", LLAMA_CPP_REPO, str(LLAMA_CPP_DIR)])
    print("Building llama-quantize ...")
    run(["cmake", "-B", "build"], cwd=LLAMA_CPP_DIR)
    run(["cmake", "--build", "build", "--config", "Release", "-t", "llama-quantize"], cwd=LLAMA_CPP_DIR)
    return local


def ensure_llama_cpp_repo() -> None:
    """Ensure the llama.cpp source tree exists (needed for convert_hf_to_gguf.py)."""
    if not LLAMA_CPP_DIR.exists():
        check_build_tools(need_cmake=False)
        print(f"Cloning llama.cpp into {LLAMA_CPP_DIR} ...")
        run(["git", "clone", "--depth=1", LLAMA_CPP_REPO, str(LLAMA_CPP_DIR)])


def maybe_strip_redundant_lm_head(checkpoint: Path) -> None:
    """Drop a redundant top-level `lm_head.weight` if it exactly matches
    `model.language_model.embed_tokens.weight`.

    leap-finetune + DeepSpeed ZeRO can break the `tie_word_embeddings: true`
    tying during consolidation, leaving `lm_head.weight` as a separate tensor
    in `model.safetensors`. The llama.cpp `--mmproj` converter then chokes on
    it (it filters `language_model.*` but not top-level `lm_head.*`).
    Stripping the duplicate restores the canonical HF layout.
    """
    safetensors_path = checkpoint / "model.safetensors"
    if not safetensors_path.exists():
        return

    from safetensors.torch import safe_open, save_file
    import torch

    with safe_open(str(safetensors_path), framework="pt") as f:
        keys = list(f.keys())
        if "lm_head.weight" not in keys:
            return
        if "model.language_model.embed_tokens.weight" not in keys:
            print("WARN: lm_head.weight present but no embed_tokens to compare against; "
                  "leaving safetensors unchanged.")
            return
        lm = f.get_tensor("lm_head.weight")
        emb = f.get_tensor("model.language_model.embed_tokens.weight")
        if not torch.equal(lm, emb):
            print("WARN: lm_head.weight differs from embed_tokens; not safe to strip.")
            return
        metadata = f.metadata() or {}
        tensors = {k: f.get_tensor(k) for k in keys if k != "lm_head.weight"}

    backup = safetensors_path.with_suffix(".safetensors.bak")
    if not backup.exists():
        shutil.copy2(safetensors_path, backup)
    save_file(tensors, str(safetensors_path), metadata=metadata)
    print(f"stripped redundant lm_head.weight (was tied to embed_tokens). "
          f"backup at {backup.name}")


def convert_to_f16(checkpoint: Path, f16_output: Path) -> None:
    convert_script = LLAMA_CPP_DIR / "convert_hf_to_gguf.py"
    print(f"Converting backbone to F16 GGUF: {f16_output} ...")
    run([
        sys.executable,
        str(convert_script),
        str(checkpoint),
        "--outtype", "f16",
        "--outfile", str(f16_output),
    ])


def convert_to_mmproj(checkpoint: Path, mmproj_output: Path) -> None:
    convert_script = LLAMA_CPP_DIR / "convert_hf_to_gguf.py"
    print(f"Converting vision components to mmproj GGUF: {mmproj_output} ...")
    run([
        sys.executable,
        str(convert_script),
        str(checkpoint),
        "--mmproj",
        "--outfile", str(mmproj_output),
    ])


def quantize(f16_path: Path, output: Path, quant: str, quantize_bin: Path) -> None:
    if quant == "F16":
        f16_path.rename(output)
        return
    print(f"Quantizing to {quant}: {output} ...")
    run([str(quantize_bin), str(f16_path), str(output), quant])


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert a fine-tuned LFM2.5-VL-450M checkpoint to quantized GGUF."
    )
    parser.add_argument("--checkpoint", required=True, metavar="PATH",
                        help="Path to the HuggingFace checkpoint directory.")
    parser.add_argument("--output", required=True, metavar="PATH",
                        help="Output path for the backbone GGUF (e.g. ./outputs/model-Q8_0.gguf). "
                             "The mmproj is written alongside it as mmproj-<stem>.gguf.")
    parser.add_argument("--quant", default="Q8_0", choices=VALID_QUANTS,
                        help="Quantization type for the backbone (default: Q8_0). "
                             "The mmproj is always F16.")
    args = parser.parse_args()

    checkpoint = Path(args.checkpoint).resolve()
    output = Path(args.output).resolve()

    if not checkpoint.is_dir():
        print(f"Checkpoint directory not found: {checkpoint}")
        sys.exit(1)

    output.parent.mkdir(parents=True, exist_ok=True)

    f16_path = output.parent / (output.stem + "-F16.gguf")
    mmproj = output.parent / f"mmproj-{output.stem}.gguf"

    ensure_llama_cpp_repo()
    quantize_bin = find_quantize_bin()
    maybe_strip_redundant_lm_head(checkpoint)

    convert_to_f16(checkpoint, f16_path)
    try:
        quantize(f16_path, output, args.quant, quantize_bin)
    finally:
        if args.quant != "F16" and f16_path.exists():
            f16_path.unlink()

    convert_to_mmproj(checkpoint, mmproj)

    print()
    print("Done.")
    print(f"  Backbone : {output}")
    print(f"  mmproj   : {mmproj}")
    print()
    print("To evaluate with the local backend:")
    print(f"  uv run scripts/evaluate.py --backend local --model {output} --mmproj {mmproj} --split test")


if __name__ == "__main__":
    main()
