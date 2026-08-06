# agent_ai2/train_gpt_model.py
import os
import argparse
import logging
from agent_ai2.gpt_trainer import GPTTrainer

# Log dizinini oluştur
os.makedirs("agent_ai2/logs", exist_ok=True)

# Günlük kaydı yapılandırma
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("agent_ai2/logs/train_gpt_model.log", mode='a', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("GPT_Training")

def main():
    """GPT modelini eğitmek için ana fonksiyon"""
    parser = argparse.ArgumentParser(description='TÜBİTAK Proje Planı Üretim Modeli Eğitimi')
    
    parser.add_argument('--model', type=str, default="gpt2", 
                        help='Kullanılacak GPT modeli (gpt2, gpt2-medium, vs.)')
    parser.add_argument('--epochs', type=int, default=4,
                        help='Eğitim epoch sayısı')
    parser.add_argument('--batch_size', type=int, default=4,
                        help='Batch size')
    parser.add_argument('--learning_rate', type=float, default=5e-5,
                        help='Öğrenme oranı')
    parser.add_argument('--output_dir', type=str, default="agent_ai2/gpt_model_data",
                        help='Çıktı dizini')
    parser.add_argument('--model_dir', type=str, default="models",
                        help='Model kayıt dizini')
    parser.add_argument('--db_path', type=str, default="db.sqlite3",
                        help='Veritabanı dosya yolu')
    
    args = parser.parse_args()
    
    logger.info(f"GPT Eğitimi Başlatılıyor: model={args.model}, epochs={args.epochs}")
    
    # GPT Trainer oluştur
    trainer = GPTTrainer(
        base_model_name=args.model,
        output_dir=args.output_dir,
        model_dir=args.model_dir,
        db_path=args.db_path
    )
    
    # Tam eğitim sürecini çalıştır
    result = trainer.run_training_pipeline()
    
    if result:
        logger.info(f"Eğitim başarıyla tamamlandı! Doğruluk: {result['accuracy_estimate']:.2f}%")
        logger.info(f"Model kaydedildi: {args.model_dir}/gpt2_tubitak_plan")
    else:
        logger.error("Eğitim süreci başarısız oldu.")

if __name__ == "__main__":
    main()