import os

import torch
from transformers import pipeline
from pprint import pprint

def main():        
    
    if os.getenv('MODEL_PATH') is None:
        print("MODEL_PATH is not set. Using the default model path: answerdotai/ModernBERT-base")
                
    model_path = os.getenv('MODEL_PATH', "answerdotai/ModernBERT-base")    
    
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Using nvidia gpu: {torch.cuda.is_available()}")
    
    pipe = pipeline(
        "fill-mask",
        model=model_path,
        torch_dtype=torch.bfloat16,
        device=device
    )
    
    input_text = "He walked to the [MASK]."
    results = pipe(input_text)
    pprint(results)

if __name__ == "__main__":
    main()