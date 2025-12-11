# ml-inference/convert_checkpoint_to_state_dict.py
"""
Convert an arbitrary PyTorch checkpoint to a clean state_dict compatible with a ResNet18 skeleton.
Usage:
    python convert_checkpoint_to_state_dict.py --input models/best_model.pth --output models/best_model_state_dict.pth

If torch.load fails because of PyTorch safe globals, set env INFERENCE_ALLOW_UNSAFE_LOAD=1 to let the script
attempt a fallback load (may execute code inside the checkpoint — only do this if you trust the file).
"""
import os
import argparse
import torch
import re
import json
from pathlib import Path
from torchvision.models import resnet18

def try_torch_load(path, allow_unsafe=False):
    try:
        return torch.load(str(path), map_location="cpu")
    except Exception as e:
        print("Initial torch.load failed:", e)
        if not allow_unsafe:
            raise
        print("Attempting unsafe torch.load(weights_only=False) (ONLY do this if you trust the checkpoint)")
        # unsafe fallback
        return torch.load(str(path), map_location="cpu", weights_only=False)

def extract_state_dict(ckpt):
    """
    Normalize checkpoint shapes:
     - if ckpt is a module -> ckpt.state_dict()
     - if ckpt is a dict and contains 'state_dict' or 'model_state_dict', extract that
     - otherwise, if dict of tensors, return as-is
    """
    if hasattr(ckpt, "state_dict"):
        print("Checkpoint is a model object; extracting state_dict()")
        return ckpt.state_dict()
    if isinstance(ckpt, dict):
        if "state_dict" in ckpt and isinstance(ckpt["state_dict"], dict):
            return ckpt["state_dict"]
        if "model_state_dict" in ckpt and isinstance(ckpt["model_state_dict"], dict):
            return ckpt["model_state_dict"]
        # assume it's already a state_dict-like mapping
        return ckpt
    raise RuntimeError("Unsupported checkpoint type: " + str(type(ckpt)))

