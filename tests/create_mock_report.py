from PIL import Image, ImageDraw, ImageFont
import os

def create_mock_report():
    print("Creating mock medical report image (Vietnamese)...")
    
    # Create a white A4-sized image
    width, height = 800, 1000
    image = Image.new('RGB', (width, height), color='white')
    draw = ImageDraw.Draw(image)
    
    # Text to put on the report
    text = (
        "BAO CAO Y TE - BENH VIEN CHO RAY\n"
        "Ngay: 25 thang 04 nam 2026\n\n"
        "BENH NHAN: Nguyen Van Minh\n"
        "GIOI TINH: Nam   TUOI: 58\n\n"
        "CHAN DOAN:\n"
        "Benh nhan co khoi u o thuy tren phoi phai.\n"
        "Nghi ngo Ung thu phoi te bao nho (SCLC).\n"
        "Giai doan: Giai doan khu tru (Limited Stage).\n\n"
        "TRIEU CHUNG:\n"
        "- Ho keo dai co dom lan mau.\n"
        "- Dau nguc khi hit tho sau.\n"
        "- Sut can nhanh (5kg trong 1 thang).\n\n"
        "YEU CAU:\n"
        "Can chuyen tuyen den trung tam chuyen khoa Ung buou\n"
        "tai Malaysia de thuc hien hoa tri va xa tri ket hop.\n"
        "Benh nhan can ho tro di chuyen (Xe lan) tai san bay."
    )
    
    # Note: Using standard font as we can't guarantee custom Vietnamese fonts on all systems
    # Tesseract is very good at reading standard fonts.
    try:
        draw.text((50, 50), text, fill='black')
        output_path = os.path.join(os.path.dirname(__file__), "vietnamese_report.jpg")
        image.save(output_path)
        print("Success: vietnamese_report.jpg created!")
    except Exception as e:
        print(f"Error creating image: {e}")

if __name__ == "__main__":
    create_mock_report()
