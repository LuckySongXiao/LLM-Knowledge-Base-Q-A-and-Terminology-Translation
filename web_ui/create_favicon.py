#!/usr/bin/env python3
"""
创建 favicon.ico 文件的脚本
生成一个简单的松瓷机电AI助手图标
"""

from PIL import Image, ImageDraw, ImageFont
import os

def create_favicon():
    """创建 favicon.ico 文件"""
    
    # 创建多个尺寸的图标
    sizes = [16, 32, 48, 64, 128, 256]
    images = []
    
    for size in sizes:
        # 创建图像
        img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # 设置颜色
        bg_color = (52, 152, 219)  # 蓝色背景
        text_color = (255, 255, 255)  # 白色文字
        
        # 绘制圆形背景
        margin = max(1, size // 16)
        draw.ellipse([margin, margin, size-margin, size-margin], fill=bg_color)
        
        # 绘制AI文字
        try:
            # 尝试使用系统字体
            font_size = max(8, size // 3)
            try:
                # Windows 系统字体
                font = ImageFont.truetype("arial.ttf", font_size)
            except:
                try:
                    # 备用字体
                    font = ImageFont.truetype("calibri.ttf", font_size)
                except:
                    # 使用默认字体
                    font = ImageFont.load_default()
            
            # 计算文字位置
            text = "AI"
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            x = (size - text_width) // 2
            y = (size - text_height) // 2 - bbox[1]
            
            # 绘制文字
            draw.text((x, y), text, fill=text_color, font=font)
            
        except Exception as e:
            print(f"绘制文字时出错 (尺寸 {size}): {e}")
            # 如果文字绘制失败，绘制一个简单的图形
            center = size // 2
            radius = size // 4
            draw.ellipse([center-radius, center-radius, center+radius, center+radius], 
                        fill=text_color)
        
        images.append(img)
    
    # 保存为 favicon.ico
    favicon_path = os.path.join(os.path.dirname(__file__), 'static', 'favicon.ico')
    
    # 确保 static 目录存在
    static_dir = os.path.dirname(favicon_path)
    os.makedirs(static_dir, exist_ok=True)
    
    # 保存图标
    images[0].save(favicon_path, format='ICO', sizes=[(img.width, img.height) for img in images])
    
    print(f"Favicon 已创建: {favicon_path}")
    
    # 同时创建 PNG 版本用于其他用途
    png_path = os.path.join(static_dir, 'favicon.png')
    images[-1].save(png_path, format='PNG')
    print(f"PNG 图标已创建: {png_path}")
    
    return favicon_path

if __name__ == "__main__":
    try:
        create_favicon()
        print("图标创建成功！")
    except Exception as e:
        print(f"创建图标时出错: {e}")
        import traceback
        traceback.print_exc()
