#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查CSV文件中第三列和第四列的换行符(\n)数量是否一致
"""

import csv
import os
from pathlib import Path


def count_newlines(text):
    """计算字符串中\n的数量"""
    if text is None:
        return 0
    return text.count('\\n')


def check_csv_file(file_path):
    """检查单个CSV文件"""
    mismatches = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            header = next(reader)  # 跳过标题行
            
            for row_num, row in enumerate(reader, start=2):  # 从第2行开始计数（第1行是标题）
                if len(row) < 4:
                    continue
                
                id_val = row[0]
                name_val = row[1]
                text_col = row[2]  # 第三列
                trans_col = row[3]  # 第四列
                
                text_newline_count = count_newlines(text_col)
                trans_newline_count = count_newlines(trans_col)
                
                if text_newline_count != trans_newline_count:
                    mismatches.append({
                        'row': row_num,
                        'id': id_val,
                        'name': name_val,
                        'text': text_col,
                        'trans': trans_col,
                        'text_count': text_newline_count,
                        'trans_count': trans_newline_count
                    })
    
    except Exception as e:
        print(f"读取文件 {file_path} 时出错: {e}")
        return None
    
    return mismatches


def main():
    # 获取data目录下的所有CSV文件
    data_dir = Path('data')
    
    if not data_dir.exists():
        print("错误: data目录不存在")
        return
    
    csv_files = list(data_dir.glob('*.csv'))
    
    if not csv_files:
        print("错误: data目录下没有找到CSV文件")
        return
    
    print(f"找到 {len(csv_files)} 个CSV文件")
    print("=" * 80)
    
    all_mismatches = []
    
    for csv_file in sorted(csv_files):
        mismatches = check_csv_file(csv_file)
        
        if mismatches is None:
            continue
        
        if mismatches:
            print(f"\n文件: {csv_file.name}")
            print(f"发现 {len(mismatches)} 处不一致")
            print("-" * 80)
            
            for mismatch in mismatches:
                print(f"  行号: {mismatch['row']}")
                print(f"  ID: {mismatch['id']}")
                print(f"  名称: {mismatch['name']}")
                print(f"  原文 (第3列, {mismatch['text_count']}个\\n): {mismatch['text']}")
                print(f"  译文 (第4列, {mismatch['trans_count']}个\\n): {mismatch['trans']}")
                print()
            
            all_mismatches.extend([
                {'file': csv_file.name, **m} for m in mismatches
            ])
    
    print("=" * 80)
    print(f"\n总结: 共检查 {len(csv_files)} 个文件，发现 {len(all_mismatches)} 处换行符数量不一致")
    
    # 保存结果到文件
    if all_mismatches:
        output_file = 'newline_mismatches.txt'
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("换行符数量不一致的记录\n")
            f.write("=" * 80 + "\n\n")
            
            for item in all_mismatches:
                f.write(f"文件: {item['file']}\n")
                f.write(f"行号: {item['row']}\n")
                f.write(f"ID: {item['id']}\n")
                f.write(f"名称: {item['name']}\n")
                f.write(f"原文 (第3列, {item['text_count']}个\\n): {item['text']}\n")
                f.write(f"译文 (第4列, {item['trans_count']}个\\n): {item['trans']}\n")
                f.write("-" * 80 + "\n\n")
        
        print(f"\n详细结果已保存到: {output_file}")


if __name__ == '__main__':
    main()
