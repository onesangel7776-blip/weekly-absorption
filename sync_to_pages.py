import shutil, os
for src in ["best_tf_per_ticker.json","absorption_v5.json","journal_data_v5.json"]:
    if os.path.exists(src):
        dst = os.path.join("docs","v5-ma-delta",src)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy(src, dst)
        print(f"Copied {src} -> {dst}")
