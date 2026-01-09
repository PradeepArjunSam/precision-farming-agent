from huggingface_hub import hf_hub_download
import os

repo_id = "TheBloke/Mistral-7B-Instruct-v0.2-GGUF"
filename = "mistral-7b-instruct-v0.2.Q4_K_M.gguf"
local_dir = "models"  # Relative path in D:\precision_farming

print(f"Downloading {filename} from {repo_id}...")
os.makedirs(local_dir, exist_ok=True)

model_path = hf_hub_download(
    repo_id=repo_id,
    filename=filename,
    local_dir=local_dir,
    local_dir_use_symlinks=False
)

print(f"Model downloaded to: {model_path}")
