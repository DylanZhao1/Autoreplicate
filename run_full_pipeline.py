from main import generate

if __name__ == '__main__':
    pdf_path = "D:\\Research\\LOUDONG\\ssrn-4433510.pdf"  # 请替换为您的PDF文件路径
    result = generate(pdf_path)
    print('生成结果:', result)