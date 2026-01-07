#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复CSV文件中译文缺少换行符的问题
规则：原文有1个\n，译文有0个\n，且译文中间有标点符号时，在标点符号后添加\n
"""

import csv
import re
from pathlib import Path


def count_newlines(text):
    """计算字符串中\n的数量"""
    if text is None:
        return 0
    return text.count('\\n')


def add_newline_after_punctuation(text):
    """
    在中文标点符号后添加\n
    优先在以下标点后添加：。！？，、；：
    """
    # 定义可以添加换行的标点符号（按优先级排序）
    punctuation_priority = ['。', '！', '？', '，', '、', '；', '：']
    
    # 尝试按优先级在标点后添加\n
    for punct in punctuation_priority:
        if punct in text:
            # 找到标点符号的位置，在第一个出现的标点后添加\n
            pos = text.find(punct)
            if pos != -1 and pos < len(text) - 1:  # 确保不是最后一个字符
                return text[:pos+1] + '\\n' + text[pos+1:]
    
    return text


def fix_csv_file(file_path):
    """修复单个CSV文件"""
    fixed_count = 0
    rows = []
    
    try:
        # 读取文件
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            header = next(reader)
            rows.append(header)
            
            for row in reader:
                if len(row) < 4:
                    rows.append(row)
                    continue
                
                text_col = row[2]  # 第三列
                trans_col = row[3]  # 第四列
                
                text_newline_count = count_newlines(text_col)
                trans_newline_count = count_newlines(trans_col)
                
                # 只处理：原文1个\n，译文0个\n的情况
                if text_newline_count == 1 and trans_newline_count == 0:
                    # 检查译文是否包含标点符号
                    if any(p in trans_col for p in ['。', '！', '？', '，', '、', '；', '：']):
                        # 在标点符号后添加\n
                        new_trans = add_newline_after_punctuation(trans_col)
                        if new_trans != trans_col:
                            row[3] = new_trans
                            fixed_count += 1
                
                rows.append(row)
        
        # 如果有修改，写回文件
        if fixed_count > 0:
            with open(file_path, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                writer.writerows(rows)
    
    except Exception as e:
        print(f"处理文件 {file_path} 时出错: {e}")
        return 0
    
    return fixed_count


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
    
    print(f"开始处理 {len(csv_files)} 个CSV文件……")
    print("=" * 80)
    
    total_fixed = 0
    fixed_files = []
    
    for csv_file in sorted(csv_files):
        fixed_count = fix_csv_file(csv_file)
        
        if fixed_count > 0:
            total_fixed += fixed_count
            fixed_files.append((csv_file.name, fixed_count))
            print(f"✓ {csv_file.name}: 修复了 {fixed_count} 处")
    
    print("=" * 80)
    print(f"\n完成！共修复 {len(fixed_files)} 个文件，总计 {total_fixed} 处换行符")
    
    if fixed_files:
        print("\n修复的文件列表：")
        for filename, count in fixed_files:
            print(f"  - {filename}: {count} 处")


if __name__ == '__main__':
    main()
