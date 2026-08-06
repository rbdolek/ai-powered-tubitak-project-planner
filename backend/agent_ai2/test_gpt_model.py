# test_gpt_model.py
import argparse
import logging
from agent_ai2.agent_ai_model import AgentAIModel
from agent_ai2.agent_ai_service import AgentAIService

# Günlük kaydı yapılandırma
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("agent_ai2/logs/test_gpt_model.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("GPT_Testing")

def main():
    """GPT modelini test etmek için ana fonksiyon"""
    parser = argparse.ArgumentParser(description='TÜBİTAK Proje Planı Üretim Modeli Testi')
    
    parser.add_argument('--model_dir', type=str, default="models/gpt2_tubitak_plan",
                        help='Model dizini')
    parser.add_argument('--max_length', type=int, default=1024,
                        help='Maksimum çıktı uzunluğu')
    parser.add_argument('--query', type=str, 
                        default="TÜBİTAK 1001 için 12 aylık yapay zeka projesi planı",
                        help='Test sorgusu')
    
    args = parser.parse_args()
    
    logger.info(f"GPT Modeli Test Ediliyor: {args.model_dir}")
    
    # Model ve servis oluştur
    model = AgentAIModel(model_dir=args.model_dir, max_length=args.max_length)
    service = AgentAIService(model)
    
    # Modeli yükle
    if not model.load_resources():
        logger.error("Model yüklenemedi!")
        return
    
    logger.info(f"Test sorgusu: {args.query}")
    
    # Plan üret
    plan_text, meta = service.generate_response(args.query)
    
    # Sonuçları göster
    logger.info(f"Üretilen plan:\n{'='*50}\n{plan_text}\n{'='*50}")
    
    if meta:
        logger.info(f"Meta bilgiler:")
        logger.info(f"Fon: {meta['fon_info']}")
        logger.info(f"Doğruluk: {meta['model_accuracy']:.2f}%")
        logger.info(f"Üretim süresi: {meta['generation_time']:.2f} saniye")

if __name__ == "__main__":
    main()