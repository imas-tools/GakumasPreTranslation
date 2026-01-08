#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用 DeepSeek API 重新翻译换行符数量不一致的内容
"""

import csv
import os
from pathlib import Path
from openai import OpenAI
import time
import re


def count_newlines(text):
    """计算字符串中\n的数量"""
    if text is None:
        return 0
    return text.count('\\n')


def validate_translation(original_text, translated_text, target_newline_count):
    """
    验证翻译结果是否符合要求
    
    要求：
    1. \n 数量必须与原文一致
    2. \n 不能出现在译文的头尾
    3. \n 不能把英文单词切断
    """
    # 检查 \n 数量
    actual_count = count_newlines(translated_text)
    if actual_count != target_newline_count:
        return False, f"\n数量不匹配: 期望{target_newline_count}个，实际{actual_count}个"
    
    # 检查 \n 不在头尾
    if translated_text.startswith('\\n') or translated_text.endswith('\\n'):
        return False, "\\n 不应出现在译文的头尾"
    
    # 检查 \n 是否切断了英文单词（只检查英文字母，不检查中文和数字）
    parts = translated_text.split('\\n')
    for i, part in enumerate(parts):
        if i > 0 and part:
            prev_part = parts[i-1]
            if prev_part:
                # 获取 \n 前后的字符
                char_before = prev_part[-1] if prev_part else ''
                char_after = part[0] if part else ''
                
                # 只检查英文字母：如果 \n 前后都是英文字母（a-z, A-Z），则可能切断了单词
                is_english_before = char_before.isascii() and char_before.isalpha()
                is_english_after = char_after.isascii() and char_after.isalpha()
                
                if is_english_before and is_english_after:
                    return False, f"\\n 切断了英文单词: ...{prev_part[-10:]}\\n{part[:10]}..."
    
    return True, "验证通过"


def translate_with_api(client, original_text, context_name="", max_retries=3):
    """
    使用 API 翻译文本，确保换行符数量一致
    
    Args:
        client: OpenAI 客户端
        original_text: 原文（日文）
        context_name: 说话者名称（用于提供上下文）
        max_retries: 最大重试次数
    
    Returns:
        翻译后的文本，如果失败则返回 None
    """
    newline_count = count_newlines(original_text)
    
    # 构建提示词
    system_prompt = """你是一个专业的日中游戏文本翻译专家，专门翻译偶像养成游戏的对话内容。

翻译要求：
1. 保持原文的换行符（\\n）数量完全一致
2. 换行符（\\n）不能出现在译文的开头或结尾
3. 换行符（\\n）应该放在合适的语义断句位置，不能把完整的词语或短语切断
4. 翻译要符合游戏角色的语气和人设
5. 保持游戏术语的一致性
6. 译文要自然流畅，符合中文表达习惯"""

    user_prompt = f"""请将以下日文翻译成中文。

说话者：{context_name if context_name else '（未知）'}
原文（包含 {newline_count} 个 \\n）：
{original_text}