def remap_keys_for_fc(sd: dict, skeleton_keys: set):
    """
    Heuristic remapping:
    - If skeleton expects 'fc.weight' and sd has 'fc.1.weight' or 'fc.0.weight', map them.
    - Also handle 'module.' prefix and 'classifier' alias.
    - Returns a **new** state_dict with remapped keys (keeps original keys where no remap needed).
    """
    new = {}
    keys = list(sd.keys())

    def strip_module(k): return k[len("module."):] if k.startswith("module.") else k

    # quick normalized keys
    normalized = {strip_module(k): k for k in keys}

    for sk in skeleton_keys:
        # if already present in sd (maybe with module. prefix), keep it
        if sk in normalized:
            continue
        # look for patterns like fc.1.weight or fc.0.weight or classifier.1.weight
        # candidate suffixes to try
        candidates = []
        base = sk.rsplit(".", 1)[0]  # e.g. 'fc'
        suffix = sk.rsplit(".", 1)[1]  # 'weight' or 'bias'
        # try base + '.1.' + suffix
        candidates.append(f"{base}.1.{suffix}")
        candidates.append(f"{base}.0.{suffix}")
        # try classifier.* pattern
        candidates.append(f"classifier.1.{suffix}")
        candidates.append(f"classifier.0.{suffix}")
        # try head.* pattern
        candidates.append(f"head.1.{suffix}")
        candidates.append(f"head.0.{suffix}")

        found = None
        for c in candidates:
            # also check module.<c>
            if c in normalized:
                found = normalized[c]
                break
            m = "module." + c
            if m in normalized:
                found = normalized[m]
                break
        if found:
            # remap all entries that share that numeric index (fc.1.weight & fc.1.bias => fc.weight & fc.bias)
            # find numeric index inside found (e.g. '...fc.1.weight')
            m = re.search(r"(.*\b(fc|classifier|head)\.)(\d+)\.(.+)$", strip_module(found))
            if m:
                prefix = m.group(1)  # e.g. '...fc.'
                idx = m.group(3)     # e.g. '1'
                rest = m.group(4)    # e.g. 'weight' or 'bias'
                # for all keys in sd that contain prefix+idx+., map to prefix + rest (remove the index)
                for k in keys:
                    kstr = strip_module(k)
                    if kstr.startswith(prefix + idx + "."):
                        newkey = kstr.replace(prefix + idx + ".", prefix)
                        # if collision, prefer existing new value (do not overwrite)
                        if newkey not in new and newkey not in sd:
                            new[newkey] = sd[k]
            else:
                # fallback: single key mapping
                new[sk] = sd[found]
    # copy over remaining keys that were not remapped and not already present
    for k, v in sd.items():
        kstr = strip_module(k)
        if kstr not in new:
            new[kstr] = v
    return new

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", "-i", required=True, help="input checkpoint (models/best_model.pth)")
    parser.add_argument("--output", "-o", default="models/best_model_state_dict.pth", help="output state_dict")
    parser.add_argument("--allow-unsafe", action="store_true", help="allow unsafe torch.load(weights_only=False) fallback")
    args = parser.parse_args()

    inp = Path(args.input)
    out = Path(args.output)

    if not inp.exists():
        print("Input not found:", inp)
        return 2

    print("Loading checkpoint:", inp)
    ckpt = try_torch_load(inp, allow_unsafe=args.allow_unsafe)

    sd = extract_state_dict(ckpt)
    print("State-dict candidate with keys:", list(sd.keys())[:10], " ... (total keys)", len(sd))

    # Build skeleton keys for ResNet18 with class count inferred from class_map.json if present
    class_map_path = Path("models/class_map.json")
    if class_map_path.exists():
        try:
            cm = json.loads(class_map_path.read_text(encoding="utf8"))
            num_classes = len(cm)
        except Exception:
            num_classes = max(1, len(sd.get("fc.weight", [])) if "fc.weight" in sd else 3)
    else:
        num_classes = 3

    skel = resnet18(weights=None)
    skel.fc = torch.nn.Linear(skel.fc.in_features, num_classes)
    skel_state_keys = set(k for k in skel.state_dict().keys())

    # quick test: if keys already match, just write
    normalized_keys = {k for k in sd.keys()}
    if set(skel_state_keys).issubset(set(normalized_keys)) or set(k.split(".")[-1] for k in skel_state_keys).issubset(set(k.split(".")[-1] for k in normalized_keys)):
        print("Checkpoint keys already look compatible. Writing out state_dict as-is.")
        torch.save(sd, str(out))
        print("Wrote:", out)
        return 0

    print("Attempting heuristic remap of keys (fc.* index -> fc.*)")
    new_sd = remap_keys_for_fc(sd, skel_state_keys)

    # Try loading into skeleton with strict=False first
    try:
        skel.load_state_dict(new_sd, strict=False)
        print("Loaded remapped state_dict into skeleton (strict=False). Now saving cleaned state_dict.")
        # produce cleaned sd matching skeleton keys only
        cleaned = {k: v for k, v in new_sd.items() if k in skel.state_dict().keys()}
        # where cleaned missing keys, take from skeleton to have full shape
        for k in skel.state_dict().keys():
            if k not in cleaned:
                cleaned[k] = skel.state_dict()[k]
        torch.save(cleaned, str(out))
        print("Wrote cleaned state_dict to:", out)
        return 0
    except Exception as e:
        print("Remapped state_dict could not be loaded into skeleton:", e)
        # last resort: attempt to load by matching suffix names (weight/bias)
        # fallback: try simpler key replacement fc.1 -> fc and module. prefix removal
        fallback = {}
        for k, v in sd.items():
            kn = k
            if kn.startswith("module."):
                kn = kn[len("module."):]
            kn = re.sub(r"\.(\d+)\.", ".", kn)  # remove numeric indices in the middle e.g. fc.1.weight -> fc.weight
            fallback[kn] = v
        try:
            skel.load_state_dict(fallback, strict=False)
            cleaned = {k: v for k, v in fallback.items() if k in skel.state_dict().keys()}
            for k in skel.state_dict().keys():
                if k not in cleaned:
                    cleaned[k] = skel.state_dict()[k]
            torch.save(cleaned, str(out))
            print("Fallback cleaned and wrote to", out)
            return 0
        except Exception as e2:
            print("Failed fallback remap too:", e2)
            print("I cannot reliably convert this checkpoint automatically. Options:")
            print(" * Regenerate checkpoint as state_dict on the training machine (recommended):\n"
                  "     torch.save(model.state_dict(), 'best_model.pth')\n"
                  " * If checkpoint is trusted, you can set --allow-unsafe and re-run (it will use torch.load weights_only=False).")
            return 3

if __name__ == "__main__":
    exit(main())
