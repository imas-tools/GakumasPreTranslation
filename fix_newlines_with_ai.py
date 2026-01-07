#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用 DeepSeek API 修复 CSV 文件中译文的换行符数量，使其与原文一致
"""

import csv
import os
import time
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 初始化 OpenAI 客户端
client = OpenAI(
    api_key=os.getenv('OPENAI_API_KEY'),
    base_url=os.getenv('OPENAI_BASE_URL')
)


def count_newlines(text):
    """计算字符串中\n的数量"""
    if text is None:
        return 0
    return text.count('\\n')


def fix_translation_newlines(original_text, translated_text, target_newline_count):
    """使用 AI 修复译文中的换行符"""
    
    prompt = f"""你是一个专业的日语到中文翻译校对专家。

原文（日语）包含 {target_newline_count} 个换行符（\\n）：
{original_text}

当前译文（中文）包含 {count_newlines(translated_text)} 个换行符（\\n）：
{translated_text}

请在译文中添加或调整换行符（\\n），使译文的换行符数量与原文相同（{target_newline_count} 个）。

要求：
1. 译文必须包含恰好 {target_newline_count} 个 \\n
2. 换行位置要符合中文语义，不能切断词语或短语
3. \\n 不能放在句子的开头或结尾
4. 保持译文的完整性和流畅性
5. 只返回修正后的译文，不要添加任何解释

修正后的译文："""

    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "你是一个专业的翻译校对专家，擅长处理文本格式。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=500
        )
        
        fixed_text = response.choices[0].message.content.strip()
        
        # 验证修正后的换行符数量
        fixed_count = count_newlines(fixed_text)
        if fixed_count == target_newline_count:
            return fixed_text, True
        else:
            print(f"  ⚠️  AI 修正后的换行符数量不匹配: 期望 {target_newline_count}, 实际 {fixed_count}")
            return translated_text, False
            
    except Exception as e:
        print(f"  ❌ API 调用失败: {e}")
        return translated_text, False


def check_and_fix_csv_file(file_path, dry_run=False):
    """检查并修复单个 CSV 文件"""
    mismatches = []
    rows = []
    
    try:
        # 读取所有行
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            header = next(reader)
            rows.append(header)
            
            for row_num, row in enumerate(reader, start=2):
                rows.append(row)
                
                if len(row) < 4:
                    continue
                
                id_val = row[0]
                name_val = row[1]
                text_col = row[2]  # 第三列（原文）
                trans_col = row[3]  # 第四列（译文）
                
                text_newline_count = count_newlines(text_col)
                trans_newline_count = count_newlines(trans_col)
                
                if text_newline_count != trans_newline_count:
                    mismatches.append({
                        'row_index': len(rows) - 1,
                        'row_num': row_num,
                        'id': id_val,
                        'name': name_val,
                        'text': text_col,
                        'trans': trans_col,
                        'text_count': text_newline_count,
                        'trans_count': trans_newline_count
                    })
    
    except Exception as e:
        print(f"❌ 读取文件 {file_path} 时出错: {e}")
        return 0, 0
    
    if not mismatches:
        return 0, 0
    
    print(f"\n📄 文件: {file_path.name}")
    print(f"   发现 {len(mismatches)} 处不一致")
    
    fixed_count = 0
    
    # 修复每个不一致的地方
    for i, mismatch in enumerate(mismatches, 1):
        print(f"\n   [{i}/{len(mismatches)}] 行 {mismatch['row_num']}: {mismatch['name']}")
        print(f"   原文 ({mismatch['text_count']}个\\n): {mismatch['text'][:50]}...")
        print(f"   译文 ({mismatch['trans_count']}个\\n): {mismatch['trans'][:50]}...")
        
        if not dry_run:
            # 调用 AI 修复
            fixed_text, success = fix_translation_newlines(
                mismatch['text'],
                mismatch['trans'],
                mismatch['text_count']
            )
            
            if success:
                # 更新行数据
                rows[mismatch['row_index']][3] = fixed_text
                fixed_count += 1
                print(f"   ✅ 已修复: {fixed_text[:50]}...")
            
            # 添加延迟以避免 API 限流
            time.sleep(0.5)
    
    # 写回文件（如果不是 dry run）
    if not dry_run and fixed_count > 0:
        try:
            with open(file_path, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                writer.writerows(rows)
            print(f"\n   💾 已保存 {fixed_count} 处修复到文件")
        except Exception as e:
            print(f"\n   ❌ 保存文件失败: {e}")
            return len(mismatches), 0
    
    return len(mismatches), fixed_count


def main():
    print("=" * 80)
    print("使用 DeepSeek AI 修复译文换行符")
    print("=" * 80)
    
    # 检查环境变量
    if not os.getenv('OPENAI_API_KEY') or not os.getenv('OPENAI_BASE_URL'):
        print("❌ 错误: 未找到 OPENAI_API_KEY 或 OPENAI_BASE_URL 环境变量")
        print("请确保 .env 文件存在并包含这些配置")
        return
    
    print(f"\n✅ API 配置已加载")
    print(f"   Base URL: {os.getenv('OPENAI_BASE_URL')}")
    
    # 询问是否测试运行
    choice = input("\n是否进行测试运行（只检查不修改）? [y/N]: ").strip().lower()
    dry_run = (choice == 'y')
    
    if dry_run:
        print("\n⚠️  测试模式：将检查文件但不会进行修改")
    else:
        print("\n⚠️  生产模式：将修改文件内容")
        confirm = input("确认继续? [y/N]: ").strip().lower()
        if confirm != 'y':
            print("已取消")
            return
    
    # 获取 data 目录下的所有 CSV 文件
    data_dir = Path('data')
    
    if not data_dir.exists():
        print("❌ 错误: data 目录不存在")
        return
    
    csv_files = list(data_dir.glob('*.csv'))
    
    if not csv_files:
        print("❌ 错误: data 目录下没有找到 CSV 文件")
        return
    
    print(f"\n找到 {len(csv_files)} 个 CSV 文件")
    print("=" * 80)
    
    total_mismatches = 0
    total_fixed = 0
    
    # 处理每个文件
    for csv_file in sorted(csv_files):
        mismatches, fixed = check_and_fix_csv_file(csv_file, dry_run)
        total_mismatches += mismatches
        total_fixed += fixed
    
    # 总结
    print("\n" + "=" * 80)
    print("处理完成！")
    print("=" * 80)
    print(f"共检查 {len(csv_files)} 个文件")
    print(f"发现 {total_mismatches} 处换行符不一致")
    
    if not dry_run:
        print(f"成功修复 {total_fixed} 处")
        if total_fixed < total_mismatches:
            print(f"未能修复 {total_mismatches - total_fixed} 处（需要人工检查）")


if __name__ == '__main__':
    main()
