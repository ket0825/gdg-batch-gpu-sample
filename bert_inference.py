import torch
from transformers import AutoTokenizer, AutoModelForMaskedLM
import os

def load_model():    
    if os.getenv('MODEL_PATH') is None:
        print("MODEL_PATH is not set. Using the default model path: answerdotai/ModernBERT-base")
                
    model_path = os.getenv('MODEL_PATH', "answerdotai/ModernBERT-base")    
            
    tokenizer = AutoTokenizer.from_pretrained(model_path)
    model = AutoModelForMaskedLM.from_pretrained(model_path)
    
    # GPU 사용 설정
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model = model.to(device)

    return tokenizer, model

def main():    
    tokenizer, model = load_model()
    
    # 여기에 실제 추론 로직 구현
    text = "The capital of France is [MASK]."
    inputs = tokenizer(text, return_tensors="pt")
    outputs = model(**inputs)

    # To get predictions for the mask:
    masked_index = inputs["input_ids"][0].tolist().index(tokenizer.mask_token_id)
    predicted_token_id = outputs.logits[0, masked_index].argmax(axis=-1)
    predicted_token = tokenizer.decode(predicted_token_id)
    print("Predicted token:", predicted_token)
    # Predicted token:  Paris
        
    # 결과 처리 및 저장
    # ...

if __name__ == "__main__":
    main()