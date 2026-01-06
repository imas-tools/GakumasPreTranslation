import csv
import re
import os
from pathlib import Path

def remove_html_tags(text):
    """
    删除HTML标签对，但保留标签中间的内容
    例如: '<r=スペシャル>特别</r>' -> '特别'
          '<em>内容</em>' -> '内容'
    """
    if not text or not isinstance(text, str):
        return text
    
    # 匹配形如 <标签名[属性]>内容</标签名> 的模式
    # 使用非贪婪匹配确保正确处理嵌套或多个标签
    pattern = r'<(\w+)[^>]*>(.*?)</\1>'
    
    # 递归处理，直到所有标签都被移除
    while re.search(pattern, text):
        text = re.sub(pattern, r'\2', text)
    
    return text

def process_csv_file(file_path):
    """
    处理单个CSV文件，删除第4列'trans'中的标签对
    """
    print(f"正在处理: {file_path}")
    
    # 读取CSV文件
    rows = []
    with open(file_path, 'r', encoding='utf-8', newline='') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        
        for row in reader:
            # 处理'trans'列
            if 'trans' in row and row['trans']:
                original = row['trans']
                row['trans'] = remove_html_tags(original)
                if original != row['trans']:
                    print(f"  修改: {original[:50]}... -> {row['trans'][:50]}...")
            rows.append(row)
    
    # 写回CSV文件
    with open(file_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"完成: {file_path}\n")

def main():
    """
    主函数：遍历data文件夹下所有CSV文件并处理
    """
    data_folder = Path(__file__).parent / 'data'
    
    if not data_folder.exists():
        print(f"错误: 文件夹 {data_folder} 不存在")
        return
    
    # 获取所有CSV文件
    csv_files = list(data_folder.glob('*.csv'))
    
    if not csv_files:
        print(f"警告: 在 {data_folder} 中没有找到CSV文件")
        return
    
    print(f"找到 {len(csv_files)} 个CSV文件\n")
    
    # 处理每个CSV文件
    for csv_file in csv_files:
        try:
            process_csv_file(csv_file)
        except Exception as e:
            print(f"处理文件 {csv_file} 时出错: {e}\n")
    
    print("所有文件处理完成！")

if __name__ == '__main__':
    main()
