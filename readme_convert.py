import re

def convert_md_to_txt(md_content):
    # Find and store plaintext blocks
    plaintext_blocks = re.findall(r'```plaintext([\s\S]*?)```', md_content)
    placeholders = [f'{{PLAINTEXT_BLOCK_{i}}}' for i in range(len(plaintext_blocks))]

    # Replace each plaintext block with a unique placeholder
    for i, block in enumerate(plaintext_blocks):
        original_block = f'```plaintext{block}```'
        md_content = md_content.replace(original_block, placeholders[i], 1)

    # Basic conversion for Markdown -> plain text (e.g., remove MD syntax)
    txt_content = re.sub(r'#+\s', '', md_content)  # Remove headers
    txt_content = re.sub(r'\*\*([^*]+)\*\*', r'\1', txt_content)  # Remove bold
    txt_content = re.sub(r'__([^_]+)__', r'\1', txt_content)      # Remove italic
    txt_content = re.sub(r'[*`>]', '', txt_content)                # Remove some other Markdown characters

    # Restore plaintext blocks
    for i, block in enumerate(plaintext_blocks):
        txt_content = txt_content.replace(placeholders[i], block, 1)

    return txt_content

def convert_md_to_bbcode(md_content):
    # Find and store plaintext blocks
    plaintext_blocks = re.findall(r'```plaintext([\s\S]*?)```', md_content)
    placeholders = [f'{{PLAINTEXT_BLOCK_{i}}}' for i in range(len(plaintext_blocks))]

    # Replace each plaintext block with a unique placeholder
    for i, block in enumerate(plaintext_blocks):
        original_block = f'```plaintext{block}```'
        md_content = md_content.replace(original_block, placeholders[i], 1)

    # Convert Markdown headers to BBCode
    bbcode_content = re.sub(r'###### (.*?)\n', r'\n[size=1][b]\1[/b][/size]\n', md_content)
    bbcode_content = re.sub(r'##### (.*?)\n', r'\n[size=2][b]\1[/b][/size]\n', bbcode_content)
    bbcode_content = re.sub(r'#### (.*?)\n', r'\n[size=3][b]\1[/b][/size]\n', bbcode_content)
    bbcode_content = re.sub(r'### (.*?)\n', r'\n[size=4][b]\1[/b][/size]\n', bbcode_content)
    bbcode_content = re.sub(r'## (.*?)\n', r'\n[size=5][b]\1[/b][/size]\n', bbcode_content)
    bbcode_content = re.sub(r'# (.*?)\n', r'\n[size=6][b]\1[/b][/size]\n', bbcode_content)

    # Convert Markdown bold to BBCode bold
    bbcode_content = re.sub(r'\*\*(.*?)\*\*', r'[b]\1[/b]', bbcode_content)


    # Restore plaintext blocks (unchanged)
    for i, block in enumerate(plaintext_blocks):
        bbcode_content = bbcode_content.replace(placeholders[i], block, 1)

    return bbcode_content

def convert_readme(input_file, txt_output_file, bbcode_output_file):
    with open(input_file, 'r', encoding='utf-8') as infile:
        md_content = infile.read()

    txt_content = convert_md_to_txt(md_content)
    bbcode_content = convert_md_to_bbcode(md_content)

    with open(txt_output_file, 'w', encoding='utf-8') as txt_outfile:
        txt_outfile.write(txt_content)

    with open(bbcode_output_file, 'w', encoding='utf-8') as bbcode_outfile:
        bbcode_outfile.write(bbcode_content)

# Example usage
input_file = 'README.md'
txt_output_file = 'README.txt'
bbcode_output_file = 'README.bbcode'
convert_readme(input_file, txt_output_file, bbcode_output_file)