注意：
- 必须在译文中保留 {newline_count} 个 \\n
- \\n 应该放在合适的断句位置（如句子之间、短语之间）
- \\n 不能出现在译文的开头或结尾
- 直接输出翻译结果，不要包含任何解释或额外内容"""

    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,  # 降低温度以获得更稳定的结果
                max_tokens=500
            )
            
            translated_text = response.choices[0].message.content.strip()
            
            # 清理可能的额外标记
            translated_text = translated_text.replace('```', '').strip()
            
            # 验证翻译结果
            is_valid, message = validate_translation(original_text, translated_text, newline_count)
            
            if is_valid:
                print(f"  ✓ 翻译成功（第 {attempt + 1} 次尝试）")
                return translated_text
            else:
                print(f"  ✗ 验证失败（第 {attempt + 1} 次尝试）: {message}")
                if attempt < max_retries - 1:
                    time.sleep(1)  # 重试前等待
                    
        except Exception as e:
            print(f"  ✗ API 调用失败（第 {attempt + 1} 次尝试）: {e}")
            if attempt < max_retries - 1:
                time.sleep(2)  # 出错后等待更长时间
    
    print(f"  ✗ 翻译失败：达到最大重试次数")
    return None


def update_csv_file(file_path, row_number, new_translation):
    """
    更新 CSV 文件中指定行的翻译内容
    
    Args:
        file_path: CSV 文件路径
        row_number: 行号（从1开始，包括标题行）
        new_translation: 新的翻译内容
    """
    rows = []
    
    # 读取所有行
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        rows = list(reader)
    
    # 更新指定行（row_number 是从1开始的，包括标题行）
    if row_number <= len(rows):
        rows[row_number - 1][3] = new_translation  # 第4列（索引3）是译文
        
        # 写回文件
        with open(file_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerows(rows)
        
        return True
    
    return False


def parse_mismatches_file(file_path):
    """
    解析 newline_mismatches.txt 文件，提取所有不一致的记录
    
    Returns:
        List of dict with keys: file, row, id, name, original, translation, original_count, translation_count
    """
    mismatches = []
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 按分隔线分割记录
    records = content.split('--------------------------------------------------------------------------------')
    
    for record in records:
        if '文件:' not in record:
            continue
            
        lines = record.strip().split('\n')
        mismatch = {}
        
        for line in lines:
            if line.startswith('文件:'):
                mismatch['file'] = line.split(':', 1)[1].strip()
            elif line.startswith('行号:'):
                mismatch['row'] = int(line.split(':', 1)[1].strip())
            elif line.startswith('ID:'):
                mismatch['id'] = line.split(':', 1)[1].strip()
            elif line.startswith('名称:'):
                mismatch['name'] = line.split(':', 1)[1].strip()
            elif line.startswith('原文'):
                # 提取原文内容和 \n 数量
                match = re.search(r'原文 \(第3列, (\d+)个\\n\): (.+)', line)
                if match:
                    mismatch['original_count'] = int(match.group(1))
                    mismatch['original'] = match.group(2)
            elif line.startswith('译文'):
                # 提取译文内容和 \n 数量
                match = re.search(r'译文 \(第4列, (\d+)个\\n\): (.+)', line)
                if match:
                    mismatch['translation_count'] = int(match.group(1))
                    mismatch['translation'] = match.group(2)
        
        if 'file' in mismatch and 'original' in mismatch:
            mismatches.append(mismatch)
    
    return mismatches


def main():
    # 设置 API 密钥和基础 URL
    api_key = os.environ.get('OPENAI_API_KEY', 'sk-5c7503d7329d4b1081cc4bad40bb4d5e')
    base_url = os.environ.get('OPENAI_BASE_URL', 'https://api.deepseek.com')
    
    print(f"使用 API: {base_url}")
    print("=" * 80)
    
    # 初始化 OpenAI 客户端
    client = OpenAI(
        api_key=api_key,
        base_url=base_url
    )
    
    # 解析不一致记录文件
    mismatches_file = Path('newline_mismatches.txt')
    
    if not mismatches_file.exists():
        print("错误: newline_mismatches.txt 文件不存在")
        print("请先运行 check_newlines.py 生成该文件")
        return
    
    mismatches = parse_mismatches_file(mismatches_file)
    
    print(f"找到 {len(mismatches)} 条需要重新翻译的记录")
    print("=" * 80)
    
    data_dir = Path('data')
    success_count = 0
    fail_count = 0
    skip_count = 0
    
    for i, mismatch in enumerate(mismatches, 1):
        print(f"\n[{i}/{len(mismatches)}] 处理: {mismatch['file']} - 行 {mismatch['row']}")
        print(f"  说话者: {mismatch['name']}")
        print(f"  原文: {mismatch['original']}")
        print(f"  旧译文: {mismatch['translation']}")
        print(f"  需要 {mismatch['original_count']} 个 \\n")
        
        # 翻译
        new_translation = translate_with_api(
            client,
            mismatch['original'],
            mismatch['name']
        )
        
        if new_translation:
            print(f"  新译文: {new_translation}")
            
            # 更新 CSV 文件
            file_path = data_dir / mismatch['file']
            if update_csv_file(file_path, mismatch['row'], new_translation):
                print(f"  ✓ 已更新文件")
                success_count += 1
            else:
                print(f"  ✗ 更新文件失败")
                fail_count += 1
        else:
            print(f"  ✗ 跳过此条记录")
            skip_count += 1
        
        # 避免 API 限流
        time.sleep(0.5)
    
    print("\n" + "=" * 80)
    print(f"处理完成！")
    print(f"  成功: {success_count}")
    print(f"  失败: {fail_count}")
    print(f"  跳过: {skip_count}")
    print(f"\n建议运行 check_newlines.py 验证结果")


if __name__ == '__main__':
    main()
