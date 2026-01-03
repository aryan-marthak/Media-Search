"""
Interactive SigLIP temperature tuning tool.
Test different temperature values and see their impact on scores.
"""

import os
import numpy as np
from PIL import Image
from services.embeddings import encode_text, encode_image, calibrate_siglip_score

def interactive_tuning():
    """Interactive tool to find optimal temperature."""
    
    img_path = r"D:\Media-Search\data\images\c7e1dc1c-dc3c-420b-9f47-8cd297fd02cb"
    
    if not os.path.exists(img_path):
        print(f"❌ Image directory not found: {img_path}")
        return
    
    files = [f for f in os.listdir(img_path) if f.lower().endswith(('.jpg', '.png', '.jpeg'))]
    if not files:
        print(f"❌ No images found in {img_path}")
        return
    
    # Load image once
    test_img_path = os.path.join(img_path, files[0])
    test_img = Image.open(test_img_path).convert("RGB")
    img_emb = encode_image(test_img)
    
    print("\n" + "=" * 80)
    print("SigLIP TEMPERATURE TUNING TOOL")
    print("=" * 80)
    print(f"\n📷 Image: {files[0]}")
    print("\nCommands:")
    print("  'test <query>' - Test a query with different temperatures")
    print("  'compare <query>' - Compare temperature impact for a query")
    print("  'all <temp>' - Test all default queries with a specific temperature")
    print("  'recommend' - Get temperature recommendation based on your image")
    print("  'quit' - Exit")
    print()
    
    while True:
        try:
            command = input("\n> ").strip().lower()
            
            if command == "quit":
                print("\n✅ Goodbye!")
                break
            
            elif command == "recommend":
                print("\n" + "-" * 80)
                print("TEMPERATURE RECOMMENDATION")
                print("-" * 80)
                
                # Analyze distribution
                test_queries = ["dog", "person", "outdoor", "food", "abstract"]
                raw_scores = []
                
                for q in test_queries:
                    q_emb = encode_text(q)
                    raw_sim = np.dot(img_emb, q_emb)
                    raw_scores.append(raw_sim)
                
                mean_score = np.mean(raw_scores)
                std_score = np.std(raw_scores)
                
                print(f"\nYour image's semantic profile:")
                print(f"  Mean score: {mean_score:.4f}")
                print(f"  Std dev: {std_score:.4f}")
                print(f"  Score range: [{min(raw_scores):.4f}, {max(raw_scores):.4f}]")
                
                # Recommend temperature
                if mean_score < -0.05:
                    recommended_temp = 15
                    reason = "Image has low semantic content"
                elif mean_score < 0:
                    recommended_temp = 18
                    reason = "Image is somewhat abstract/ambiguous"
                elif mean_score < 0.05:
                    recommended_temp = 20
                    reason = "Image has moderate semantic content"
                else:
                    recommended_temp = 25
                    reason = "Image has clear semantic content"
                
                if std_score < 0.03:
                    recommended_temp = max(10, recommended_temp - 5)
                    reason += ", consider lower temperature for better recall"
                
                print(f"\n✨ Recommended temperature: {recommended_temp}")
                print(f"   Reason: {reason}")
                
                # Show preview
                print(f"\n   Preview with temp={recommended_temp}:")
                for q in test_queries[:3]:
                    q_emb = encode_text(q)
                    raw = np.dot(img_emb, q_emb)
                    calib = calibrate_siglip_score(raw, temperature=recommended_temp)
                    print(f"   '{q}' → {calib:.3f}")
            
            elif command.startswith("test "):
                query = command[5:].strip()
                if not query:
                    print("❌ Please provide a query. Usage: test <query>")
                    continue
                
                print(f"\n📊 Testing query: '{query}'")
                print("-" * 80)
                print(f"{'Temperature':<15} {'Raw Score':<15} {'Calibrated':<15}")
                print("-" * 80)
                
                q_emb = encode_text(query)
                raw_sim = np.dot(img_emb, q_emb)
                
                for temp in [10, 12, 15, 18, 20, 25, 30, 35]:
                    calib = calibrate_siglip_score(raw_sim, temperature=temp)
                    print(f"{temp:<15} {raw_sim:<15.4f} {calib:<15.4f}")
            
            elif command.startswith("compare "):
                query = command[8:].strip()
                if not query:
                    print("❌ Please provide a query. Usage: compare <query>")
                    continue
                
                q_emb = encode_text(query)
                raw_sim = np.dot(img_emb, q_emb)
                
                print(f"\n📈 Temperature impact comparison for '{query}'")
                print(f"Raw score: {raw_sim:.4f}")
                print("-" * 80)
                
                temps = [10, 15, 20, 25, 30]
                calibs = [calibrate_siglip_score(raw_sim, temperature=t) for t in temps]
                
                # ASCII bar chart
                max_calib = max(calibs)
                for temp, calib in zip(temps, calibs):
                    bar_len = int(calib * 50)
                    bar = "█" * bar_len + "░" * (50 - bar_len)
                    print(f"Temp {temp:2d} [{bar}] {calib:.3f}")
                
                print(f"\n💡 Observation: Lower temp = higher scores (more lenient)")
                print(f"                Higher temp = lower scores (more strict)")
            
            elif command.startswith("all "):
                try:
                    temp = int(command[4:].strip())
                    if temp < 1 or temp > 100:
                        print("❌ Temperature must be between 1 and 100")
                        continue
                    
                    queries = ["dog", "person", "outdoor", "food", "beautiful", 
                              "dark", "bright", "nature", "abstract", "random"]
                    
                    print(f"\n📊 All queries with temperature={temp}")
                    print("-" * 80)
                    print(f"{'Query':<20} {'Raw Score':<15} {'Calibrated':<15}")
                    print("-" * 80)
                    
                    for q in queries:
                        q_emb = encode_text(q)
                        raw = np.dot(img_emb, q_emb)
                        calib = calibrate_siglip_score(raw, temperature=temp)
                        print(f"{q:<20} {raw:<15.4f} {calib:<15.4f}")
                
                except ValueError:
                    print("❌ Please provide a number. Usage: all <temperature>")
            
            elif command:
                print("❌ Unknown command. Type 'quit' to exit.")
        
        except KeyboardInterrupt:
            print("\n\n✅ Exiting...")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    try:
        interactive_tuning()
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
